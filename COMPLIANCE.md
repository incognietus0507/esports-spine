# Compliance, Legal & Anti-Scraping Notes

**Read this before running the tool against any live platform.** Retail
arbitrage itself is legal in most jurisdictions; the *data collection* is where
projects get themselves banned or sued. This document is engineering guidance,
not legal advice — consult a lawyer for your specific situation.

## The hierarchy of acceptable data access

1. **Official API** (best). Keyed, rate-limited, explicitly permitted. Use it.
2. **Machine-readable feed the platform publishes** (RSS, sitemaps, JSON
   endpoints documented for public use). Acceptable if you stay polite.
3. **Scraping public HTML pages** (grey zone). Only where 1 and 2 don't exist,
   only public (non-logged-in) pages, only at low volume, only respecting
   `robots.txt`. Carries ToS and legal risk.
4. **Bypassing login walls / CAPTCHAs / bot detection** (don't). This is where
   ToS violations become clear-cut and, in some readings, CFAA-relevant in the
   US. This project will not help you do this.

## Platform-by-platform

### eBay — ✅ use the official API
- **Browse API** → active listings and current asking prices.
- **Marketplace Insights API** → *sold* comparable transactions (the gold for
  valuation). Requires application approval but is the legitimate way to get
  sold comps.
- Free tier limits are generous for a personal tool. OAuth client-credentials
  flow; tokens cached and auto-refreshed in `valuation/ebay.py`.
- **Do not** scrape `ebay.com/sch` HTML. It violates the User Agreement, the
  markup is deliberately churned, and you'll be rate-limited fast.

### Craigslist — ⚠️ public RSS, politely
- No official API. Craigslist has historically litigated aggressively against
  scrapers (e.g. *Craigslist v. 3Taps*).
- Craigslist **does** publish RSS for search results (`&format=rss`). That is
  data offered for machine consumption. This repo uses only that.
- Guardrails baked in: long poll interval, descriptive `User-Agent` with a
  contact, on-disk caching, exponential backoff on 403/429, hard per-run caps.
- Even so: keep volume tiny, scope to one metro, and stop if you ever see a
  block. Do not parallelize across IPs to evade limits.

### Facebook Marketplace — ⛔ disabled, ToS-prohibited
- **There is no public Marketplace API**, and Facebook's Terms of Service
  expressly forbid automated data collection without written permission. The
  Graph API does **not** expose Marketplace listings.
- Marketplace sits behind authentication and is protected by sophisticated bot
  detection (TLS/JA3 fingerprinting, behavioral signals, device checks). Working
  around these means impersonating a logged-in human — a clear ToS violation
  with real legal exposure (*Meta v. Bright Data* and related cases).
- **Therefore `sources/facebook.py` is a stub that refuses to run.** It exists
  to document the boundary, not to cross it.
- **Legitimate alternatives** if you need Marketplace coverage:
  - Use Facebook's own **saved searches + native notifications** and act on
    them manually.
  - Source comparable inventory from platforms that *do* offer APIs/feeds
    (eBay, Mercari has limited options, OfferUp, local auction houses, estate
    sale aggregators).
  - License data from a provider that has its own agreements in place.

## General anti-scraping reality & how we cope

| Defense you'll hit        | Compliant response (in this repo)                         |
|---------------------------|-----------------------------------------------------------|
| Rate limits / 429         | Hard throttle + exponential backoff + per-run caps.       |
| IP bans                   | Stay under limits; **never** rotate IPs to evade a block. |
| TLS/JA3 fingerprinting    | Prefer APIs; don't spoof to defeat detection.             |
| CAPTCHAs                  | Treat as a stop sign, not an obstacle. We don't solve them.|
| Login walls               | Only fetch public, non-authenticated pages.               |
| HTML churn                | Prefer RSS/JSON/API over brittle HTML selectors.          |

### If you must use a headless browser
Only for sites with no API/feed, only on public pages. Configure it to be a
*good citizen*, not to evade detection:
- a real, current `User-Agent`;
- realistic viewport and locale;
- conservative, human-scale pacing (seconds between actions);
- respect `robots.txt`;
- caching so you never re-fetch the same page needlessly.

The moment your headless config is about defeating a bot challenge rather than
rendering JS for a public page, you're on the wrong side of the line.

## Operating principles

- **Public data only.** No logged-in sessions, no walled gardens.
- **Throttle generously.** Minutes between polls, not seconds.
- **Cache aggressively.** Don't re-pull what hasn't changed.
- **Fail safe.** On any block signal, back off and alert the operator.
- **Keep it personal-scale.** This is a tool for one buyer, not a data business.
