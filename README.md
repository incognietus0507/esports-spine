# Retail Arbitrage Automation

A modular pipeline that monitors local marketplace listings, cross-references
them against eBay market values, calculates potential net profit, and fires a
real-time alert when an item clears a configurable profit threshold.

> ⚠️ **Read [`COMPLIANCE.md`](COMPLIANCE.md) before pointing this at any live
> platform.** Some of the sources requested (notably Facebook Marketplace)
> prohibit automated access in their Terms of Service. This project ships with
> the *compliant* paths enabled by default (eBay official APIs, Craigslist
> public RSS) and the *non-compliant* paths disabled and stubbed.

---

## 1. Conceptual Architecture

The system is a classic **collect → enrich → decide → notify** pipeline. Each
stage is decoupled so a misbehaving source or a rate-limited API never takes the
whole pipeline down.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            SCHEDULER (APScheduler)                        │
│                   runs the pipeline every N minutes                       │
└───────────────┬───────────────────────────────────────────────────────────┘
                │
        ┌───────▼────────┐
        │  1. SOURCES    │  Pluggable adapters, one per marketplace.
        │  (collect)     │  Each yields a stream of normalized Listing objects.
        │                │
        │  • Marktplaats │  → AUTHORIZED feed only (JSON export/partner API)
        │  • Facebook MP │  → DISABLED stub (ToS-prohibited, see COMPLIANCE)
        └───────┬────────┘
                │  List[Listing]   (title, price, location, url, source)
                │
        ┌───────▼────────┐
        │  2. DEDUPE     │  SQLite-backed seen-set keyed by (source, listing_id).
        │  (state)       │  Only brand-new listings continue down the pipe.
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │  3. VALUATION  │  For each new listing, query eBay for comparable
        │  (enrich)      │  ACTIVE + SOLD listings and compute a robust
        │                │  market value (trimmed median of sold comps).
        │                │  → eBay Browse API (active) + Marketplace Insights
        │                │    API (sold). Official, keyed, compliant.
        └───────┬────────┘
                │  market_value, comp_count, confidence
                │
        ┌───────▼────────┐
        │  4. PROFIT     │  net_profit  = resale - buy - ebay_fees -
        │  (decide)      │                shipping - acquisition(gas)
        │                │  margin      = net_profit / buy_price
        │                │  Filter: keep margin >= THRESHOLD (default 30%).
        └───────┬────────┘
                │  List[Opportunity]
                │
        ┌───────▼────────┐
        │  5. ALERTS     │  Fan-out to one or more channels.
        │  (notify)      │  • Discord webhook  • Telegram bot  • SMTP email
        └────────────────┘
```

### Why this shape

- **Adapter pattern for sources** (`arbitrage/sources/base.py`): adding
  OfferUp, Mercari, or a new region is a new file, not a rewrite.
- **Stateful dedupe** prevents alert spam — you get pinged once per listing,
  not once per poll cycle.
- **Valuation isolated from sourcing** means you can swap the eBay strategy
  (official API vs. a priced dataset) without touching scrapers.
- **Alert fan-out** lets you start with Discord and add email later for free.

---

## 2. Recommended Tech Stack

| Concern              | Choice                          | Why |
|----------------------|---------------------------------|-----|
| Language             | **Python 3.11+**                | Best scraping/data ecosystem. |
| HTTP                 | **httpx**                       | Async-capable, HTTP/2, modern. |
| Data validation      | **pydantic v2**                 | Typed, validated domain models. |
| Scheduling           | **APScheduler**                 | In-process cron without a broker. |
| Persistence          | **SQLite** (stdlib `sqlite3`)   | Zero-ops dedupe + audit log. |
| eBay data            | **Official eBay REST APIs**     | Browse (active) + Marketplace Insights (sold). |
| HTML/feeds           | **feedparser** + **selectolax** | Fast RSS + HTML parse where needed. |
| Headless (last resort)| **Playwright**                 | Only when no API/feed exists. |
| Config               | **python-dotenv** + env vars    | Secrets out of source. |
| Logging              | **structlog**                   | Structured, greppable logs. |
| Packaging/runtime    | **Docker** (optional)           | Reproducible deploy on a VPS. |

**Scaling note:** this single-process design comfortably handles a handful of
saved searches polled every few minutes. If you grow to dozens of searches or
need horizontal scale, promote the queue between stages to **Redis + RQ/Celery**
and move state to **Postgres**. The interfaces here are built so that swap is
localized.

---

## 3. Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # only needed for the headless source

cp .env.example .env                 # then fill in your keys
python -m arbitrage.main --once      # single pass (dry run friendly)
python -m arbitrage.main             # run on the schedule
```

Run with no eBay/Discogs credentials and the pipeline drops into **mock
valuation** mode so you can exercise the full flow end-to-end before wiring
real APIs (set `MIN_COMP_CONFIDENCE=0.2` in production so mocks never alert).

### Daily NL workflow (vinyl lane)

1. Create Marktplaats **saved searches** for each term in your watchlist
   (start from `watchlist-vinyl.example.txt`, set `WATCHLIST_FILE`).
2. When Marktplaats notifies you of a hit, log it in ~5 seconds:

   ```bash
   python -m arbitrage.intake "Miles Davis Kind of Blue LP" "€ 25" \
       https://link.marktplaats.nl/m123... --location Utrecht --run
   ```

3. The pipeline values it against Discogs (`VALUATION_SOURCE=discogs`),
   applies eBay/Discogs fees + margeregeling VAT, and alerts if net margin
   clears 30%. Duplicates are skipped automatically.

---

## 4. Key Technical Challenges & Compliant Alternatives

This is the part that decides whether the project is sustainable. Summary here;
full detail in [`COMPLIANCE.md`](COMPLIANCE.md).

| Platform | The challenge | The compliant path this repo takes |
|----------|---------------|------------------------------------|
| **eBay** | Naive HTML scraping breaks constantly and is rate-limited. | Use the **official Browse + Marketplace Insights APIs** (free tier, OAuth). Implemented in `valuation/ebay.py` (`EBAY_MARKETPLACE_ID=EBAY_DE` for NL). |
| **Marktplaats** | No public API for consumers; ToS prohibit scraping; bot detection. | **Authorized feeds only**: partner/Admarkt API, business exports, or a local JSON file you maintain (`MARKTPLAATS_FEED_FILE`). Implemented in `sources/marktplaats.py` + `sources/feeds.py`. |
| **Discogs** | — | **Official API** with price suggestions + marketplace stats. Implemented in `valuation/discogs.py` (`VALUATION_SOURCE=discogs`). |
| **Facebook Marketplace** | **No public API. The ToS explicitly prohibit automated collection.** Heavy bot detection (TLS/behavioral fingerprinting), login walls, and legal exposure. | **Shipped disabled.** The adapter is a stub that raises unless you supply your own compliant data source. Recommended legitimate alternative: manual saved searches + Facebook's own notifications, or a licensed data provider. |
| **All** | Anti-bot: TLS fingerprinting, rate limits, CAPTCHAs, IP bans. | Prefer APIs; when scraping public feeds, throttle hard, set a real `User-Agent` + contact, cache, respect `robots.txt`, and back off on 429/403. |

**Bottom line:** prefer official APIs every time one exists. Where it doesn't,
restrict yourself to data the platform *publishes for machine consumption*
(RSS), stay well under any rate limit, and never bypass a login wall or bot
challenge. The economics of arbitrage do not survive a platform ban or a
cease-and-desist.

---

## 5. Layout

```
arbitrage/
  config.py            # env-driven settings + thresholds
  models.py            # Listing / Comparable / Opportunity (pydantic)
  store.py             # SQLite dedupe + opportunity log
  pipeline.py          # wires the stages together
  main.py              # CLI entrypoint + scheduler
  profit.py            # fee/shipping/gas → net profit & margin
  sources/
    base.py            # Source ABC + Listing contract
    marktplaats.py     # authorized-feed adapter (no scraping)
    feeds.py           # local JSON feed loader
    facebook.py        # DISABLED stub (ToS)
  valuation/
    ebay.py            # official-API valuation (+ mock fallback)
    discogs.py         # official Discogs API (vinyl/CDs)
    catawiki.py        # note: no compliant comps API — manual check
  alerts/
    base.py            # Alerter ABC
    discord.py         # webhook
    telegram.py        # bot sendMessage
    email_smtp.py      # SMTP
```
