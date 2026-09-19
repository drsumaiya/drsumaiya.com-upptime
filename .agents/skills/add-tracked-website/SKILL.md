---
name: add-tracked-website
description: >-
  Adds a new website or endpoint to this repository for uptime monitoring,
  PageSpeed Insights / Core Web Vitals CI tracking, frontend dashboard reporting,
  and SEO & indexing health verification.
  Use this skill whenever:
    1. The user asks to add, track, or monitor a new website, domain, or URL.
    2. Setting up PageSpeed / Lighthouse or SEO health checks for an existing or new property.
    3. Updating .upptimerc.yml, pagespeed CI matrix, or verify_seo_health.py targets.
---

# Add Tracked Website Skill

This skill provides automated and manual procedures to register a website or URL across the four core tracking systems in `drsumaiya.com-upptime`:

1. **Uptime & Response Time Tracking** (`.upptimerc.yml`)
2. **PageSpeed Insights & Core Web Vitals CI** (`.github/workflows/pagespeed.yml`)
3. **Frontend PageSpeed Dashboard** (`assets/pagespeed.js`)
4. **SEO & Indexing Health CI** (`scripts/verify_seo_health.py`)

---

## Quick Start (Automated Script)

Use the built-in helper script to automatically discover endpoints (`robots.txt`, XML sitemaps) and inject the website into all configuration files:

```bash
uv run python .agents/skills/add-tracked-website/scripts/add_website.py \
  --name "Site Display Name" \
  --url "https://example.com/" \
  --slug "example-slug"
```

### Script Arguments

| Flag | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| `--name` | Yes | Human-readable title for dashboards and issues | `"IQS - Hifz Focus"` |
| `--url` | Yes | Full homepage or endpoint URL | `"https://hifz.iqs.org.in/"` |
| `--slug` | Yes | Unique kebab-case slug for filenames, CI matrix & labels | `"iqs-hifz"` |
| `--robots` | No | Explicit robots.txt URL (auto-probed if omitted) | `"https://hifz.iqs.org.in/robots.txt"` |
| `--sitemap` | No | Explicit XML sitemap URL (auto-probed if omitted) | `"https://hifz.iqs.org.in/sitemap.xml"` |
| `--skip-probe` | No | Skip live HTTP probe during setup | `--skip-probe` |

---

## Step-by-Step Manual Procedure

If manual editing is preferred or adjustments are required:

### 1. Uptime Monitoring ([`.upptimerc.yml`](file:///d:/code/drsumaiya.com-upptime/.upptimerc.yml))
Add the site under the `sites:` list:
```yaml
sites:
  - name: IQS - Hifz Focus
    url: https://hifz.iqs.org.in/
```

### 2. PageSpeed CI Workflow ([`.github/workflows/pagespeed.yml`](file:///d:/code/drsumaiya.com-upptime/.github/workflows/pagespeed.yml))
Add the site to `jobs.pagespeed.strategy.matrix.include`:
```yaml
          - name: IQS - Hifz Focus
            url: https://hifz.iqs.org.in/
            slug: iqs-hifz
```

### 3. Frontend Dashboard Selector ([`assets/pagespeed.js`](file:///d:/code/drsumaiya.com-upptime/assets/pagespeed.js))
Add the site to the `SITES` array:
```javascript
    {
      name: "IQS - Hifz Focus",
      slug: "iqs-hifz",
      url: "https://hifz.iqs.org.in/"
    }
```

### 4. SEO & Indexing Health ([`scripts/verify_seo_health.py`](file:///d:/code/drsumaiya.com-upptime/scripts/verify_seo_health.py))
Add the target to `TARGETS`:
```python
    {
        "name": "IQS - Hifz Focus",
        "domain": "https://hifz.iqs.org.in",
        "robots_url": "https://hifz.iqs.org.in/robots.txt",
        "sitemap_url": "https://hifz.iqs.org.in/sitemap.xml",
        "slug": "iqs-hifz"
    }
```

---

## Verification & Testing

After updating the configurations:

1. **Verify SEO & Sitemap**:
   ```bash
   uv run python scripts/verify_seo_health.py
   ```
   Confirm that `robots.txt` reports `✅ OK` and the sitemap reports `✅ Valid (...)`.

2. **Clean up local test report diffs** (so only source files are committed):
   ```bash
   git checkout -- seo/
   ```

3. **Check Git Diff**:
   ```bash
   git diff
   ```
   Ensure edits are present across `.upptimerc.yml`, `.github/workflows/pagespeed.yml`, `assets/pagespeed.js`, and `scripts/verify_seo_health.py`.
