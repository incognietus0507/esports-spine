# Retail Arbitrage Strategy — Netherlands

A concrete, opinionated playbook for running this tool (and your time) profitably
in the Dutch market. Adapts the generic pipeline to NL platforms, categories,
fee/VAT reality, and a weekly operating cadence.

> Not legal/tax advice. Before scaling, confirm KvK/BTW specifics with a Dutch
> accountant — the margin scheme and registration rules genuinely affect margins.

---

## 0. The one-line thesis

**Buy locally on Marktplaats / at flea markets where sellers don't know an item's
value; resell to a bigger or more specialized audience (eBay.de, Catawiki,
Discogs).** NL is small, dense, and cheap to move around — so even mid-value
flips work, and the price gap between "Dutch seller who wants it gone" and
"German/collector buyer" is your margin.

---

## 1. Platforms

### Sourcing (buy cheap)
| Platform | Use it for | Tactic |
|----------|-----------|--------|
| **Marktplaats.nl** | Everything. The dominant NL classifieds. | Saved searches (*bewaarde zoekopdrachten*) + notifications; filter **"Gratis"** / **"Ophalen"**; sort by newest; *bieden* (negotiate). |
| **Kringloopwinkels** (thrift) | Furniture, ceramics, books, audio | Go early-week after weekend donations; build a route. |
| **Flea markets** | Bulk lots, collectibles | **IJ-Hallen** (Amsterdam-Noord, monthly — the big one), **Beverwijk Bazaar**, **Waterlooplein**, local *rommelmarkten*. |
| **Vinted** | Branded fashion, smaller items | Saved searches; snipe underpriced branded listings. |
| **Local auctions** | Estate/clearance lots | BVA Auctions, Vendu Notarishuis, *inboedel* clearances. |
| **Facebook Marketplace** | Secondary supply | Manual only — secondary to Marktplaats in NL. |

### Selling (capture value)
| Platform | Best for | Why |
|----------|----------|-----|
| **eBay.de** | Games, electronics, cameras, collectibles | Far bigger buyer pool than eBay.nl; ships easily within EU. |
| **Catawiki** | Antiques, design, watches, art, vintage | Curated auctions; collector audiences bid prices **up**; HQ in NL. |
| **Discogs** | Vinyl / CDs | The global record marketplace; deep price data. |
| **Marktplaats / Vinted** | Local resale, fashion | Fast, no shipping for local pickup. |
| **Bol.com** | *New* retail-arbitrage stock | NL/BE retail marketplace; third-party selling. |
| **Whatnot** | Live-selling lots (growing in EU) | Good for bulk/collectible liquidation. |

---

## 2. Categories that actually work in NL

Ranked by margin × ease. Start with one lane, don't spread thin.

1. **Dutch vintage design furniture** ⭐ *highest edge*
   - Brands sellers under-price because they don't recognize them:
     **Artifort, Pastoe, Gispen, Cees Braakman, Friso Kramer, Tomado** (wall
     racks), **Rietveld**, **Kembo**.
   - Economics: buy €20–80 → sell €150–600+. Local pickup = ~€0 logistics.
   - Sell on Catawiki / Marktplaats / Whatnot.
   - Edge: brand knowledge. Memorize maker's marks and labels.

2. **Retro games & consoles** — Nintendo (NES/SNES/Game Boy), Sega, PS1/PS2.
   Easy to value (sold comps), shippable. Sell eBay.de / Marktplaats.

3. **Vinyl records** — buy crates cheap, sort, sell singles on **Discogs**.
   Jazz/soul/funk/electronic hold value. Discogs gives you exact comps.

4. **Film cameras & lenses** — Leica, Contax, Nikon, Canon, Olympus. High
   value-to-weight, global demand on eBay. Test before listing.

5. **Vintage hi-fi / audio** — Marantz, Technics, Sansui, Sennheiser. Local
   pickup (heavy), strong local + DE demand.

6. **Pro tools** — Festool, Makita, Hilti. Resell briskly; easy to value.

7. **Watches & jewelry** — Seiko/vintage divers, etc. → Catawiki.

8. **Dutch ceramics/glass** — Delft, Makkum (Tichelaar), Royal
   Copenhagen, Leerdam glass. → Catawiki.

> Bulky-but-NL-classic (bicycles, large furniture) = great margins but solve
> logistics first; keep them **local pickup only**.

---

## 3. The numbers (build these into the profit model)

The tool's `ProfitModel` should reflect **EUR fees + the margin scheme**.

### Fees (approx — verify current rates)
- **eBay.de:** ~11–13% final value + payment processing.
- **Catawiki:** ~12.5% seller commission; buyer's premium is added on top of
  your hammer price (works in your favor).
- **Marktplaats:** free to list; small fee only if you use *Verkopen via
  Marktplaats* payments.
- **Vinted:** free for the seller (buyer pays Buyer Protection).
- **Discogs:** ~9% + payment.

### Shipping (PostNL/DHL)
- Small parcel within NL ≈ €4–7; to Germany ≈ €13–16.
- Local pickup (*ophalen*) = €0 — favor this for heavy items.

### VAT — the **margeregeling** (margin scheme) is the key lever
For secondhand goods bought from private individuals, a VAT-registered business
pays 21% **only on the margin**, not the full sale price:

```
VAT_owed = margin × 21 / 121        # 21% extracted from the gross margin
e.g. buy €100, sell €200 → margin €100 → VAT ≈ €17.36
```

> Requires proper bookkeeping (an *inkoopverklaring* / purchase record per item).
> If turnover is low, the **KOR** (small-business scheme, ~€20k threshold) lets
> you skip charging VAT entirely — simpler, but you can't reclaim input VAT and
> the margin-scheme math no longer applies. Pick one deliberately.

### Profit gate
Keep the tool's **30% net-margin** filter, computed on a *fully loaded* resale:
`net = resale − buy − platform_fee − shipping − margin_VAT − pickup_cost`.

---

## 4. Legal / admin checklist

- **KvK registration** once this is *structural* (regular, profit-seeking) — an
  **eenmanszaak** (sole proprietorship) is the usual start.
- **BTW (VAT)** number from the Belastingdienst; decide margeregeling vs KOR.
- **Income tax** — profit is taxable (box 1 if it's effectively a business).
- **Bookkeeping** — keep purchase records (needed for the margin scheme) and
  all sale/fee/shipping records.
- **Consumer law** — selling as a business carries *conformiteit* (warranty)
  obligations and return rights, even on secondhand. Price that risk in.

---

## 5. Weekly operating cadence

| When | Activity |
|------|----------|
| **Daily (15 min)** | Review Marktplaats saved-search alerts / the tool's Discord/Telegram pings. Respond to sellers **fast** — speed wins deals. |
| **Tue/Wed** | Kringloop route (fresh post-weekend stock). |
| **Thu** | List the week's finds; ship sold items (PostNL drop). |
| **Weekend** | Flea markets — prioritize **IJ-Hallen** on its monthly date; cash, arrive early. |
| **Monthly** | Reconcile books; review which categories actually netted 30%+ and prune the rest. |

---

## 6. 30-day starter plan (pick ONE lane)

**Recommended starter: retro games + vinyl** (easy to value, shippable, fast
feedback loop) *or* **Dutch design furniture** (highest margin, local, but needs
brand knowledge).

- **Week 1:** Set up Marktplaats saved searches for your lane. Learn 15–20 brand
  names / sold-comp price bands cold. Configure the tool (see §7).
- **Week 2:** Make 3–5 small buys under €30 each. List on the right channel.
  Measure *actual* net after fees/VAT/shipping vs. the tool's estimate.
- **Week 3:** Hit one flea market + one kringloop route. Tighten your buy
  ceiling so the 30% gate holds after real costs.
- **Week 4:** Review. Keep only categories that cleared 30% net. Register with
  KvK if it's working and recurring.

Target to validate the model: **10 completed flips, ≥30% net each**, before
scaling volume or adding a second lane.

---

## 7. How to point the tool at this strategy

The architecture is unchanged; swap the adapters and tune the model:

- **Source adapter:** add a `MarktplaatsSource` (replace/augment Craigslist).
  ⚠️ Marktplaats & Catawiki **prohibit scraping** in their ToS — use their
  official seller/feed channels or a polite manual workflow, per `COMPLIANCE.md`.
- **Valuation:** comp against **eBay.de** + **Catawiki** (and **Discogs** for
  vinyl) instead of eBay US.
- **Profit model (`arbitrage/config.py` → `ProfitModel`):**
  - fees in EUR per target platform,
  - add a **margeregeling VAT** term (`margin × 21/121`),
  - set `acquisition_cost` low (dense geography / local pickup),
  - keep `MIN_PROFIT_MARGIN=0.30`.
- **Categories:** set `SEARCH_TERMS` to your brand list (Artifort, Pastoe,
  Game Boy, …) rather than broad category codes.

> Next build step, if you want it: I can add a `MarktplaatsSource` stub +
> a EUR/margeregeling profit model and a Catawiki/eBay.de valuation note,
> mirroring the existing Craigslist/eBay structure.
