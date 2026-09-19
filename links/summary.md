# 🛡️ Broken Link & 404 Sentinel Report
> Last updated: `2026-09-19 16:37:31 UTC`

Automated weekly deep-crawl and stress-test of internal navigation and external outbound hyperlinks across all live properties.

| Site | Status | Links Audited | Broken Links | Health Status |
| :--- | :---: | :---: | :---: | :--- |
| [DrSumaiya.com](https://drsumaiya.com) | 🚨 1 Fault(s) | 120 | 1 | 🟥 Degraded |
| [IQS](https://iqs.org.in) | 🚨 2 Fault(s) | 98 | 2 | 🟥 Degraded |
| [IQS - Hifz Focus](https://hifz.iqs.org.in) | ✅ Clean | 18 | 0 | 🟩 Healthy |

### 🚨 Faulty Endpoints & Broken Link Tracking Log:

| Property | Source Page | Target Broken URL | HTTP Status | Details |
| :--- | :--- | :--- | :---: | :--- |
| **DrSumaiya.com** | [https://drsumaiya.com/](https://drsumaiya.com/) | `https://maps.app.goo.gl/ULJKgWjvx1FCLf2WA` | `404` | Rejected status code: 404 Not Found |
| **IQS** | [https://iqs.org.in/](https://iqs.org.in/) | `https://iqs.org.in/wp-content/plugins/events-manager/includes/img/flags.webp` | `404` | Rejected status code: 404 Not Found |
| **IQS** | [https://iqs.org.in/](https://iqs.org.in/) | `https://iqs.org.in/wp-content/plugins/events-manager/includes/img/globe.webp` | `404` | Rejected status code: 404 Not Found |

### 🔍 Sentinel Diagnostics:
* **Deep Crawl Boundary**: Evaluates internal navigation depth up to 2 hops from canonical sitemaps.
* **Outbound Stress-Test**: Probes external citation links, partner endpoints, and media sources.
* **Anti-Bot Filtering**: Pre-filtered to exclude rate-limited platforms (LinkedIn, X, WhatsApp, Instagram).

---
*Report generated automatically by the Continuous Broken Link & 404 Sentinel CI.*
