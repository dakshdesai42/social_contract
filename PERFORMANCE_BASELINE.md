# Phase 1 Baseline (2026-02-06)

## Current Static Payload Sizes

- `static/style.css`: 92,877 bytes
- `static/script.js`: 33,976 bytes
- `static/challenge.js`: 16,551 bytes
- `static/create-challenge.js`: 6,234 bytes
- `static/sw.js`: 4,820 bytes
- Total (major front-end assets): 154,458 bytes

## Instrumentation Added

- Server page-view analytics (already present): `PageViewEvent`
- New Real User Metrics (RUM) table: `WebVitalEvent`
- New ingest endpoint: `POST /api/analytics/web-vitals`
- New client collector: `static/perf-metrics.js`
- Admin dashboard now includes Web Vitals summary on `/admin/analytics`

## Metrics Collected

- `TTFB` (from navigation timing)
- `FCP` (First Contentful Paint)
- `LCP` (Largest Contentful Paint)
- `CLS` (Cumulative Layout Shift)
- `INP` (Interaction latency from Event Timing where supported)

Each sample includes:
- metric name/value/rating
- page path
- date/time
- country code (header-derived)
- anonymous session key and optional user id

## Production Baseline Checklist

1. Deploy commit to Render.
2. Open app in mobile + desktop and navigate key pages (`/dashboard`, `/challenge/<id>`, `/profile`, `/explore`).
3. Wait 10-15 minutes for samples to accumulate.
4. Review `/admin/analytics?days=7`.
5. Record:
   - DAU today
   - Top 5 pages by views
   - Top countries by active users
   - Web Vitals p75 values for LCP/INP/CLS/FCP/TTFB

## Notes

- Lighthouse CLI is not installed in this environment, so this baseline uses production RUM metrics.
- `tracking.private.env` remains git-ignored for private tracking settings.
