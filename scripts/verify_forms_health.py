#!/usr/bin/env python3
"""
verify_forms_health.py - Lead Intake & Form Submission Endpoints Synthetic Health Prober.

Audits form pages, DOM integrity, REST submission endpoints, and critical styling/script
assets across DrSumaiya, IQS, and Hifz Focus to catch silent failures (plugin deactivations,
expired nonces, broken form actions, missing assets, or CDN routing errors).
"""

import sys
import json
import re
import time
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output across all operating systems
sys.stdout.reconfigure(encoding="utf-8")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 SyntheticFormHealthBot/1.0"
DEFAULT_TIMEOUT = 12

SSL_CTX = ssl.create_default_context()

FORM_TARGETS = [
    {
        "id": "drsumaiya-inquiry",
        "name": "DrSumaiya - Consultation Inquiry Form",
        "page_url": "https://drsumaiya.com/inquiry-form/",
        "dom_checks": {
            "form_pattern": r'<form\b[^>]*class=["\'][^"\']*nutricareLeadForm[^"\']*["\']',
            "required_inputs": ["name", "phone", "email", "lead_id"]
        },
        "submission_endpoint": {
            "url": "https://drsumaiya.com/wp-json/nutricare/v1/submit",
            "method": "OPTIONS",
            "expected_status": 200,
            "required_allow_method": "POST"
        },
        "static_assets": [
            "https://drsumaiya.com/wp-content/plugins/leadformplugin/basic_form_styling.css",
            "https://drsumaiya.com/wp-content/plugins/drsumaiyacoreplugin/assets/css/portal-common.css",
            "https://drsumaiya.com/wp-content/plugins/badgeplugin/assets/css/badge-styles.css"
        ],
        "discover_page_assets": True
    },
    {
        "id": "drsumaiya-booking",
        "name": "DrSumaiya - Patient History Form",
        "page_url": "https://drsumaiya.com/form/",
        "dom_checks": {
            "form_pattern": r'id=["\']formIframe["\']',
            "required_inputs": []
        },
        "iframe_target": {
            "url": "https://docs.google.com/forms/d/e/1FAIpQLSdOnU6NJUiOTLHouIEhRpnqIUiNV40TfUqFLdtuflvUulLkAg/viewform?embedded=true",
            "disallowed_content": [
                "This form is no longer accepting responses",
                "Page Not Found",
                "form has been moved to the trash",
                "form is no longer available",
                "You need permission"
            ]
        },
        "static_assets": [
            "https://drsumaiya.com/wp-content/plugins/leadformplugin/basic_form_styling.css"
        ],
        "discover_page_assets": False
    },
    {
        "id": "iqs-inquiry",
        "name": "IQS - Admissions & Course Inquiry Form",
        "page_url": "https://iqs.org.in/inquiry/",
        "dom_checks": {
            "form_pattern": r'<form\b[^>]*class=["\'][^"\']*iqs-inq-form[^"\']*["\']',
            "required_inputs": ["name", "phone", "email", "lead_id"]
        },
        "submission_endpoint": {
            "url": "https://iqs.org.in/wp-json/iqs/v1/inquiry",
            "method": "OPTIONS",
            "expected_status": 200,
            "required_allow_method": "POST"
        },
        "static_assets": [],
        "discover_page_assets": True
    },
    {
        "id": "hifz-onboarding",
        "name": "Hifz Focus - Student Onboarding Form",
        "page_url": "https://hifz.iqs.org.in/onboarding",
        "dom_checks": {
            "form_pattern": r'<form\b',
            "required_inputs": ["fullName", "email", "phone"]
        },
        "submission_endpoint": None,
        "static_assets": [],
        "discover_page_assets": True
    }
]


def http_request(url, method="GET", headers=None, timeout=DEFAULT_TIMEOUT):
    """Executes an HTTP request and measures latency."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method=method)
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as response:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            content = response.read()
            return {
                "success": True,
                "status_code": response.status,
                "latency_ms": latency_ms,
                "headers": dict(response.headers),
                "body": content,
                "error": None
            }
    except urllib.error.HTTPError as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        body = e.read()
        return {
            "success": False,
            "status_code": e.code,
            "latency_ms": latency_ms,
            "headers": dict(e.headers),
            "body": body,
            "error": f"HTTP {e.code}: {e.reason}"
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "headers": {},
            "body": b"",
            "error": str(e)
        }


def extract_form_assets(html_str, base_url):
    """Extracts CSS and JS assets specifically tied to forms from HTML."""
    assets = set()
    
    # CSS
    css_links = re.findall(r'<link\b[^>]*href=["\']([^"\']+\.css[^"\']*)["\']', html_str, re.I)
    for link in css_links:
        full_url = urllib.parse.urljoin(base_url, link)
        # Filter for form/plugin/portal assets
        if any(k in full_url.lower() for k in ["lead", "form", "portal", "badge", "chunk", "styles"]):
            assets.add(full_url)
            
    # Scripts
    scripts = re.findall(r'<script\b[^>]*src=["\']([^"\']+\.js[^"\']*)["\']', html_str, re.I)
    for sc in scripts:
        full_url = urllib.parse.urljoin(base_url, sc)
        if any(k in full_url.lower() for k in ["lead", "form", "portal", "chunk", "app", "main"]):
            assets.add(full_url)
            
    return sorted(list(assets))


def probe_target(target):
    """Executes end-to-end synthetic probe on a form target."""
    print(f"\n[INFO] Probing target: {target['name']} ({target['page_url']})")
    target_result = {
        "id": target["id"],
        "name": target["name"],
        "page_url": target["page_url"],
        "overall_status": "PASS",
        "failures": [],
        "checks": {}
    }
    
    # 1. Page Availability & DOM Inspection
    page_res = http_request(target["page_url"], method="GET")
    target_result["checks"]["page"] = {
        "url": target["page_url"],
        "status_code": page_res["status_code"],
        "latency_ms": page_res["latency_ms"],
        "status": "PASS" if page_res["status_code"] == 200 else "FAIL",
        "error": page_res["error"]
    }
    if page_res["status_code"] != 200:
        target_result["overall_status"] = "FAIL"
        target_result["failures"].append(f"Page returned HTTP {page_res['status_code']} instead of 200")
        return target_result
        
    html = page_res["body"].decode("utf-8", errors="ignore")
    
    # Check DOM form pattern
    form_pattern = target["dom_checks"]["form_pattern"]
    if not re.search(form_pattern, html, re.I):
        target_result["overall_status"] = "FAIL"
        target_result["failures"].append(f"DOM missing expected form container matching /{form_pattern}/")
        target_result["checks"]["dom_form"] = {"status": "FAIL", "pattern": form_pattern}
    else:
        target_result["checks"]["dom_form"] = {"status": "PASS", "pattern": form_pattern}
        
    # Check Required Inputs
    missing_inputs = []
    for inp in target["dom_checks"]["required_inputs"]:
        # Match input name="..." or id="..."
        pattern = rf'<(?:input|textarea|select)\b[^>]*name=["\']{re.escape(inp)}["\']'
        if not re.search(pattern, html, re.I):
            missing_inputs.append(inp)
            
    if missing_inputs:
        target_result["overall_status"] = "FAIL"
        target_result["failures"].append(f"Missing required form inputs: {', '.join(missing_inputs)}")
        target_result["checks"]["dom_inputs"] = {"status": "FAIL", "missing": missing_inputs}
    else:
        target_result["checks"]["dom_inputs"] = {"status": "PASS", "checked": target["dom_checks"]["required_inputs"]}

    # 2. Submission Endpoint Probe (if configured)
    sub = target.get("submission_endpoint")
    if sub:
        sub_res = http_request(sub["url"], method=sub["method"])
        allow_header = sub_res["headers"].get("Allow", "") or sub_res["headers"].get("allow", "")
        
        endpoint_ok = (sub_res["status_code"] == sub["expected_status"])
        if sub.get("required_allow_method") and sub["required_allow_method"] not in allow_header:
            endpoint_ok = False
            
        sub_status = "PASS" if endpoint_ok else "FAIL"
        target_result["checks"]["submission_endpoint"] = {
            "url": sub["url"],
            "method": sub["method"],
            "status_code": sub_res["status_code"],
            "latency_ms": sub_res["latency_ms"],
            "allow_header": allow_header,
            "status": sub_status,
            "error": sub_res["error"]
        }
        if not endpoint_ok:
            target_result["overall_status"] = "FAIL"
            err_msg = f"Submission endpoint {sub['url']} failed probe: HTTP {sub_res['status_code']} (Allow: '{allow_header}')"
            target_result["failures"].append(err_msg)

    # 3. Iframe Target Probe (if configured, e.g. embedded Google Forms)
    iframe_conf = target.get("iframe_target")
    if iframe_conf:
        iframe_res = http_request(iframe_conf["url"], method="GET")
        iframe_body = iframe_res["body"].decode("utf-8", errors="ignore")
        iframe_ok = (iframe_res["status_code"] == 200)
        
        disallowed_hit = None
        for dis in iframe_conf.get("disallowed_content", []):
            if dis in iframe_body:
                iframe_ok = False
                disallowed_hit = dis
                break
                
        iframe_status = "PASS" if iframe_ok else "FAIL"
        target_result["checks"]["iframe_target"] = {
            "url": iframe_conf["url"],
            "status_code": iframe_res["status_code"],
            "latency_ms": iframe_res["latency_ms"],
            "disallowed_content_found": disallowed_hit,
            "status": iframe_status,
            "error": iframe_res["error"]
        }
        if not iframe_ok:
            target_result["overall_status"] = "FAIL"
            target_result["failures"].append(f"Embedded iframe target failed: HTTP {iframe_res['status_code']} (Disallowed flag: {disallowed_hit})")

    # 4. Critical Asset Probing
    assets_to_probe = set(target.get("static_assets", []))
    if target.get("discover_page_assets"):
        discovered = extract_form_assets(html, target["page_url"])
        # Take up to 6 discovered assets to keep probe lightweight
        assets_to_probe.update(discovered[:6])
        
    asset_results = []
    for asset_url in sorted(assets_to_probe):
        a_res = http_request(asset_url, method="GET")
        a_ok = (a_res["status_code"] == 200 and len(a_res["body"]) > 0)
        a_status = "PASS" if a_ok else "FAIL"
        asset_info = {
            "url": asset_url,
            "status_code": a_res["status_code"],
            "bytes": len(a_res["body"]),
            "latency_ms": a_res["latency_ms"],
            "status": a_status,
            "error": a_res["error"]
        }
        asset_results.append(asset_info)
        if not a_ok:
            target_result["overall_status"] = "FAIL"
            target_result["failures"].append(f"Form asset failed: {asset_url} (HTTP {a_res['status_code']})")
            
    target_result["checks"]["assets"] = asset_results

    return target_result


def main():
    import urllib.parse
    start_all = time.time()
    results = []
    overall_exit_code = 0
    
    print("=" * 70)
    print("🚀 Lead Intake & Form Submission Endpoints Synthetic Health Prober")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    
    for target in FORM_TARGETS:
        res = probe_target(target)
        results.append(res)
        if res["overall_status"] != "PASS":
            overall_exit_code = 1
            print(f"  ❌ {target['name']}: FAIL -> {', '.join(res['failures'])}")
        else:
            print(f"  ✅ {target['name']}: PASS (Page: {res['checks']['page']['latency_ms']}ms)")

    # Prepare directories
    forms_dir = Path("forms")
    forms_dir.mkdir(parents=True, exist_ok=True)
    
    # Save latest.json
    telemetry = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_targets": len(results),
        "passed": sum(1 for r in results if r["overall_status"] == "PASS"),
        "failed": sum(1 for r in results if r["overall_status"] != "PASS"),
        "targets": results
    }
    
    latest_json = forms_dir / "latest.json"
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)
        
    # Generate summary.md
    summary_md = forms_dir / "summary.md"
    with open(summary_md, "w", encoding="utf-8") as f:
        f.write("# 📋 Lead Intake & Form Health Summary\n\n")
        f.write(f"**Last Probe Run:** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`  \n")
        f.write(f"**Total Targets:** {telemetry['total_targets']} | ")
        f.write(f"**Passed:** {telemetry['passed']} | ")
        f.write(f"**Failed:** {telemetry['failed']}\n\n")
        
        f.write("| Form Target | Page Status | Submission Route | Assets Verified | Health |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: |\n")
        
        for r in results:
            page_status = f"HTTP {r['checks']['page']['status_code']} ({r['checks']['page']['latency_ms']}ms)"
            
            sub = r['checks'].get('submission_endpoint')
            if sub:
                sub_status = f"`{sub['method']}` {sub['status_code']}"
            elif r['checks'].get('iframe_target'):
                sub_status = f"Iframe HTTP {r['checks']['iframe_target']['status_code']}"
            else:
                sub_status = "Client-side"
                
            assets_cnt = len(r['checks'].get('assets', []))
            health_badge = "🟢 **PASS**" if r["overall_status"] == "PASS" else "🔴 **FAIL**"
            
            f.write(f"| [{r['name']}]({r['page_url']}) | {page_status} | {sub_status} | {assets_cnt} assets | {health_badge} |\n")
            
        f.write("\n## Detailed Target Breakdown\n\n")
        for r in results:
            f.write(f"### {r['name']}\n")
            f.write(f"- **URL:** {r['page_url']}\n")
            f.write(f"- **DOM Container Status:** `{r['checks']['dom_form']['status']}`\n")
            f.write(f"- **Inputs Checked:** `{r['checks']['dom_inputs']['status']}`\n")
            
            if "submission_endpoint" in r["checks"]:
                s = r["checks"]["submission_endpoint"]
                f.write(f"- **REST Submission Route:** `{s['url']}` ({s['method']} -> HTTP {s['status_code']}, Allow: `{s.get('allow_header', '')}`)\n")
            if "iframe_target" in r["checks"]:
                ifr = r["checks"]["iframe_target"]
                f.write(f"- **Embedded Form Target:** `{ifr['url']}` (HTTP {ifr['status_code']})\n")
                
            if r["failures"]:
                f.write("\n> [!CAUTION]\n")
                for fail in r["failures"]:
                    f.write(f"> - ⚠️ {fail}\n")
                    
            f.write("\n")

    print("\n" + "=" * 70)
    print(f"Probe execution completed in {round((time.time() - start_all), 2)}s.")
    print(f"Results written to {latest_json} and {summary_md}")
    print("=" * 70)
    
    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
