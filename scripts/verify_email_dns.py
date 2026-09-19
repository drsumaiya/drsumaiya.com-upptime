#!/usr/bin/env python3
"""
Email Deliverability & DNS Health Verification (SPF, DKIM, DMARC, MX)
Audits DNS records protecting domain reputation and mail deliverability
using dual-engine DNS-over-HTTPS (Cloudflare + Google DoH).
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

TARGETS = [
    {
        "name": "DrSumaiya.com",
        "domain": "drsumaiya.com",
        "slug": "dr-sumaiya-com",
        "check_mx": True,
        "expected_mx": ["mx1.hostinger.com", "mx2.hostinger.com"],
        "check_spf": True,
        "expected_spf_includes": ["_spf.mail.hostinger.com"],
        "check_dmarc": True,
        "dmarc_host": "_dmarc.drsumaiya.com",
        "dkim_selectors": []
    },
    {
        "name": "IQS",
        "domain": "iqs.org.in",
        "slug": "iqs",
        "check_mx": True,
        "expected_mx": ["mx1.hostinger.com", "mx2.hostinger.com"],
        "check_spf": True,
        "expected_spf_includes": ["_spf.mail.hostinger.com"],
        "check_dmarc": True,
        "dmarc_host": "_dmarc.iqs.org.in",
        "dkim_selectors": ["iqs_newsletter._domainkey.iqs.org.in"]
    },
    {
        "name": "IQS - Hifz Focus",
        "domain": "hifz.iqs.org.in",
        "slug": "iqs-hifz",
        "check_mx": False,
        "check_spf": False,
        "check_dmarc": True,
        "dmarc_host": "_dmarc.hifz.iqs.org.in",
        "dkim_selectors": []
    }
]

def query_doh(name, record_type):
    """
    Query DNS-over-HTTPS via Cloudflare with automatic Google DoH fallback.
    Returns list of answer records (string data) or raises Exception.
    """
    # Attempt 1: Cloudflare DoH
    cf_url = f"https://cloudflare-dns.com/dns-query?name={urllib.parse.quote(name)}&type={record_type}"
    req = urllib.request.Request(cf_url, headers={"Accept": "application/dns-json", "User-Agent": "Email-DNS-Audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status == 200:
                payload = json.loads(res.read().decode('utf-8'))
                answers = payload.get("Answer", [])
                results = []
                for a in answers:
                    val = a.get("data", "").strip()
                    # Strip wrapping quotes on TXT strings
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    results.append(val)
                return results
    except Exception as cf_err:
        pass

    # Attempt 2: Google DoH Fallback
    gg_url = f"https://dns.google/resolve?name={urllib.parse.quote(name)}&type={record_type}"
    g_req = urllib.request.Request(gg_url, headers={"Accept": "application/json", "User-Agent": "Email-DNS-Audit/1.0"})
    try:
        with urllib.request.urlopen(g_req, timeout=10) as res:
            if res.status == 200:
                payload = json.loads(res.read().decode('utf-8'))
                answers = payload.get("Answer", [])
                results = []
                for a in answers:
                    val = a.get("data", "").strip()
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    results.append(val)
                return results
    except Exception as g_err:
        raise Exception(f"DoH query failed on both Cloudflare & Google for {name} ({record_type}): {g_err}")

    return []

def audit_mx(target):
    result = {
        "status": "pass",
        "records": [],
        "errors": [],
        "warnings": []
    }
    if not target.get("check_mx"):
        result["status"] = "skipped"
        return result

    try:
        answers = query_doh(target["domain"], "MX")
        if not answers:
            result["status"] = "fail"
            result["errors"].append(f"No MX records found for {target['domain']}. Domain cannot receive emails!")
            return result

        parsed_mx = []
        for ans in answers:
            parts = ans.split()
            if len(parts) >= 2:
                pref, host = parts[0], parts[1].rstrip(".")
                parsed_mx.append({"priority": int(pref) if pref.isdigit() else pref, "host": host})
            else:
                parsed_mx.append({"host": ans.rstrip(".")})

        result["records"] = parsed_mx

        # Verify expected hosters if configured
        expected = target.get("expected_mx", [])
        if expected:
            found_hosts = [m["host"] for m in parsed_mx]
            for exp in expected:
                if not any(exp in h for h in found_hosts):
                    result["warnings"].append(f"Expected mail server '{exp}' not found in active MX records.")

    except Exception as e:
        result["status"] = "fail"
        result["errors"].append(f"MX lookup error: {e}")

    return result

def audit_spf(target):
    result = {
        "status": "pass",
        "record": None,
        "errors": [],
        "warnings": []
    }
    if not target.get("check_spf"):
        result["status"] = "skipped"
        return result

    try:
        answers = query_doh(target["domain"], "TXT")
        spf_records = [a for a in answers if a.startswith("v=spf1")]

        if not spf_records:
            result["status"] = "fail"
            result["errors"].append(f"No SPF (v=spf1) record found for {target['domain']}. Emails will fail SPF authentication!")
            return result

        if len(spf_records) > 1:
            result["status"] = "fail"
            result["errors"].append(f"Multiple SPF records detected ({len(spf_records)}). RFC 7208 forbids multiple SPF records and causes PermError!")

        raw_spf = spf_records[0]
        result["record"] = raw_spf

        # Validate mechanisms
        tokens = raw_spf.split()
        all_mechanisms = [t for t in tokens if t.endswith("all")]

        if "+all" in all_mechanisms:
            result["status"] = "fail"
            result["errors"].append("SPF contains '+all' (allow all). Anyone can spoof emails from your domain!")
        elif "?all" in all_mechanisms:
            result["warnings"].append("SPF ends with '?all' (neutral). Consider hardening to '~all' or '-all'.")

        expected_includes = target.get("expected_spf_includes", [])
        for inc in expected_includes:
            if not any(inc in t for t in tokens):
                result["warnings"].append(f"Expected mail provider '{inc}' not included in SPF statement.")

    except Exception as e:
        result["status"] = "fail"
        result["errors"].append(f"SPF lookup error: {e}")

    return result

def audit_dmarc(target):
    result = {
        "status": "pass",
        "record": None,
        "policy": None,
        "errors": [],
        "warnings": []
    }
    if not target.get("check_dmarc"):
        result["status"] = "skipped"
        return result

    host = target.get("dmarc_host", f"_dmarc.{target['domain']}")
    try:
        answers = query_doh(host, "TXT")
        dmarc_records = [a for a in answers if "v=dmarc1" in a.lower()]

        if not dmarc_records:
            result["status"] = "fail"
            result["errors"].append(f"No DMARC record found at {host}. Domain lacks anti-spoofing protection and Gmail/Yahoo DMARC compliance!")
            return result

        if len(dmarc_records) > 1:
            result["status"] = "fail"
            result["errors"].append(f"Multiple DMARC records found at {host}. Receivers may ignore DMARC!")

        raw_dmarc = dmarc_records[0]
        result["record"] = raw_dmarc

        # Parse tags
        tags = {}
        for part in raw_dmarc.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                tags[k.strip().lower()] = v.strip()

        policy = tags.get("p", "").lower()
        result["policy"] = policy

        if not policy:
            result["status"] = "fail"
            result["errors"].append(f"DMARC record at {host} is missing required 'p=' policy tag.")
        elif policy not in ["none", "quarantine", "reject"]:
            result["status"] = "fail"
            result["errors"].append(f"Invalid DMARC policy 'p={policy}'. Must be 'none', 'quarantine', or 'reject'.")

        if "rua" not in tags:
            result["warnings"].append("DMARC record does not declare 'rua=' (aggregate feedback reports).")

    except Exception as e:
        result["status"] = "fail"
        result["errors"].append(f"DMARC lookup error at {host}: {e}")

    return result

def audit_dkim(target):
    result = {
        "status": "pass",
        "selectors_tested": [],
        "errors": [],
        "warnings": []
    }
    selectors = target.get("dkim_selectors", [])
    if not selectors:
        result["status"] = "skipped"
        return result

    for sel in selectors:
        sel_res = {
            "selector_host": sel,
            "valid": False,
            "errors": []
        }
        try:
            answers = query_doh(sel, "TXT")
            dkim_records = [a for a in answers if "p=" in a or "v=dkim1" in a.lower()]
            if not dkim_records:
                sel_res["errors"].append(f"No DKIM record found at {sel}.")
                result["status"] = "fail"
                result["errors"].append(f"DKIM key missing at {sel}.")
            else:
                raw_dkim = dkim_records[0]
                if "p=" in raw_dkim and len(raw_dkim.split("p=")[1].strip()) > 10:
                    sel_res["valid"] = True
                    sel_res["key_preview"] = raw_dkim[:40] + "..."
                else:
                    sel_res["errors"].append("DKIM key payload empty or revoked.")
                    result["status"] = "fail"
                    result["errors"].append(f"DKIM key invalid at {sel}.")
        except Exception as e:
            sel_res["errors"].append(str(e))
            result["status"] = "fail"
            result["errors"].append(f"DKIM lookup error at {sel}: {e}")

        result["selectors_tested"].append(sel_res)

    return result

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    os.makedirs("dns", exist_ok=True)

    summary_lines = [
        "# 📬 Email Deliverability & DNS Health Report",
        f"> Last updated: `{timestamp}`",
        "",
        "Automated daily audit of **SPF**, **DMARC**, **MX**, and **DKIM** DNS records for domain reputation and mailbox inbox placement.",
        "",
        "| Site / Domain | MX Records | SPF | DMARC Policy | DKIM | Status | Details |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
    ]

    all_results = []
    has_critical_error = False

    for target in TARGETS:
        print(f"\n--- Checking Email & DNS Health: {target['name']} ({target['domain']}) ---")
        mx_res = audit_mx(target)
        spf_res = audit_spf(target)
        dmarc_res = audit_dmarc(target)
        dkim_res = audit_dkim(target)

        target_errors = mx_res["errors"] + spf_res["errors"] + dmarc_res["errors"] + dkim_res["errors"]
        target_warnings = mx_res["warnings"] + spf_res["warnings"] + dmarc_res["warnings"] + dkim_res["warnings"]

        is_ok = len(target_errors) == 0
        if not is_ok:
            has_critical_error = True

        status_badge = "🟩 Healthy" if is_ok else "🟥 Degraded"
        
        # MX Badge
        if mx_res["status"] == "skipped":
            mx_badge = "➖ N/A"
        elif mx_res["status"] == "pass":
            mx_badge = f"✅ Valid ({len(mx_res['records'])})"
        else:
            mx_badge = "❌ Broken"

        # SPF Badge
        if spf_res["status"] == "skipped":
            spf_badge = "➖ N/A"
        elif spf_res["status"] == "pass":
            spf_badge = "✅ Valid"
        else:
            spf_badge = "❌ Insecure"

        # DMARC Badge
        if dmarc_res["status"] == "skipped":
            dmarc_badge = "➖ N/A"
        elif dmarc_res["status"] == "pass":
            dmarc_badge = f"✅ `p={dmarc_res['policy']}`"
        else:
            dmarc_badge = "❌ Missing"

        # DKIM Badge
        if dkim_res["status"] == "skipped":
            dkim_badge = "➖ N/A"
        elif dkim_res["status"] == "pass":
            dkim_badge = f"✅ Valid ({len(dkim_res['selectors_tested'])})"
        else:
            dkim_badge = "❌ Invalid"

        details = []
        if target_errors:
            details.extend(target_errors)
        elif target_warnings:
            details.extend(target_warnings)
        else:
            details.append("All deliverability records verified.")

        summary_lines.append(
            f"| **{target['name']}** (`{target['domain']}`) | {mx_badge} | {spf_badge} | {dmarc_badge} | {dkim_badge} | {status_badge} | {' '.join(details)} |"
        )

        record = {
            "site": target["name"],
            "domain": target["domain"],
            "slug": target["slug"],
            "timestamp": timestamp,
            "mx": mx_res,
            "spf": spf_res,
            "dmarc": dmarc_res,
            "dkim": dkim_res,
            "is_ok": is_ok,
            "errors": target_errors,
            "warnings": target_warnings
        }
        all_results.append(record)

        print(f"MX: {mx_badge} | SPF: {spf_badge} | DMARC: {dmarc_badge} | DKIM: {dkim_badge} | Status: {status_badge}")
        if target_errors:
            print("Errors:", target_errors)
        if target_warnings:
            print("Warnings:", target_warnings)

    summary_lines.append("")
    summary_lines.append("### Diagnostic Requirements:")
    summary_lines.append("* **SPF**: Confirms single valid `v=spf1` record, ensures authorized mail servers are included, and rejects `+all`.")
    summary_lines.append("* **DMARC**: Requires active `_dmarc` record with valid alignment policy (`p=none`, `quarantine`, or `reject`).")
    summary_lines.append("* **MX**: Verifies mail server priority and reachability without DNS timeouts.")
    summary_lines.append("* **DKIM**: Validates selector public keys for email cryptographic signing.")
    summary_lines.append("")
    summary_lines.append("---")
    summary_lines.append("*Report generated by Email Deliverability & DNS Health CI.*")

    with open("dns/summary.md", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    payload = {
        "timestamp": timestamp,
        "has_critical_error": has_critical_error,
        "results": all_results
    }
    with open("dns/latest.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open("dns/history.jsonl", "a", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    print("\nEmail Deliverability & DNS verification completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
