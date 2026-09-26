#!/usr/bin/env python3
"""
record_page_popularity.py - Content Popularity & Daily Page Views Telemetry

Queries the secure Upptime Telemetry endpoint across monitored web properties
(drsumaiya.com, iqs.org.in, etc.) to record daily views per blog post and page.
Generates:
  - popularity/latest.json (live dashboard snapshot)
  - popularity/summary.md  (human-readable markdown digest & step summary)
  - popularity/history.jsonl (append-only time-series for trend tracking)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure UTF-8 output on all platforms
sys.stdout.reconfigure(encoding="utf-8")

UPPTIME_SECRET = os.environ.get("UPPTIME_WAF_SECRET", "").strip()

TARGETS = [
    {
        "name": "DrSumaiya.com",
        "slug": "dr-sumaiya-com",
        "domain": "https://drsumaiya.com",
        "endpoint": "https://drsumaiya.com/wp-json/upptime/v1/page-views",
    },
    {
        "name": "IQS",
        "slug": "iqs",
        "domain": "https://iqs.org.in",
        "endpoint": "https://iqs.org.in/wp-json/upptime/v1/page-views",
    }
]

DEFAULT_TIMEOUT = 15

def fetch_telemetry(endpoint: str, days: int = 1, limit: int = 50, date: str = None) -> dict:
    timestamp_param = int(time.time())
    url = f"{endpoint}?days={days}&limit={limit}&_t={timestamp_param}"
    if date:
        url += f"&date={date}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; UpptimePopularityBot/1.0)",
        "Accept": "application/json",
    }
    if UPPTIME_SECRET:
        headers["X-Upptime-Token"] = UPPTIME_SECRET

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                return payload
            else:
                print(f"⚠️ Unexpected status {response.status} from {url}", file=sys.stderr)
                return {}
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code} fetching {url}: {e.reason}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"❌ Connection error fetching {url}: {e}", file=sys.stderr)
        return {}

def process_target(target: dict, timestamp: str) -> dict:
    print(f"\n📡 Querying views telemetry for {target['name']}...")
    yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    data_1d = fetch_telemetry(target["endpoint"], days=1, limit=60, date=yesterday_str)
    # If completed day returned no items, query current 24-48h window
    if not data_1d.get("pages"):
        data_1d = fetch_telemetry(target["endpoint"], days=1, limit=60)
    data_7d = fetch_telemetry(target["endpoint"], days=7, limit=60)

    site_result = {
        "name": target["name"],
        "slug": target["slug"],
        "domain": target["domain"],
        "status": "online" if data_1d.get("status") == "ok" else "unavailable",
        "timestamp": timestamp,
        "views_24h": data_1d.get("total_views", 0),
        "views_7d": data_7d.get("total_views", 0),
        "pages_24h": [],
        "posts_24h": [],
        "all_items_24h": data_1d.get("pages", []),
        "all_items_7d": data_7d.get("pages", []),
    }

    # Partition 24h items into posts (blogs/articles) and pages/forms
    for item in data_1d.get("pages", []):
        ptype = item.get("type", "other")
        if ptype in ("page", "home"):
            site_result["pages_24h"].append(item)
        else:
            # 'post' or custom post types (services, courses, resources)
            site_result["posts_24h"].append(item)

    # Sort descending by views
    site_result["posts_24h"].sort(key=lambda x: x.get("views", 0), reverse=True)
    site_result["pages_24h"].sort(key=lambda x: x.get("views", 0), reverse=True)

    print(f"  ✓ Total 24h Views: {site_result['views_24h']} | 7d Views: {site_result['views_7d']}")
    print(f"  ✓ Tracked {len(site_result['posts_24h'])} blog posts, {len(site_result['pages_24h'])} pages in last 24h")
    return site_result

def build_summary_markdown(results: list, timestamp: str) -> str:
    lines = [
        "# 📈 Daily Page Views & Content Popularity Report",
        f"*Audit Timestamp: `{timestamp}` • Automated telemetry via Origin Stats Engine*",
        "",
        "| Monitored Property | Health Status | 24h Views | 7-Day Views | Top Performing Article (24h) |",
        "| :--- | :---: | :---: | :---: | :--- |"
    ]

    for site in results:
        status_badge = "🟢 Live" if site["status"] == "online" else "🔴 Offline"
        v24 = f"**{site['views_24h']:,}**"
        v7 = f"{site['views_7d']:,}"
        
        top_post = "None recorded"
        if site["posts_24h"]:
            first = site["posts_24h"][0]
            title = first.get("title") or "Untitled"
            url = first.get("url") or "#"
            views = first.get("views", 0)
            top_post = f"[{title[:55]}...]({url}) ({views} views)" if len(title) > 55 else f"[{title}]({url}) ({views} views)"
        elif site["all_items_24h"]:
            first = site["all_items_24h"][0]
            title = first.get("title") or "Untitled"
            url = first.get("url") or "#"
            views = first.get("views", 0)
            top_post = f"[{title}]({url}) ({views} views)"

        lines.append(f"| **{site['name']}** | {status_badge} | {v24} | {v7} | {top_post} |")

    lines.append("")

    for site in results:
        lines.append(f"## 🏆 {site['name']} — Top Performing Content")
        lines.append("")
        
        # Blog Posts Table
        lines.append("### 📝 Top Blog Posts (Last 24 Hours)")
        if site["posts_24h"]:
            lines.append("| Rank | Blog Post Title | Views | URL |")
            lines.append("| :---: | :--- | :---: | :--- |")
            for idx, p in enumerate(site["posts_24h"][:10], start=1):
                title = p.get("title") or "Untitled"
                views = p.get("views", 0)
                url = p.get("url") or ""
                lines.append(f"| **#{idx}** | {title} | **{views}** | [Read Post]({url}) |")
        else:
            lines.append("*No dedicated blog post views recorded in the last 24h window.*")
        lines.append("")

        # Core Pages Table
        lines.append("### 📄 Top Pages & Intake Forms (Last 24 Hours)")
        if site["pages_24h"]:
            lines.append("| Rank | Page Title | Views | URL |")
            lines.append("| :---: | :--- | :---: | :--- |")
            for idx, p in enumerate(site["pages_24h"][:10], start=1):
                title = p.get("title") or "Untitled"
                views = p.get("views", 0)
                url = p.get("url") or ""
                lines.append(f"| **#{idx}** | {title} | **{views}** | [Visit Page]({url}) |")
        else:
            lines.append("*No core page views recorded in the last 24h window.*")
        lines.append("")

    lines.append("---")
    lines.append("*Telemetry gathered automatically via Upptime Content Popularity Engine.*")
    return "\n".join(lines) + "\n"

def main() -> int:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    out_dir = Path("popularity")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for target in TARGETS:
        res = process_target(target, timestamp)
        results.append(res)

    # 1. Write latest.json
    latest_payload = {
        "timestamp": timestamp,
        "sites": results
    }
    with open(out_dir / "latest.json", "w", encoding="utf-8") as f:
        json.dump(latest_payload, f, indent=2)

    # 2. Write summary.md
    summary_md = build_summary_markdown(results, timestamp)
    with open(out_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)

    # 3. Append to history.jsonl
    with open(out_dir / "history.jsonl", "a", encoding="utf-8") as f:
        for site in results:
            hist_entry = {
                "timestamp": timestamp,
                "slug": site["slug"],
                "views_24h": site["views_24h"],
                "views_7d": site["views_7d"],
                "top_posts": site["posts_24h"][:5],
                "top_pages": site["pages_24h"][:5],
            }
            f.write(json.dumps(hist_entry) + "\n")

    print(f"\n✅ Content popularity audit finished successfully. Telemetry saved to {out_dir}/")
    return 0

if __name__ == "__main__":
    sys.exit(main())
