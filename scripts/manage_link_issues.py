#!/usr/bin/env python3
"""
manage_link_issues.py - Broken Link Incident Management Lifecycle.

Monitors links/latest.json and manages GitHub incident issues:
- Automatically creates an incident issue tagged `link-incident`, `incident`, and `{slug}` when broken links or 404s are discovered.
- Deduplicates against existing open issues, updating with weekly scan deltas.
- Automatically resolves and closes the issue once all links recover.
"""

import os
import sys
import json
import subprocess

# Ensure UTF-8 output across all operating systems
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def run_gh(args):
    """Run a gh CLI command and return stdout string, or empty string on failure."""
    try:
        res = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"gh command failed: {e.stderr.strip()}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"Error running gh: {e}", file=sys.stderr)
        return ""


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "drsumaiya/drsumaiya.com-upptime")
    if len(sys.argv) > 1:
        repo = sys.argv[1]

    results_file = "links/latest.json"
    if not os.path.isfile(results_file):
        print(f"File {results_file} not found. Run aggregate_link_reports.py first.")
        return 1

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("timestamp_human", "Unknown UTC")
    results = data.get("results", [])

    for r in results:
        name = r["site"]
        slug = r["slug"]
        url = r["url"]
        failed = r.get("failed", 0)
        total = r.get("total_checked", 0)
        is_clean = r.get("is_clean", True)
        broken_links = r.get("broken_links", [])

        print(f"\nEvaluating Link Incident Status for: {name} ({slug})")

        # Query existing open issue for this slug
        raw_issues = run_gh([
            "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", "link-incident",
            "--label", slug,
            "--json", "number,title"
        ])
        existing_issues = []
        if raw_issues:
            try:
                existing_issues = json.loads(raw_issues)
            except Exception:
                existing_issues = []

        existing_number = existing_issues[0]["number"] if existing_issues else None

        if not is_clean:
            print(f"❌ Broken link degradation detected for {name} ({failed} broken link(s) out of {total}).")

            # Build markdown table of broken links (capped at 25 for issue body readability)
            table_rows = []
            for b in broken_links[:25]:
                src = b.get("source", "N/A")
                tgt = b.get("url", "N/A")
                status = b.get("status", 404)
                err = b.get("error", "Dead Link")
                table_rows.append(f"| [{src}]({src}) | `{tgt}` | `{status}` | {err} |")

            table_md = "\n".join(table_rows)
            more_note = f"\n*...and {len(broken_links) - 25} more broken link(s). See `links/summary.md` for full log.*" if len(broken_links) > 25 else ""

            body = f"""### 🚨 Broken Links & 404 Sentinel Alert for **{name}**

An automated weekly deep-crawl detected broken hyperlinks, 404 Not Found errors, or dead redirects on [{name}]({url}):

#### 📋 Audit Summary:
- **Property**: [{name}]({url})
- **Total Links Checked**: `{total:,}`
- **Broken / Dead Links**: `{failed}`
- **Scan Timestamp**: `{timestamp}`

#### ❌ Faulty Links Log:
| Source Page | Target Broken URL | HTTP Status | Details |
| :--- | :--- | :---: | :--- |
{table_md}
{more_note}

#### 🛠️ Recommended Remediation:
1. Review the source pages listed above in WordPress or code base.
2. Update dead external links to current live URLs, or replace with suitable alternatives.
3. For internal 404s, set up a 301 redirect in your Redirection plugin or update the page href.
4. Verify link accessibility in your browser.

---
*Reported automatically at `{timestamp}` by Broken Link Sentinel CI. This incident will automatically close once all links are verified healthy.*
"""

            if existing_number:
                print(f"Updating existing open link incident #{existing_number}...")
                comment = f"""**Weekly Broken Link Sentinel Update (`{timestamp}`):**
- **Status**: ❌ **{failed} broken link(s) remain active.**
- **Total Links Audited**: `{total:,}`

#### Active Faults Sample:
| Source Page | Target Broken URL | HTTP Status | Details |
| :--- | :--- | :---: | :--- |
{table_md}
{more_note}

*Issue remains open until all links recover.*
"""
                run_gh([
                    "issue", "comment", str(existing_number),
                    "--repo", repo,
                    "--body", comment
                ])
            else:
                print(f"Creating new link incident issue for {name}...")
                title = f"🚨 Broken Links Alert: {name} ({failed} dead link(s) detected)"
                labels = f"link-incident,incident,{slug}"
                run_gh([
                    "issue", "create",
                    "--repo", repo,
                    "--title", title,
                    "--body", body,
                    "--label", labels
                ])
        else:
            print(f"✅ All audited links healthy for {name} ({total:,} links checked).")
            if existing_number:
                print(f"Resolving and closing link incident #{existing_number}...")
                resolve_comment = f"""**✅ Resolved:** All hyperlinks on **{name}** have been verified healthy!

- **Total Links Audited**: `{total:,}`
- **Broken Links**: `0`
- **Scan Timestamp**: `{timestamp}`

*Closed automatically by Broken Link Sentinel CI.*
"""
                run_gh([
                    "issue", "close", str(existing_number),
                    "--repo", repo,
                    "--comment", resolve_comment
                ])

    return 0


if __name__ == "__main__":
    sys.exit(main())
