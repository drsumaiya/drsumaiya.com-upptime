#!/usr/bin/env python3
"""
manage_form_issues.py - Lead Intake & Form Health Incident Management.

Monitors forms/latest.json and manages GitHub incident issues when booking forms,
inquiry endpoints, or critical script/CSS assets fail. Automatically opens detailed incident
reports and closes them upon recovery.
"""

import os
import sys
import json
import subprocess

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

    results_file = "forms/latest.json"
    if not os.path.isfile(results_file):
        print(f"File {results_file} not found. Run verify_forms_health.py first.")
        return 1

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("last_updated", "Unknown UTC")
    targets = data.get("targets", [])

    for target in targets:
        target_id = target["id"]
        name = target["name"]
        page_url = target["page_url"]
        status = target["overall_status"]
        failures = target.get("failures", [])
        checks = target.get("checks", {})

        print(f"\nEvaluating Form Incident Status for: {name} ({target_id})")

        # Query existing open issue for this target
        raw_issues = run_gh([
            "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", "form-incident",
            "--label", target_id,
            "--json", "number,title"
        ])
        existing_issues = []
        if raw_issues:
            try:
                existing_issues = json.loads(raw_issues)
            except Exception:
                existing_issues = []

        existing_number = existing_issues[0]["number"] if existing_issues else None

        if status != "PASS":
            print(f"❌ Form incident detected for {name} ({len(failures)} failure(s)).")
            fail_list_md = "\n".join([f"* ❌ **{fail}**" for fail in failures])

            body = f"""### 🚨 Lead Intake & Form Incident: **{name}**

An automated synthetic health probe detected that lead intake, form rendering, submission endpoints, or critical styling assets are broken on **{name}**:

#### ❌ Detected Failures:
{fail_list_md}

#### 📋 Component Status:
- **Form Page:** `{checks.get('page', {}).get('url')}` -> HTTP {checks.get('page', {}).get('status_code')} ({checks.get('page', {}).get('latency_ms')}ms)
- **DOM Container Check:** `{checks.get('dom_form', {}).get('status')}`
- **Required Inputs Check:** `{checks.get('dom_inputs', {}).get('status')}`
"""
            if "submission_endpoint" in checks:
                sub = checks["submission_endpoint"]
                body += f"- **REST Submission Route:** `{sub['url']}` ({sub['method']} -> HTTP {sub['status_code']}, Allow: `{sub.get('allow_header', '')}`)\n"
            if "iframe_target" in checks:
                ifr = checks["iframe_target"]
                body += f"- **Embedded Form Target:** `{ifr['url']}` (HTTP {ifr['status_code']})\n"

            body += f"""
#### 🛠️ Recommended Troubleshooting:
1. **Plugin / Theme Conflict:** Check if any recently updated WordPress plugins broke form JavaScript or REST API routes.
2. **Missing Asset / 404:** Check if `basic_form_styling.css` or portal assets were moved or deleted on Hostinger / WordPress.
3. **REST API Route Missing:** Check `/wp-json/` and confirm custom endpoints (`nutricare/v1/submit`, `iqs/v1/inquiry`) are active and not returning 404/500.
4. **Iframe / Google Form:** Verify that the linked Google Form is still active, accepting responses, and not set to private.

---
*Reported at `{timestamp}` by Lead Intake & Form Health CI. This issue will automatically close once all synthetic probes pass.*
"""

            if existing_number:
                print(f"Updating existing open form incident issue #{existing_number}...")
                comment = f"""**Form Health Probe Update (`{timestamp}`):**
- **Status**: ❌ **Lead intake form remains broken.**
- **Active Failures**:
{fail_list_md}

*Issue remains open until verified healthy.*"""
                run_gh([
                    "issue", "comment", str(existing_number),
                    "--repo", repo,
                    "--body", comment
                ])
            else:
                print("Opening new form incident issue...")
                title = f"Form Incident: {name} lead intake or submission endpoint broken"
                run_gh([
                    "issue", "create",
                    "--repo", repo,
                    "--title", title,
                    "--body", body,
                    "--label", "form-incident,incident," + target_id
                ])
        else:
            print(f"✅ Form health verified for {name}.")
            if existing_number:
                print(f"Closing resolved form incident issue #{existing_number}...")
                close_comment = f"""### 🟢 Issue Resolved: Form Health Restored

All synthetic health checks (page load, DOM form container, input elements, REST submission route, and static assets) are passing:
- **Timestamp**: `{timestamp}`
- **Page Latency**: `{checks.get('page', {}).get('latency_ms')}ms`

Closing this incident automatically.
"""
                run_gh([
                    "issue", "comment", str(existing_number),
                    "--repo", repo,
                    "--body", close_comment
                ])
                run_gh([
                    "issue", "close", str(existing_number),
                    "--repo", repo,
                    "--reason", "completed"
                ])

    return 0


if __name__ == "__main__":
    sys.exit(main())
