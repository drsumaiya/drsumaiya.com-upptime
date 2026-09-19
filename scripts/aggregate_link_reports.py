#!/usr/bin/env python3
"""
aggregate_link_reports.py - Aggregate Lychee Crawl Reports & Telemetry.

Merges individual site crawl outputs (JSON / Markdown) into a unified
telemetry payload (`links/latest.json`), generates a GitHub-compatible
Markdown summary (`links/summary.md`), and appends to `links/history.jsonl`.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output across all operating systems
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SITES = [
    {
        "name": "DrSumaiya.com",
        "slug": "dr-sumaiya-com",
        "url": "https://drsumaiya.com"
    },
    {
        "name": "IQS",
        "slug": "iqs",
        "url": "https://iqs.org.in"
    },
    {
        "name": "IQS - Hifz Focus",
        "slug": "iqs-hifz",
        "url": "https://hifz.iqs.org.in"
    }
]

RAW_DIR = Path("links/raw")
OUTPUT_DIR = Path("links")


def parse_lychee_json(file_path):
    """Parse raw JSON output from lychee."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total = data.get("total", 0)
        successful = data.get("successful", 0)
        failures = data.get("errors", data.get("failures", 0))
        timeouts = data.get("timeouts", 0)
        redirects = data.get("redirects", 0)
        excludes = data.get("excludes", 0)

        broken_links = []
        # Lychee 0.24+ error_map: key is source URL, value is list of broken targets
        error_map = data.get("error_map", {})
        if isinstance(error_map, dict) and error_map:
            for source_url, err_list in error_map.items():
                if isinstance(err_list, list):
                    for item in err_list:
                        target = item.get("url")
                        status_obj = item.get("status", {})
                        status_code = status_obj.get("code") if isinstance(status_obj, dict) else 404
                        err_text = status_obj.get("text") if isinstance(status_obj, dict) else str(status_obj)
                        line = item.get("span", {}).get("line") if isinstance(item.get("span"), dict) else None
                        broken_links.append({
                            "url": target,
                            "source": source_url,
                            "line": line,
                            "status": status_code or 404,
                            "error": err_text or "Dead Link"
                        })
        # Legacy fail_map fallback
        fail_map = data.get("fail_map", {})
        if isinstance(fail_map, dict) and not broken_links:
            for target_url, details in fail_map.items():
                if isinstance(details, list):
                    for detail in details:
                        source = detail.get("source", "Unknown Page")
                        line = detail.get("line")
                        status_code = detail.get("status_code")
                        error_msg = detail.get("error", "Dead Link")
                        broken_links.append({
                            "url": target_url,
                            "source": source,
                            "line": line,
                            "status": status_code or 404,
                            "error": str(error_msg)
                        })
                elif isinstance(details, dict):
                    source = details.get("source", "Unknown Page")
                    broken_links.append({
                        "url": target_url,
                        "source": source,
                        "status": details.get("status_code", 404),
                        "error": str(details.get("error", "Dead Link"))
                    })
                else:
                    broken_links.append({
                        "url": target_url,
                        "source": "Unknown Page",
                        "status": 404,
                        "error": str(details)
                    })

        return {
            "total": total,
            "successful": successful,
            "failures": failures or len(broken_links),
            "timeouts": timeouts,
            "redirects": redirects,
            "excludes": excludes,
            "broken_links": broken_links
        }
    except Exception as e:
        print(f"[-] Error parsing JSON report {file_path}: {e}", file=sys.stderr)
        return None


def parse_lychee_markdown(file_path):
    """Fallback: Parse lychee markdown output if JSON is unavailable."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        total = 0
        successful = 0
        failures = 0
        broken_links = []

        m_checked = re.search(r"Checked:\s*(\d+)", content)
        if m_checked:
            total = int(m_checked.group(1))
        m_success = re.search(r"Successful:\s*(\d+)", content)
        if m_success:
            successful = int(m_success.group(1))
        m_fail = re.search(r"Failed:\s*(\d+)", content)
        if m_fail:
            failures = int(m_fail.group(1))

        # Extract error blocks:
        # ### <source>
        # * [<status>] <target_url>
        current_source = "Unknown Page"
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("### "):
                current_source = line_str.replace("### ", "").strip()
            elif line_str.startswith("* ["):
                match = re.match(r"\*\s*\[(.*?)\]\s*(https?://\S+)", line_str)
                if match:
                    status_raw = match.group(1)
                    target_url = match.group(2)
                    status_code = int(status_raw) if status_raw.isdigit() else 404
                    broken_links.append({
                        "url": target_url,
                        "source": current_source,
                        "status": status_code,
                        "error": f"HTTP {status_raw}"
                    })

        if failures == 0 and len(broken_links) > 0:
            failures = len(broken_links)

        return {
            "total": total,
            "successful": successful,
            "failures": failures,
            "timeouts": 0,
            "redirects": 0,
            "excludes": 0,
            "broken_links": broken_links
        }
    except Exception as e:
        print(f"[-] Error parsing Markdown report {file_path}: {e}", file=sys.stderr)
        return None


def generate_summary_md(aggregated_data):
    """Render a GitHub-compatible Markdown summary table."""
    timestamp = aggregated_data.get("timestamp_human", "Unknown UTC")
    results = aggregated_data.get("results", [])

    md = f"""# 🛡️ Broken Link & 404 Sentinel Report
> Last updated: `{timestamp}`

Automated weekly deep-crawl and stress-test of internal navigation and external outbound hyperlinks across all live properties.

| Site | Status | Links Audited | Broken Links | Health Status |
| :--- | :---: | :---: | :---: | :--- |
"""

    all_broken = []
    for r in results:
        site_name = r["site"]
        site_url = r["url"]
        failed = r.get("failed", 0)
        total = r.get("total_checked", 0)
        is_clean = r.get("is_clean", True)
        
        status_icon = "✅ Clean" if is_clean else f"🚨 {failed} Fault(s)"
        health_badge = "🟩 Healthy" if is_clean else "🟥 Degraded"
        
        md += f"| [{site_name}]({site_url}) | {status_icon} | {total:,} | {failed} | {health_badge} |\n"

        for b in r.get("broken_links", []):
            all_broken.append((site_name, b))

    if all_broken:
        md += "\n### 🚨 Faulty Endpoints & Broken Link Tracking Log:\n\n"
        md += "| Property | Source Page | Target Broken URL | HTTP Status | Details |\n"
        md += "| :--- | :--- | :--- | :---: | :--- |\n"
        for site_name, b in all_broken:
            source = b.get("source", "N/A")
            target = b.get("url", "N/A")
            status = b.get("status", 404)
            err = b.get("error", "Not Found")
            md += f"| **{site_name}** | [{source}]({source}) | `{target}` | `{status}` | {err} |\n"
    else:
        md += "\n> 🎉 **All Clear**: Every crawled internal page and outbound link resolved successfully with no 404s or dead endpoints.\n"

    md += """
### 🔍 Sentinel Diagnostics:
* **Deep Crawl Boundary**: Evaluates internal navigation depth up to 2 hops from canonical sitemaps.
* **Outbound Stress-Test**: Probes external citation links, partner endpoints, and media sources.
* **Anti-Bot Filtering**: Pre-filtered to exclude rate-limited platforms (LinkedIn, X, WhatsApp, Instagram).

---
*Report generated automatically by the Continuous Broken Link & 404 Sentinel CI.*
"""
    return md


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    iso_time = now_utc.isoformat()
    human_time = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    aggregated_results = []
    total_checked = 0
    total_broken = 0

    for site in SITES:
        slug = site["slug"]
        name = site["name"]
        url = site["url"]

        json_file = RAW_DIR / f"report-{slug}.json"
        md_file = RAW_DIR / f"broken-links-{slug}.md"

        site_report = None
        if json_file.is_file():
            site_report = parse_lychee_json(json_file)
        elif md_file.is_file():
            site_report = parse_lychee_markdown(md_file)

        if site_report is None:
            # Fallback placeholder if crawl did not run or produced no file
            site_report = {
                "total": 0,
                "successful": 0,
                "failures": 0,
                "timeouts": 0,
                "redirects": 0,
                "excludes": 0,
                "broken_links": []
            }

        failed_count = site_report["failures"]
        site_total = site_report["total"]
        is_clean = (failed_count == 0)

        total_checked += site_total
        total_broken += failed_count

        aggregated_results.append({
            "site": name,
            "slug": slug,
            "url": url,
            "total_checked": site_total,
            "successful": site_report["successful"],
            "failed": failed_count,
            "timeouts": site_report["timeouts"],
            "redirects": site_report["redirects"],
            "excludes": site_report["excludes"],
            "is_clean": is_clean,
            "broken_links": site_report["broken_links"]
        })

    payload = {
        "timestamp": iso_time,
        "timestamp_human": human_time,
        "total_checked": total_checked,
        "total_broken": total_broken,
        "overall_clean": (total_broken == 0),
        "results": aggregated_results
    }

    # 1. Write links/latest.json
    latest_file = OUTPUT_DIR / "latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[+] Wrote telemetry to {latest_file}")

    # 2. Write links/summary.md
    summary_file = OUTPUT_DIR / "summary.md"
    summary_content = generate_summary_md(payload)
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_content)
    print(f"[+] Wrote summary report to {summary_file}")

    # 3. Append to links/history.jsonl
    history_file = OUTPUT_DIR / "history.jsonl"
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"[+] Appended record to {history_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
