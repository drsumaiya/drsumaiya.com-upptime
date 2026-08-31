# PageSpeed Insights Results

Automated daily performance tracking via [Google PageSpeed Insights API v5](https://developers.google.com/speed/docs/insights/v5/get-started).

Results will be populated after the first workflow run.

## Tracked Sites

- **DrSumaiya.com** — `https://drsumaiya.com/`
- **IQS** — `https://iqs.org.in/`

## Structure

- `<slug>/latest.json` — Latest scores (mobile + desktop)
- `<slug>/raw/` — Full API responses per day
- `<slug>/summary.md` — Per-site markdown summary
- `history/<slug>.jsonl` — Historical scores log (JSONL, one entry per day)

## How to Trigger

- **Automatic**: Runs daily at 06:00 UTC (11:30 AM IST)
- **Manual**: Go to Actions → "PageSpeed Insights CI" → "Run workflow"

## Adding a New Site

Edit `.github/workflows/pagespeed.yml` and add an entry to the matrix:

```yaml
- name: My New Site
  url: https://example.com/
  slug: my-new-site
```

---
*Powered by GitHub Actions + [Google PageSpeed Insights API v5](https://developers.google.com/speed/docs/insights/v5/get-started)*
