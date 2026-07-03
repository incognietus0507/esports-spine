# Project Roadmap — Retail Arbitrage (NL)

Living checklist. One phase per working session; every code phase ends with
tests green + review-agent pass + a push to the feature branch.

**Lane locked (Phase 0):** Vinyl — Marktplaats (authorized feed) → Discogs
valuation → 30% net-margin gate. Rationale: the only fully-automatable NL
combo (official Discogs API), small/flat/cheap to ship, fast feedback loop.
Second lane (design furniture / retro games) only after 10 validated flips.

---

## Phase 0 — Lock scope & baseline ✅ DONE (2026-07-02)
- [x] Lane chosen: vinyl (Marktplaats → Discogs)
- [x] Security audit of `.claude/`: AgentShield grade B, 0 critical/high after
      fixes (code-simplifier Bash removed; permissions deny-block added).
      Details + accepted risks in `.claude/ECC-MANIFEST.md`.
- [x] Test baseline green (40 tests) + CI workflow in place
- [x] ROADMAP.md committed

## Phase 1 — Real Marktplaats ingestion ✅ interim path DONE (2026-07-03)
- [ ] Evaluate official access: Marktplaats partner/Admarkt API or business
      export (requires an account/application — USER ACTION, still open)
- [x] Interim compliant path: local JSON feed (`MARKTPLAATS_FEED_FILE`)
- [x] Saved-search config: watchlist file (`WATCHLIST_FILE`, one term/line)
      filters the feed per lane; starter list `watchlist-vinyl.example.txt`
- [x] Intake CLI: `python -m arbitrage.intake "<title>" "<price>" <url>
      [--location X] [--run]` — 5-second logging from a Marktplaats
      notification, duplicate-URL safe
- [ ] Pagination + rate limiting on the official channel (blocked on access)
- Agents/skills: `python-reviewer` pass done; `api-connector-builder` waits
  for API credentials

## Phase 2 — Matching & valuation quality ✅ DONE (2026-07-03)
- [x] Discogs title→release plausibility matcher (token overlap)
- [x] Fuzzy matching upgrade: diacritics folding (Motörhead≡Motorhead, also in
      watchlist), artist-segment guard (same-titled album by another artist
      rejected), catalog-number extraction with catno-first Discogs search
- [x] Match-precision fixture suite (tests/test_matching.py, TDD red→green)
- [ ] eBay comp matching gets the same treatment (only if eBay lane activates)
- Agents/skills: `tdd-workflow` followed; `python-reviewer` pass

## Phase 3 — Robustness, config & secrets ✅ DONE (2026-07-03)
- [x] Fail-fast env parsing; failed valuations retry instead of being lost
- [x] Startup validation: Config.validate() runs in build_pipeline (daemon and
      intake --run); invalid config exits with every problem listed
- [x] Range checks: fee/VAT/confidence 0–1, costs ≥ 0, interval/budget bounds
- [x] Consistent retry/backoff: shared httputil.get_with_backoff (429 + 5xx,
      exponential) used by Discogs and eBay clients; eBay 403-insights
      fallback preserved
- Agents: `silent-failure-hunter` audit done; all CRITICAL/HIGH/MEDIUM
  findings fixed (mark_seen ordering, per-listing isolation, valuator
  exception breadth, scheduler error listener, alert-outage aggregation)

## Phase 4 — Observability & reporting
- [ ] Run-history table (per-run stats: fetched, valued, alerted)
- [ ] Daily digest (found/alerted/hit-rate) via existing alert channels
- [ ] Estimate-vs-outcome log for calibration (enter real sale results)
- Agents/skills: `database-migrations`, `doc-updater`

## Phase 5 — CI/CD & quality gates
- [x] CI: unittest on push/PR
- [ ] Add ruff + coverage gate (80% per repo rules) to CI
- [ ] bandit security scan in CI
- [ ] SessionStart hook for web sessions (auto-verify env)
- Skills: `github-ops`, `/build-fix`

## Phase 6 — Packaging & deployment
- [ ] Dockerfile + compose; run scheduled on VPS/GitHub Actions
- [ ] Secrets via env/secret manager; healthcheck + failure alert
- Agents: `architect`, `code-simplifier`, `refactor-cleaner`

## Phase 7 — Compliance & calibration (ongoing)
- [ ] Marktplaats authorized-access decision documented
- [ ] KvK/BTW decision (margeregeling vs KOR) once trading is structural
- [ ] Backtest the 30% gate on ≥10 real flips; retune fees/VAT from actuals
