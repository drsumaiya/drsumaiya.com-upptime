#!/usr/bin/env python3
"""
SEO & Search Engine Indexing Health Verification
Validates robots.txt rules (detects accidental Disallow: /)
and XML Sitemap integrity (well-formedness, sub-sitemaps reachability).
"""

import os
import sys
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

TARGETS = [
    {
        "name": "DrSumaiya.com",
        "domain": "https://drsumaiya.com",
        "robots_url": "https://drsumaiya.com/robots.txt",
        "sitemap_url": "https://drsumaiya.com/sitemap_index.xml",
        "slug": "dr-sumaiya-com"
    },
    {
        "name": "IQS",
        "domain": "https://iqs.org.in",
        "robots_url": "https://iqs.org.in/robots.txt",
        "sitemap_url": "https://iqs.org.in/wp-sitemap.xml",
        "slug": "iqs"
    },
    {
        "name": "IQS - Hifz Focus",
        "domain": "https://hifz.iqs.org.in",
        "robots_url": "https://hifz.iqs.org.in/robots.txt",
        "sitemap_url": "https://hifz.iqs.org.in/sitemap.xml",
        "slug": "iqs-hifz"
    }
]

WAF_TOKEN = os.environ.get("UPPTIME_WAF_SECRET")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 SEO-Health-Bot/1.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
if WAF_TOKEN:
    HEADERS['X-Upptime-Token'] = WAF_TOKEN

def verify_robots(target):
    result = {
        "status": None,
        "valid": False,
        "disallow_all": False,
        "sitemap_directive": None,
        "errors": [],
        "warnings": []
    }
    try:
        req = urllib.request.Request(target["robots_url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as res:
            result["status"] = res.status
            content = res.read().decode('utf-8', errors='ignore')
            result["valid"] = True
            
            lines = [l.strip() for l in content.splitlines()]
            current_agent = None
            for line in lines:
                lower = line.lower()
                if lower.startswith("user-agent:"):
                    current_agent = line.split(":", 1)[1].strip()
                elif lower.startswith("disallow:"):
                    rule = line.split(":", 1)[1].strip()
                    if rule == "/" and (current_agent == "*" or current_agent is None):
                        result["disallow_all"] = True
                        result["errors"].append("CRITICAL: 'Disallow: /' directive detected for all user-agents. Entire site is blocked from Google indexing!")
                elif lower.startswith("sitemap:"):
                    raw_sitemap = line.split(":", 1)[1].strip()
                    if "http" in line:
                        raw_sitemap = line[line.find("http"):].strip()
                    elif raw_sitemap.startswith("/"):
                        raw_sitemap = target["domain"].rstrip("/") + raw_sitemap
                    result["sitemap_directive"] = raw_sitemap

            if not result["sitemap_directive"]:
                result["warnings"].append("No 'Sitemap:' declaration found in robots.txt.")
    except Exception as e:
        result["errors"].append(f"robots.txt fetch failed: {e}")
        
    return result

def verify_sitemap(target):
    result = {
        "status": None,
        "valid": False,
        "has_leading_whitespace": False,
        "child_sitemaps_count": 0,
        "urls_count": 0,
        "child_sitemaps_probed": [],
        "errors": [],
        "warnings": []
    }
    try:
        req = urllib.request.Request(target["sitemap_url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as res:
            result["status"] = res.status
            raw_bytes = res.read()
            
            if raw_bytes.startswith(b'\r\n') or raw_bytes.startswith(b'\n') or raw_bytes.startswith(b' '):
                result["has_leading_whitespace"] = True
                result["warnings"].append("XML Sitemap has leading whitespace/newline before '<?xml'. Strict XML parsers or Google Search Console may flag this.")

            # Parse XML (strip leading whitespace for tolerant parsing)
            clean_bytes = raw_bytes.strip()
            root = ET.fromstring(clean_bytes)
            tag = root.tag.lower()
            
            if "sitemapindex" in tag:
                children = root.findall("{*}sitemap")
                result["child_sitemaps_count"] = len(children)
                result["valid"] = True
                
                # Probe up to 3 child sitemaps to verify they don't 404
                for child in children[:3]:
                    loc = child.find("{*}loc")
                    if loc is not None and loc.text:
                        child_url = loc.text.strip()
                        try:
                            c_req = urllib.request.Request(child_url, headers=HEADERS)
                            with urllib.request.urlopen(c_req, timeout=15) as c_res:
                                result["child_sitemaps_probed"].append({
                                    "url": child_url,
                                    "status": c_res.status,
                                    "ok": True
                                })
                        except Exception as ce:
                            result["child_sitemaps_probed"].append({
                                "url": child_url,
                                "status": None,
                                "ok": False,
                                "error": str(ce)
                            })
                            result["errors"].append(f"Child sitemap {child_url} is unreachable: {ce}")
            elif "urlset" in tag:
                urls = root.findall("{*}url")
                result["urls_count"] = len(urls)
                result["valid"] = True
            else:
                result["errors"].append(f"Unexpected XML root element: {root.tag}")
    except Exception as e:
        result["errors"].append(f"Sitemap fetch / parse failed: {e}")
        
    return result

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs("seo", exist_ok=True)
    
    summary_lines = [
        "# 🤖 Search Engine Indexing & SEO Health Report",
        f"> Last updated: `{timestamp}`",
        "",
        "Automated daily audit of `robots.txt` directives (de-indexing guard) and XML Sitemaps.",
        "",
        "| Site | robots.txt | Sitemap | Indexing Status | Details |",
        "| :--- | :---: | :---: | :---: | :--- |"
    ]
    
    all_results = []
    has_critical_error = False

    for target in TARGETS:
        print(f"\n--- Checking SEO Health: {target['name']} ---")
        robots_res = verify_robots(target)
        sitemap_res = verify_sitemap(target)
        
        target_errors = robots_res["errors"] + sitemap_res["errors"]
        target_warnings = robots_res["warnings"] + sitemap_res["warnings"]
        
        is_ok = len(target_errors) == 0
        if not is_ok:
            has_critical_error = True
            
        status_badge = "🟩 Healthy" if is_ok else "🟥 Degraded"
        robots_badge = "✅ OK" if robots_res["valid"] and not robots_res["disallow_all"] else "❌ Failed"
        if sitemap_res["valid"]:
            if sitemap_res["child_sitemaps_count"] > 0:
                sitemap_badge = f"✅ Valid ({sitemap_res['child_sitemaps_count']} sub-sitemaps)"
            else:
                sitemap_badge = f"✅ Valid ({sitemap_res['urls_count']} URLs)"
        else:
            sitemap_badge = "❌ Broken"
        
        detail_msg = []
        if robots_res["disallow_all"]:
            detail_msg.append("🚨 'Disallow: /' Active!")
        if target_errors:
            detail_msg.extend(target_errors)
        elif target_warnings:
            detail_msg.extend(target_warnings)
        else:
            detail_msg.append("All directives & sitemaps verified.")
            
        summary_lines.append(
            f"| **{target['name']}** | {robots_badge} | {sitemap_badge} | {status_badge} | {' '.join(detail_msg)} |"
        )
        
        record = {
            "site": target["name"],
            "slug": target["slug"],
            "timestamp": timestamp,
            "robots": robots_res,
            "sitemap": sitemap_res,
            "is_ok": is_ok,
            "errors": target_errors,
            "warnings": target_warnings
        }
        all_results.append(record)
        
        print(f"Robots: {robots_badge} | Sitemap: {sitemap_badge} | Status: {status_badge}")
        if target_errors:
            print("Errors:", target_errors)
        if target_warnings:
            print("Warnings:", target_warnings)

    summary_lines.append("")
    summary_lines.append("### Diagnostic Rules:")
    summary_lines.append("* **Robots.txt De-Indexing Guard**: Verifies that `Disallow: /` is NOT present for `User-agent: *`.")
    summary_lines.append("* **XML Sitemap Validation**: Confirms well-formed XML syntax, sitemap declarations, and sub-sitemap reachability.")
    summary_lines.append("")
    summary_lines.append("---")
    summary_lines.append("*Report generated by SEO Health CI.*")

    # Write summary.md
    with open("seo/summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")
        
    # Append to history.jsonl
    with open("seo/history.jsonl", "a", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")
            
    payload = {
        "timestamp": timestamp,
        "has_critical_error": has_critical_error,
        "results": all_results
    }
    with open("seo/latest.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    if os.name != 'nt':
        with open("/tmp/seo_results.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    print("\nSEO verification completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
