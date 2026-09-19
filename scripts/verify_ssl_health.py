#!/usr/bin/env python3
"""
SSL/TLS Certificate Expiry & Health Verification Watchdog.
Audits TLS certificates, expiration countdowns, SAN coverage,
CA issuers, and cipher suites across all managed domains.
"""

import os
import sys
import json
import ssl
import socket
import fnmatch
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output across all operating systems
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Alert Thresholds (in days)
CRITICAL_DAYS = 7
WARNING_DAYS = 21

DEFAULT_TIMEOUT = 10

TARGETS = [
    {
        "name": "DrSumaiya.com",
        "hostname": "drsumaiya.com",
        "port": 443,
        "slug": "dr-sumaiya-com"
    },
    {
        "name": "DrSumaiya - Status",
        "hostname": "status.drsumaiya.com",
        "port": 443,
        "slug": "drsumaiya-status"
    },
    {
        "name": "IQS",
        "hostname": "iqs.org.in",
        "port": 443,
        "slug": "iqs"
    },
    {
        "name": "IQS - Hifz Focus",
        "hostname": "hifz.iqs.org.in",
        "port": 443,
        "slug": "iqs-hifz"
    },
    {
        "name": "Hifz Focus App",
        "hostname": "hifzfocus.com",
        "port": 443,
        "slug": "hifzfocus-com"
    }
]


def parse_rdn_tuple(rdn_tuple):
    """Convert an X.509 RDN tuple of tuples into a flat dictionary."""
    result = {}
    if not rdn_tuple:
        return result
    for rdn in rdn_tuple:
        for item in rdn:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                result[item[0]] = item[1]
    return result


def parse_ssl_date(date_str):
    """Parse OpenSSL certificate timestamp into a UTC datetime object."""
    # Common format: 'Dec 12 04:06:45 2026 GMT'
    try:
        return datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except Exception:
        # Fallback without timezone specification
        clean = " ".join(date_str.split()[:4])
        return datetime.strptime(clean, "%b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)


def matches_hostname(hostname, allowed_names):
    """Check if hostname matches any SAN or CN pattern (including wildcards)."""
    hostname_lower = hostname.lower()
    for pattern in allowed_names:
        pattern_lower = pattern.lower()
        if fnmatch.fnmatch(hostname_lower, pattern_lower):
            return True
    return False


def verify_ssl_target(target):
    """Probe a single target over TLS with SNI and evaluate certificate health."""
    hostname = target["hostname"]
    port = target.get("port", 443)
    name = target["name"]
    slug = target["slug"]

    now = datetime.now(timezone.utc)

    result = {
        "site": name,
        "hostname": hostname,
        "port": port,
        "slug": slug,
        "is_ok": False,
        "severity": "healthy",  # 'healthy', 'warning', 'critical'
        "days_remaining": None,
        "valid_from": None,
        "valid_to": None,
        "issuer": None,
        "subject_cn": None,
        "sans": [],
        "tls_version": None,
        "cipher": None,
        "errors": [],
        "warnings": []
    }

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=DEFAULT_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                result["tls_version"] = ssock.version()
                cipher_info = ssock.cipher()
                if cipher_info:
                    result["cipher"] = cipher_info[0]

                # Parse validity dates
                not_before_str = cert.get("notBefore")
                not_after_str = cert.get("notAfter")

                if not_after_str:
                    valid_to = parse_ssl_date(not_after_str)
                    result["valid_to"] = valid_to.isoformat()
                    days_remaining = round((valid_to - now).total_seconds() / 86400.0, 1)
                    result["days_remaining"] = days_remaining
                else:
                    result["errors"].append("Certificate missing expiration date ('notAfter').")

                if not_before_str:
                    valid_from = parse_ssl_date(not_before_str)
                    result["valid_from"] = valid_from.isoformat()
                    if now < valid_from:
                        result["errors"].append(f"Certificate is not yet valid (active from {valid_from.isoformat()}).")

                # Parse Subject and Issuer
                subject = parse_rdn_tuple(cert.get("subject"))
                issuer = parse_rdn_tuple(cert.get("issuer"))

                result["subject_cn"] = subject.get("commonName", "Unknown")

                issuer_org = issuer.get("organizationName")
                issuer_cn = issuer.get("commonName")
                if issuer_org and issuer_cn:
                    result["issuer"] = f"{issuer_org} ({issuer_cn})"
                elif issuer_org:
                    result["issuer"] = issuer_org
                elif issuer_cn:
                    result["issuer"] = issuer_cn
                else:
                    result["issuer"] = "Unknown CA"

                # Parse SANs
                sans = []
                for san_entry in cert.get("subjectAltName", ()):
                    if len(san_entry) == 2 and san_entry[0].lower() == "dns":
                        sans.append(san_entry[1])
                result["sans"] = sans

                # Validate hostname matching
                allowed_names = list(sans)
                if result["subject_cn"] and result["subject_cn"] not in allowed_names:
                    allowed_names.append(result["subject_cn"])

                if not matches_hostname(hostname, allowed_names):
                    result["errors"].append(
                        f"Hostname mismatch: '{hostname}' not covered by SANs {sans} or CN '{result['subject_cn']}'."
                    )

                # Evaluate Days Remaining
                if result["days_remaining"] is not None:
                    if result["days_remaining"] <= 0:
                        result["errors"].append(
                            f"Certificate has EXPIRED {abs(result['days_remaining'])} days ago on {result['valid_to']}."
                        )
                        result["severity"] = "critical"
                    elif result["days_remaining"] <= CRITICAL_DAYS:
                        result["errors"].append(
                            f"CRITICAL: Certificate expires in {result['days_remaining']} days (<= {CRITICAL_DAYS} days)."
                        )
                        result["severity"] = "critical"
                    elif result["days_remaining"] <= WARNING_DAYS:
                        result["warnings"].append(
                            f"WARNING: Certificate expires in {result['days_remaining']} days (<= {WARNING_DAYS} days). Check auto-renewal."
                        )
                        result["severity"] = "warning"
                    else:
                        result["severity"] = "healthy"

    except ssl.SSLCertVerificationError as e:
        result["errors"].append(f"TLS certificate verification failed: {e.strerror or e}")
        result["severity"] = "critical"
    except (socket.timeout, TimeoutError):
        result["errors"].append(f"Connection timed out connecting to {hostname}:{port}")
        result["severity"] = "critical"
    except socket.gaierror as e:
        result["errors"].append(f"DNS resolution failure for {hostname}: {e}")
        result["severity"] = "critical"
    except ConnectionRefusedError:
        result["errors"].append(f"Connection refused on {hostname}:{port}")
        result["severity"] = "critical"
    except Exception as e:
        result["errors"].append(f"TLS inspection error on {hostname}: {type(e).__name__} - {e}")
        result["severity"] = "critical"

    # Overall target health determination
    # If there are hard errors, is_ok is False.
    # Note: Warnings do not flip is_ok to False, but will notify via warning severity.
    result["is_ok"] = len(result["errors"]) == 0

    return result


def generate_summary_markdown(results, now_str):
    """Render a GitHub-compatible Markdown summary table for ssl/summary.md."""
    lines = [
        "# 🔒 SSL/TLS Certificate Health & Expiry Report",
        f"> Last updated: `{now_str}`",
        "",
        "Automated daily audit of TLS certificates, expiration countdowns, SAN coverage, and cipher suites.",
        "",
        "| Site | Hostname | Status | Days Left | Expires On | Issuer | TLS | Details |",
        "| :--- | :--- | :---: | :---: | :--- | :--- | :---: | :--- |"
    ]

    for r in results:
        site = r["site"]
        hostname = f"`{r['hostname']}`"
        days = f"**{r['days_remaining']}d**" if r["days_remaining"] is not None else "N/A"
        expires_date = r["valid_to"][:10] if r.get("valid_to") else "N/A"
        issuer = r.get("issuer") or "Unknown"
        tls_ver = r.get("tls_version") or "N/A"

        if r["severity"] == "critical":
            status_badge = "🚨 Critical"
        elif r["severity"] == "warning":
            status_badge = "⚠️ Warning"
        else:
            status_badge = "🟩 Healthy"

        details = []
        if r["errors"]:
            details.extend([f"❌ {e}" for e in r["errors"]])
        if r["warnings"]:
            details.extend([f"⚠️ {w}" for w in r["warnings"]])
        if not details:
            details.append("Certificate valid and trusted.")

        details_str = " <br> ".join(details)
        lines.append(f"| **{site}** | {hostname} | {status_badge} | {days} | {expires_date} | {issuer} | {tls_ver} | {details_str} |")

    lines.extend([
        "",
        "### Diagnostic Thresholds:",
        f"* **🚨 Critical Alert (`<= {CRITICAL_DAYS} days` or expired):** Immediate action required. Potential outage imminent.",
        f"* **⚠️ Warning Alert (`<= {WARNING_DAYS} days`):** Certificate nearing expiration. Check automated renewal cron (certbot / Cloudflare / host).",
        f"* **🟩 Healthy (`> {WARNING_DAYS} days`):** Valid certificate chain with sufficient validity buffer.",
        "",
        "---",
        "*Report generated by SSL/TLS Health CI.*",
        ""
    ])

    return "\n".join(lines)


def main():
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"[{now_str}] Starting SSL/TLS Certificate Expiry & Health Verification...")
    print(f"Monitoring {len(TARGETS)} target(s). Thresholds: Critical <= {CRITICAL_DAYS}d, Warning <= {WARNING_DAYS}d.\n")

    results = []
    overall_all_ok = True

    for target in TARGETS:
        print(f"[*] Auditing {target['name']} ({target['hostname']}:{target.get('port', 443)})...")
        r = verify_ssl_target(target)
        results.append(r)

        status_emoji = "🟩" if r["is_ok"] and r["severity"] == "healthy" else ("⚠️" if r["severity"] == "warning" else "🚨")
        print(f"    {status_emoji} Status: {r['severity'].upper()} | Days Remaining: {r['days_remaining']} | Issuer: {r['issuer']} | TLS: {r['tls_version']}")
        for err in r["errors"]:
            print(f"    ❌ Error: {err}")
        for warn in r["warnings"]:
            print(f"    ⚠️ Warning: {warn}")

        if not r["is_ok"]:
            overall_all_ok = False

    # Ensure ssl/ directory exists
    output_dir = Path("ssl")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write ssl/latest.json
    latest_payload = {
        "timestamp": now_str,
        "critical_threshold_days": CRITICAL_DAYS,
        "warning_threshold_days": WARNING_DAYS,
        "all_healthy": overall_all_ok and all(r["severity"] == "healthy" for r in results),
        "results": results
    }

    latest_file = output_dir / "latest.json"
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(latest_payload, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Wrote latest snapshot to {latest_file}")

    # 2. Append to ssl/history.jsonl
    history_file = output_dir / "history.jsonl"
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(latest_payload, ensure_ascii=False) + "\n")
    print(f"[+] Appended audit entry to {history_file}")

    # 3. Write ssl/summary.md
    summary_md = generate_summary_markdown(results, now_str)
    summary_file = output_dir / "summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_md)
    print(f"[+] Rendered Markdown summary to {summary_file}")

    print("\nSSL/TLS verification completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
