# 📋 Lead Intake & Form Health Summary

**Last Probe Run:** `2026-09-19 22:12:48 UTC`  
**Total Targets:** 4 | **Passed:** 3 | **Failed:** 1

| Form Target | Page Status | Submission Route | Assets Verified | Health |
| :--- | :---: | :---: | :---: | :---: |
| [DrSumaiya - Consultation Inquiry Form](https://drsumaiya.com/inquiry-form/) | HTTP 200 (477.92ms) | `OPTIONS` 200 | 4 assets | 🟢 **PASS** |
| [DrSumaiya - Patient History Form](https://drsumaiya.com/form/) | HTTP 200 (390.63ms) | Iframe HTTP 200 | 1 assets | 🟢 **PASS** |
| [IQS - Admissions & Course Inquiry Form](https://iqs.org.in/inquiry/) | HTTP 200 (605.83ms) | `OPTIONS` 200 | 0 assets | 🟢 **PASS** |
| [Hifz Focus - Student Onboarding Form](https://hifz.iqs.org.in/onboarding) | HTTP 500 (150.74ms) | Client-side | 0 assets | 🔴 **FAIL** |

## Detailed Target Breakdown

### DrSumaiya - Consultation Inquiry Form
- **URL:** https://drsumaiya.com/inquiry-form/
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`
- **REST Submission Route:** `https://drsumaiya.com/wp-json/nutricare/v1/submit` (OPTIONS -> HTTP 200, Allow: `POST`)

### DrSumaiya - Patient History Form
- **URL:** https://drsumaiya.com/form/
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`
- **Embedded Form Target:** `https://docs.google.com/forms/d/e/1FAIpQLSdOnU6NJUiOTLHouIEhRpnqIUiNV40TfUqFLdtuflvUulLkAg/viewform?embedded=true` (HTTP 200)

### IQS - Admissions & Course Inquiry Form
- **URL:** https://iqs.org.in/inquiry/
- **DOM Container Status:** `PASS`
- **Inputs Checked:** `PASS`
- **REST Submission Route:** `https://iqs.org.in/wp-json/iqs/v1/inquiry` (OPTIONS -> HTTP 200, Allow: `POST`)

### Hifz Focus - Student Onboarding Form
- **URL:** https://hifz.iqs.org.in/onboarding
