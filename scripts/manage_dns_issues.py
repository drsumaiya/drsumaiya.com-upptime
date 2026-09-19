#!/usr/bin/env python3
"""
Email Deliverability & DNS Incident Management
Monitors dns/latest.json and manages GitHub incident issues for SPF, DMARC, MX, and DKIM degradations.
"""

import os
import sys
import json
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

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

    results_file = "dns/latest.json"
    if not os.path.isfile(results_file):
        print(f"File {results_file} not found. Run verify_email_dns.py first.")
        return 1

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("timestamp", "Unknown UTC")
    results = data.get("results", [])

    for r in results:
        name = r["site"]
        domain = r["domain"]
        slug = r["slug"]
        is_ok = r["is_ok"]
        errors = r.get("errors", [])
        warnings = r.get("warnings", [])
        mx = r.get("mx", {})
        spf = r.get("spf", {})
        dmarc = r.get("dmarc", {})
        dkim = r.get("dkim", {})

        print(f"\nEvaluating Email & DNS Incident Status for: {name} ({domain})")

        # Query existing open issue for this slug
        raw_issues = run_gh([
            "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", "email-dns-incident",
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

        if not is_ok:
            print(f"❌ Email deliverability / DNS issue detected for {name} ({len(errors)} error(s)).")
            error_list_md = "\n".join([f"* ❌ **{err}**" for err in errors])
            warning_list_md = "\n".join([f"* ⚠️ {w}" for w in warnings]) if warnings else ""

            body = f"""### 🚨 Email Deliverability & DNS Alert for **{name}** (`{domain}`)

An automated DNS audit detected missing, misconfigured, or broken email authentication records that could cause emails to land in spam or be rejected by mail providers (Gmail, Outlook, Yahoo):

#### ❌ Detected Errors:
{error_list_md}

"""
            if warning_list_md:
                body += f"#### ⚠️ Warnings:\n{warning_list_md}\n\n"

            body += f"""#### 📋 Active Record Details:
- **Domain**: `{domain}`
- **MX Records**: `{', '.join([f"{m.get('priority', '')} {m.get('host', '')}".strip() for m in mx.get('records', [])]) or 'None'}`
- **SPF Record**: `{spf.get('record') or 'Missing'}`
- **DMARC Policy**: `{dmarc.get('record') or 'Missing'}`
- **DKIM Status**: `{dkim.get('status')}`

#### 🛠️ Recommended Remediation:
1. Log into your DNS management portal (Hostinger / Cloudflare / DNS registrar).
2. For **SPF**: Ensure a single TXT record starting with `v=spf1 include:_spf.mail.hostinger.com ~all` is published on `{domain}`.
3. For **DMARC**: Confirm a TXT record `v=DMARC1; p=none;` exists at `_dmarc.{domain}`.
4. For **MX**: Verify MX records point to valid mail exchanger hostnames.
5. Once updated, DNS changes typically propagate within 5–15 minutes.

---
*Reported at `{timestamp}` by Email Deliverability & DNS Health CI. This issue will automatically close once DNS records are verified healthy.*
"""

            if existing_number:
                print(f"Updating existing open DNS incident issue #{existing_number}...")
                comment = f"""**Daily Email & DNS Health Update (`{timestamp}`):**
- **Status**: ❌ **Deliverability records remain degraded.**
- **Active Errors**:
{error_list_md}
"""
                if warning_list_md:
                    comment += f"- **Warnings**:\n{warning_list_md}\n"
                comment += "\n*Issue remains open until verified healthy.*"

                run_gh([
                    "issue", "comment", str(existing_number),
                    "--repo", repo,
                    "--body", comment
                ])
            else:
                print(f"Creating new Email & DNS incident issue for {name}...")
                title = f"🚨 Email Deliverability Alert: {name} ({domain} DNS records degraded)"
                labels = f"email-dns-incident,incident,{slug}"
                run_gh([
                    "issue", "create",
                    "--repo", repo,
                    "--title", title,
                    "--body", body,
                    "--label", labels
                ])
        else:
            print(f"✅ Email & DNS health is verified OK for {name}.")
            if existing_number:
                print(f"Resolving and closing DNS incident issue #{existing_number}...")
                resolve_comment = f"""**✅ Resolved:** Email Deliverability & DNS records for **{name}** (`{domain}`) have recovered!

- **SPF**: Valid (`{spf.get('record', 'OK')}`)
- **DMARC**: Active policy `p={dmarc.get('policy', 'none')}`
- **MX**: Reachable ({len(mx.get('records', []))} exchangers)

*Closed automatically by Email Deliverability & DNS Health CI at `{timestamp}`.*
"""
                run_gh([
                    "issue", "close", str(existing_number),
                    "--repo", repo,
                    "--comment", resolve_comment
                ])

    print("\nDNS issue evaluation completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
