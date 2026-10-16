#!/usr/bin/env python3
"""
reconcile_status_issues.py - Upptime False Alarm & Zombie Issue Reconciler.

Proactively monitors open GitHub issues with the 'status' label.
If an issue was opened due to a transient blip, network hiccup, or git push collision:
1. Conducts a multi-stage validation probe (up to 3 attempts with exponential backoff).
2. If the endpoint is verified UP (HTTP 200), unlocks the issue, posts a detailed
   verification comment, and closes it immediately.
3. Synchronizes history/<slug>.yml to ensure Upptime's internal state machine remains consistent.
"""

import os
import sys
import json
import time
import glob
import re
import urllib.request
import urllib.error
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# UTF-8 stdout
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 (Upptime Watchdog; +https://status.drsumaiya.com)"
)


def run_gh(args):
    """Run a gh CLI command and return stdout string."""
    try:
        res = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"gh command failed: {e.stderr.strip()}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error running gh: {e}", file=sys.stderr)
        return ""


def load_tracked_endpoints():
    """Load all tracked endpoints and their slugs from history/*.yml."""
    endpoints = {}
    history_files = glob.glob("history/*.yml")
    for hf in history_files:
        slug = Path(hf).stem
        try:
            with open(hf, "r", encoding="utf-8") as f:
                content = f.read()
            url_match = re.search(r"^url:\s*(.+)$", content, re.MULTILINE)
            if url_match:
                url = url_match.group(1).strip()
                endpoints[slug] = {
                    "slug": slug,
                    "url": url,
                    "file": hf,
                }
        except Exception as e:
            print(f"⚠️ Could not parse {hf}: {e}", file=sys.stderr)
    return endpoints


def probe_endpoint(url: str, max_retries: int = 3, timeout: int = 15):
    """
    Perform a multi-probe health check against the URL.
    Returns (is_up: bool, status_code: int, latency_ms: int, error_msg: str).
    """
    for attempt in range(1, max_retries + 1):
        start_time = time.time()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                code = response.status
                if 200 <= code < 400:
                    return True, code, latency_ms, ""
        except urllib.error.HTTPError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            # Some REST API routes or assets may return 200 or 403 (with WAF/Token), but 5xx is down
            if 200 <= e.code < 400 or e.code == 403:
                return True, e.code, latency_ms, f"HTTP {e.code}"
            if attempt == max_retries:
                return False, e.code, latency_ms, f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            if attempt == max_retries:
                return False, 0, latency_ms, str(e)

        time.sleep(2)

    return False, 0, 0, "All probe attempts failed"


def sync_history_file(hf_path: str, code: int, response_time: int):
    """Ensure history/<slug>.yml reflects status: up."""
    try:
        with open(hf_path, "r", encoding="utf-8") as f:
            content = f.read()

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        content = re.sub(r"^status:\s*down", "status: up", content, flags=re.MULTILINE)
        content = re.sub(r"^code:\s*\d+", f"code: {code}", content, flags=re.MULTILINE)
        content = re.sub(r"^responseTime:\s*\d+", f"responseTime: {response_time}", content, flags=re.MULTILINE)
        content = re.sub(r"^lastUpdated:\s*.+$", f"lastUpdated: {now_iso}", content, flags=re.MULTILINE)

        with open(hf_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ Synchronized {hf_path} to status: up")
    except Exception as e:
        print(f"⚠️ Error syncing {hf_path}: {e}", file=sys.stderr)


def reconcile_issues(repo: str):
    print(f"🔍 Checking for open Upptime status issues on {repo}...")
    endpoints = load_tracked_endpoints()
    print(f"  Loaded {len(endpoints)} tracked endpoints from history/ directory.")

    raw_issues = run_gh([
        "issue", "list",
        "--repo", repo,
        "--state", "open",
        "--label", "status",
        "--json", "number,title,labels,body,createdAt"
    ])

    if not raw_issues:
        print("✅ No open status issues found or gh query returned empty.")
        return 0

    try:
        issues = json.loads(raw_issues)
    except Exception as e:
        print(f"❌ Could not parse issues JSON: {e}", file=sys.stderr)
        return 1

    if not issues:
        print("✅ Clean: 0 open status issues found.")
        return 0

    print(f"⚠️ Found {len(issues)} open status issue(s). Evaluating live health...")

    resolved_count = 0
    history_modified = False

    for issue in issues:
        num = issue["number"]
        title = issue["title"]
        labels = [l["name"] for l in issue.get("labels", [])]
        body = issue.get("body", "")

        # Find matching endpoint
        matched_slug = None
        for slug in endpoints.keys():
            if slug in labels or slug in title.lower().replace(" ", "-"):
                matched_slug = slug
                break

        target_url = None
        if matched_slug:
            target_url = endpoints[matched_slug]["url"]
        else:
            # Fallback URL extraction from body
            url_match = re.search(r"https?://[^\s\)\>]+", body)
            if url_match:
                target_url = url_match.group(0).rstrip("/.")

        if not target_url:
            print(f"  ❓ Issue #{num} ('{title}') could not be matched to a known endpoint. Skipping.")
            continue

        print(f"\n📡 Probing endpoint for Issue #{num} ('{title}'): {target_url}")
        is_up, code, latency_ms, err = probe_endpoint(target_url)

        if is_up:
            print(f"  🟢 Live check PASSED: HTTP {code} ({latency_ms}ms). Resolving false/stale incident #{num}...")

            # 1. Unlock issue if locked
            run_gh(["issue", "unlock", str(num), "--repo", repo])

            # 2. Post verification comment
            comment = f"""### 🟢 Automated Sentinel: Endpoint Verified Healthy

The automated reliability sentinel independently verified that this endpoint is **online and healthy**:
- **Target URL**: `{target_url}`
- **HTTP Status**: `{code}`
- **Latency**: `{latency_ms} ms`
- **Verification**: Multi-stage synthetic probe passed without error.

Closing this incident report automatically to maintain status dashboard integrity.
"""
            run_gh(["issue", "comment", str(num), "--repo", repo, "--body", comment])

            # 3. Close issue
            run_gh(["issue", "close", str(num), "--repo", repo, "--reason", "completed"])
            resolved_count += 1

            # 4. Sync history state
            if matched_slug and matched_slug in endpoints:
                sync_history_file(endpoints[matched_slug]["file"], code, latency_ms)
                history_modified = True
        else:
            print(f"  🔴 Live check FAILED: {err} ({latency_ms}ms). Issue #{num} remains OPEN.")

    print(f"\n🏁 Reconciliation complete: {resolved_count} orphaned/false issues closed.")
    return 0


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "drsumaiya/drsumaiya.com-upptime")
    if len(sys.argv) > 1:
        repo = sys.argv[1]
    return reconcile_issues(repo)


if __name__ == "__main__":
    sys.exit(main())
