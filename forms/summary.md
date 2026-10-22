# 📋 Lead Intake & Form Health Summary

**Last Probe Run:** `2026-10-22 19:49:00 UTC`  
**Total Targets:** 4 | **Passed:** 2 | **Failed:** 2

| Form Target | Page Status | Submission Route | Assets Verified | Health |
| :--- | :---: | :---: | :---: | :---: |
| [DrSumaiya - Consultation Inquiry Form](https://drsumaiya.com/inquiry-form/) | HTTP 200 (3838.35ms) | `OPTIONS` 307 | 3 assets | 🔴 **FAIL** |
| [DrSumaiya - Patient History Form](https://drsumaiya.com/form/) | HTTP 200 (3497.06ms) | Iframe HTTP 200 | 1 assets | 🟢 **PASS** |
| [IQS - Admissions & Course Inquiry Form](https://iqs.org.in/inquiry/) | HTTP 200 (2137.43ms) | `OPTIONS` 307 | 0 assets | 🔴 **FAIL** |
| [Hifz Focus - Student Onboarding Form](https://hifz.iqs.org.in/onboarding) | HTTP 200 (158.73ms) | Client-side | 6 assets | 🟢 **PASS** |

## Detailed Target Breakdown

### DrSumaiya - Consultation Inquiry Form
- **URL:** https://drsumaiya.com/inquiry-form/
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`
- **REST Submission Route:** `https://drsumaiya.com/wp-json/nutricare/v1/submit` (OPTIONS -> HTTP 307, Allow: ``)

> [!CAUTION]
> - ⚠️ Submission endpoint https://drsumaiya.com/wp-json/nutricare/v1/submit failed probe: HTTP 307 (Allow: '')

### DrSumaiya - Patient History Form
- **URL:** https://drsumaiya.com/form/
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`
- **Embedded Form Target:** `https://docs.google.com/forms/d/e/1FAIpQLSdOnU6NJUiOTLHouIEhRpnqIUiNV40TfUqFLdtuflvUulLkAg/viewform?embedded=true` (HTTP 200)

### IQS - Admissions & Course Inquiry Form
- **URL:** https://iqs.org.in/inquiry/
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`
- **REST Submission Route:** `https://iqs.org.in/wp-json/iqs/v1/inquiry` (OPTIONS -> HTTP 307, Allow: ``)

> [!CAUTION]
> - ⚠️ Submission endpoint https://iqs.org.in/wp-json/iqs/v1/inquiry failed probe: HTTP 307 (Allow: '')

### Hifz Focus - Student Onboarding Form
- **URL:** https://hifz.iqs.org.in/onboarding
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`

