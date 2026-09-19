#!/usr/bin/env python3
"""
SSL/TLS Certificate Expiry & Incident Management.
Monitors ssl/latest.json and manages GitHub incident issues for certificate expirations,
failed handshakes, hostname mismatches, and renewal warnings.
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

    results_file = "ssl/latest.json"
    if not os.path.isfile(results_file):
        print(f"File {results_file} not found. Run verify_ssl_health.py first.")
        return 1

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("timestamp", "Unknown UTC")
    results = data.get("results", [])

    for r in results:
        name = r["site"]
        hostname = r["hostname"]
        slug = r["slug"]
        is_ok = r["is_ok"]
        severity = r.get("severity", "healthy")
        days_remaining = r.get("days_remaining")
        valid_to = r.get("valid_to")
        issuer = r.get("issuer") or "Unknown CA"
        tls_version = r.get("tls_version") or "N/A"
        cipher = r.get("cipher") or "N/A"
        sans = r.get("sans", [])
        errors = r.get("errors", [])
        warnings = r.get("warnings", [])

        print(f"\nEvaluating SSL/TLS Incident Status for: {name} ({hostname})")

        # Query existing open issue for this slug
        raw_issues = run_gh([
            "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", "ssl-incident",
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

        # Incident condition: Hard errors or Warning threshold reached
        needs_issue = (not is_ok) or (severity in ["critical", "warning"])

        if needs_issue:
            is_critical = (severity == "critical") or (not is_ok)
            severity_label = "critical" if is_critical else "warning"

            print(f"⚠️ SSL degradation/warning detected for {name} (Severity: {severity.upper()}, Days left: {days_remaining}).")

            error_list_md = "\n".join([f"* ❌ **{err}**" for err in errors]) if errors else ""
            warning_list_md = "\n".join([f"* ⚠️ {w}" for w in warnings]) if warnings else ""

            body = f"""### {'🚨 Critical SSL/TLS Certificate Alert' if is_critical else '⚠️ SSL/TLS Certificate Expiry Warning'} for **{name}** (`{hostname}`)

An automated SSL/TLS health audit detected an issue requiring administrative attention:

"""
            if error_list_md:
                body += f"#### ❌ Errors:\n{error_list_md}\n\n"
            if warning_list_md:
                body += f"#### ⚠️ Warnings:\n{warning_list_md}\n\n"

            body += f"""#### 📋 Active Certificate Telemetry:
- **Hostname**: `{hostname}`
- **Days Remaining**: **`{days_remaining if days_remaining is not None else 'N/A'} days`**
- **Expiration Date**: `{valid_to or 'N/A'}`
- **Issuer / CA**: `{issuer}`
- **Negotiated Protocol**: `{tls_version}` (`{cipher}`)
- **Subject Alternative Names (SANs)**: `{', '.join(sans) if sans else 'None'}`
- **Audit Timestamp**: `{timestamp}`

#### 🛠️ Recommended Remediation:
1. **Check Auto-Renewal Service**: Verify whether Certbot, Let's Encrypt, or your host's SSL auto-renew cron is active and unblocked.
2. **Review DNS / WAF Rules**: Ensure ACME HTTP-01 challenge paths (`/.well-known/acme-challenge/`) or DNS-01 records are not blocked by Cloudflare WAF or reverse proxies.
3. **Hostinger / Cloudflare Origin**: In your hosting panel (Hostinger, Cloudflare Edge Certificates, or VPS), trigger a manual certificate re-issuance if needed.
4. **Resolution**: Once renewed with > 21 days remaining, this incident issue will **automatically close** on the next daily audit.
"""

            if existing_number:
                print(f"Issue #{existing_number} is already open. Posting telemetry update comment...")
                run_gh([
                    "issue", "comment", str(existing_number),
                    "--repo", repo,
                    "--body", f"🔄 **Daily Telemetry Update ({timestamp})**:\n- **Days Remaining**: `{days_remaining}d`\n- **Status**: `{severity.upper()}`\n- **Errors**: `{len(errors)}`\n- **Warnings**: `{len(warnings)}`"
                ])
            else:
                title_prefix = "🚨 Critical SSL/TLS Alert" if is_critical else "⚠️ SSL/TLS Expiry Warning"
                issue_title = f"{title_prefix}: {name} ({hostname}) - {days_remaining}d remaining" if days_remaining is not None else f"{title_prefix}: {name} ({hostname}) handshake failure"
                print(f"Creating new GitHub issue: '{issue_title}'")
                run_gh([
                    "issue", "create",
                    "--repo", repo,
                    "--title", issue_title,
                    "--body", body,
                    "--label", "incident",
                    "--label", "ssl-incident",
                    "--label", severity_label,
                    "--label", slug
                ])
        else:
            # System is completely healthy
            print(f"✅ SSL/TLS health is nominal for {name} ({days_remaining} days remaining).")
            if existing_number:
                print(f"Found open issue #{existing_number} for recovered target. Auto-closing...")
                recovery_comment = f"""### ✅ SSL/TLS Certificate Renewed Successfully

The automated SSL/TLS watchdog confirmed that the certificate for **{name}** (`{hostname}`) has been renewed and is healthy:
- **New Expiry Date**: `{valid_to}`
- **Days Remaining**: **`{days_remaining} days`**
- **Issuer**: `{issuer}`
- **TLS Protocol**: `{tls_version}`

All checks are green. Automatically closing this incident.
"""
                run_gh([
                    "issue", "close", str(existing_number),
                    "--repo", repo,
                    "--comment", recovery_comment,
                    "--reason", "completed"
                ])

    print("\nSSL incident evaluation completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
