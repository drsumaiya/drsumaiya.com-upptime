#!/usr/bin/env python3
"""
SEO & Indexing Incident Management
Monitors seo/latest.json and manages GitHub incident issues for SEO degradations.
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

    results_file = "seo/latest.json"
    if not os.path.isfile(results_file):
        print(f"File {results_file} not found. Run verify_seo_health.py first.")
        return 1

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp = data.get("timestamp", "Unknown UTC")
    results = data.get("results", [])

    for r in results:
        name = r["site"]
        slug = r["slug"]
        is_ok = r["is_ok"]
        errors = r.get("errors", [])
        warnings = r.get("warnings", [])
        robots = r.get("robots", {})
        sitemap = r.get("sitemap", {})

        print(f"\nEvaluating SEO Incident Status for: {name} ({slug})")

        # Query existing open issue for this slug
        raw_issues = run_gh([
            "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", "seo-incident",
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
            print(f"❌ SEO degradation detected for {name} ({len(errors)} error(s)).")
            error_list_md = "\n".join([f"* ❌ **{err}**" for err in errors])
            warning_list_md = "\n".join([f"* ⚠️ {w}" for w in warnings]) if warnings else ""

            body = f"""### 🚨 Search Engine Indexing & Sitemap Alert for **{name}**

An automated SEO health audit detected indexing or sitemap issues that could harm search engine visibility:

#### ❌ Detected Errors:
{error_list_md}

"""
            if warning_list_md:
                body += f"#### ⚠️ Warnings:\n{warning_list_md}\n\n"

            body += f"""#### 📋 Audit Details:
- **Site URL**: [{name}]({r.get('domain', f'https://{name.lower()}')})
- **robots.txt Status**: `HTTP {robots.get('status', 'N/A')}`
- **Sitemap Directive in robots.txt**: `{robots.get('sitemap_directive', 'None')}`
- **Catastrophic De-Indexing Guard (`Disallow: /`)**: `{'🚨 ACTIVE' if robots.get('disallow_all') else '✅ Not present'}`
- **XML Sitemap Status**: `HTTP {sitemap.get('status', 'N/A')}`
- **Sub-sitemaps Found**: `{sitemap.get('child_sitemaps_count', 0)}`

#### 🛠️ Recommended Remediation:
1. Check web server and CDN configuration for `robots.txt` and XML sitemaps.
2. In WordPress Admin, navigate to **Settings > Reading** and verify that *"Discourage search engines from indexing this site"* is **unchecked**.
3. Verify your SEO plugin (RankMath / Yoast / native WordPress core sitemap) is active and outputting valid XML without fatal PHP warnings.
4. Test URL accessibility directly in browser or via Google Search Console URL Inspection tool.

---
*Reported at `{timestamp}` by SEO & Indexing Health CI. This issue will automatically close once robots.txt and sitemaps are verified healthy.*
"""

            if existing_number:
                print(f"Updating existing open SEO issue #{existing_number}...")
                comment = f"""**Daily SEO Health Update (`{timestamp}`):**
- **Status**: ❌ **Indexing or Sitemap remains degraded.**
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
                print(f"Creating new SEO incident issue for {name}...")
                title = f"🚨 SEO / Indexing Alert: {name} (robots.txt or Sitemap degraded)"
                labels = f"seo-incident,incident,{slug}"
                run_gh([
                    "issue", "create",
                    "--repo", repo,
                    "--title", title,
                    "--body", body,
                    "--label", labels
                ])
        else:
            print(f"✅ SEO health is verified OK for {name}.")
            if existing_number:
                print(f"Resolving and closing SEO issue #{existing_number}...")
                resolve_comment = f"""**✅ Resolved:** Search Engine Indexing & Sitemap health for **{name}** has recovered!

- **robots.txt**: Accessible (`HTTP {robots.get('status', 200)}`), no global disallow directives.
- **XML Sitemap**: Valid XML (`HTTP {sitemap.get('status', 200)}`) with `{sitemap.get('child_sitemaps_count', 0)}` reachable sub-sitemaps.

*Closed automatically by SEO & Indexing Health CI at `{timestamp}`.*
"""
                run_gh([
                    "issue", "close", str(existing_number),
                    "--repo", repo,
                    "--comment", resolve_comment
                ])

    return 0

if __name__ == "__main__":
    sys.exit(main())
