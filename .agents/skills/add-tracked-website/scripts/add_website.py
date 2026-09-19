#!/usr/bin/env python3
"""
Helper script to add a website to drsumaiya.com-upptime across:
1. .upptimerc.yml (Uptime monitoring)
2. .github/workflows/pagespeed.yml (PageSpeed & Core Web Vitals CI matrix)
3. assets/pagespeed.js (Frontend dashboard site switcher)
4. scripts/verify_seo_health.py (SEO, robots.txt, and sitemap auditing)
"""

import argparse
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

def probe_url(url, timeout=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Upptime-Probe/1.0'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, str(e)

def discover_seo_endpoints(base_url):
    domain = base_url.rstrip("/")
    parsed = urlparse(domain)
    clean_domain = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{clean_domain}/robots.txt"

    print(f"[*] Probing robots.txt at {robots_url}...")
    status, content = probe_url(robots_url)
    sitemap_candidate = None
    if status == 200:
        for line in content.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                raw = line.split(":", 1)[1].strip()
                if "http" in line:
                    raw = line[line.find("http"):].strip()
                elif raw.startswith("/"):
                    raw = clean_domain + raw
                sitemap_candidate = raw
                break

    if not sitemap_candidate:
        for common in ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"]:
            test_url = clean_domain + common
            s_status, _ = probe_url(test_url)
            if s_status == 200:
                sitemap_candidate = test_url
                break

    if not sitemap_candidate:
        sitemap_candidate = f"{clean_domain}/sitemap.xml"

    return clean_domain, robots_url, sitemap_candidate

def update_upptimerc(name, url, filepath=".upptimerc.yml"):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = rf"url:\s*{re.escape(url)}"
    if re.search(pattern, content):
        print(f"[-] Site URL already present in {filepath}")
        return False

    entry = f"  - name: {name}\n    url: {url}\n"
    # Locate status-website: and insert before it
    if "\nstatus-website:" in content:
        new_content = content.replace("\nstatus-website:", f"\n{entry}\nstatus-website:")
    else:
        new_content = content + f"\n{entry}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[+] Added '{name}' to {filepath}")
    return True

def update_pagespeed_workflow(name, url, slug, filepath=".github/workflows/pagespeed.yml"):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if f"slug: {slug}" in content:
        print(f"[-] Slug '{slug}' already present in {filepath}")
        return False

    matrix_entry = f"          - name: {name}\n            url: {url}\n            slug: {slug}\n"
    marker = "    steps:"
    if marker in content:
        idx = content.find(marker)
        new_content = content[:idx] + matrix_entry + "\n" + content[idx:]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[+] Added '{slug}' to {filepath}")
        return True
    else:
        print(f"[!] Could not locate '{marker}' in {filepath}")
        return False

def update_pagespeed_js(name, url, slug, filepath="assets/pagespeed.js"):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if f'slug: "{slug}"' in content:
        print(f"[-] Slug '{slug}' already present in {filepath}")
        return False

    pattern = r"(\s*\{\s*name:\s*\"[^\"]+\",\s*slug:\s*\"[^\"]+\",\s*url:\s*\"[^\"]+\"\s*\})\s*\];"
    new_content, count = re.subn(pattern, rf"\1,\n    {{\n      name: \"{name}\",\n      slug: \"{slug}\",\n      url: \"{url}\"\n    }}\n  ];", content, count=1)

    if count > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[+] Added '{slug}' to {filepath}")
        return True
    else:
        print(f"[!] Could not match SITES array in {filepath}")
        return False

def update_verify_seo_health(name, domain, robots_url, sitemap_url, slug, filepath="scripts/verify_seo_health.py"):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if f'"slug": "{slug}"' in content:
        print(f"[-] Slug '{slug}' already present in {filepath}")
        return False

    pattern = r"(\s*\{\s*\"name\":\s*\"[^\"]+\",\s*\"domain\":\s*\"[^\"]+\",\s*\"robots_url\":\s*\"[^\"]+\",\s*\"sitemap_url\":\s*\"[^\"]+\",\s*\"slug\":\s*\"[^\"]+\"\s*\})\s*\]"
    new_content, count = re.subn(pattern, rf"\1,\n    {{\n        \"name\": \"{name}\",\n        \"domain\": \"{domain}\",\n        \"robots_url\": \"{robots_url}\",\n        \"sitemap_url\": \"{sitemap_url}\",\n        \"slug\": \"{slug}\"\n    }}\n]", content, count=1)

    if count > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[+] Added '{slug}' to {filepath}")
        return True
    else:
        print(f"[!] Could not match TARGETS list in {filepath}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Add website to Upptime & PageSpeed & SEO")
    parser.add_argument("--name", required=True, help="Display name of the website")
    parser.add_argument("--url", required=True, help="Full URL of the website")
    parser.add_argument("--slug", required=True, help="Unique kebab-case slug (e.g. iqs-hifz)")
    parser.add_argument("--robots", default=None, help="Custom robots.txt URL (auto-detected if omitted)")
    parser.add_argument("--sitemap", default=None, help="Custom sitemap URL (auto-detected if omitted)")
    parser.add_argument("--skip-probe", action="store_true", help="Skip remote endpoint probing")
    args = parser.parse_args()

    clean_url = args.url.strip()
    if not clean_url.endswith("/"):
        clean_url += "/"

    domain, robots_url, sitemap_url = discover_seo_endpoints(clean_url)
    if args.robots:
        robots_url = args.robots
    if args.sitemap:
        sitemap_url = args.sitemap

    print(f"\nConfiguring tracking for:")
    print(f"  Name:    {args.name}")
    print(f"  URL:     {clean_url}")
    print(f"  Slug:    {args.slug}")
    print(f"  Domain:  {domain}")
    print(f"  Robots:  {robots_url}")
    print(f"  Sitemap: {sitemap_url}\n")

    update_upptimerc(args.name, clean_url)
    update_pagespeed_workflow(args.name, clean_url, args.slug)
    update_pagespeed_js(args.name, clean_url, args.slug)
    update_verify_seo_health(args.name, domain, robots_url, sitemap_url, args.slug)

    print("\n[✓] All configurations updated! Run verify_seo_health.py to test.")

if __name__ == "__main__":
    main()
