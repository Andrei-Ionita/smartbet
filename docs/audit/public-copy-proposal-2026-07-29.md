# Public copy proposal — verified pricing standard

**Status:** DRAFT — **NOT DEPLOYED. Awaiting founder approval.**
**Context:** `docs/audit/gem-selector-diagnostics-2026-07-29.md`

## Framing

BetGlitch is introducing a **stricter verified pricing standard**. Every
published price is now tied to an exact betting market, line, outcome,
bookmaker and capture time, and every published claim is snapshotted and hashed
so it can never change.

The verified pricing record therefore **begins at a stated cutoff**. Earlier
predictions remain visible but are excluded from ROI and other price-dependent
reporting, because their original price snapshots cannot be reconstructed to the
new standard. **No historical row has been deleted.**

**No positive ROI is claimed anywhere until the verified record contains
resolved predictions.**

Language avoided throughout: describing the old ROI as valid; implying prices
were corrected; implying nothing went wrong; dramatic self-flagellation; any
profit figure on a zero sample; guarantees or "start winning" phrasing.

**Timing column:** *Deploy* = must ship with the corrected dashboard.
*Marketing* = must be right before any public promotion, but does not block the
verified record from accumulating.

---

## 1. Homepage — `app/page.tsx`

| Current | Proposed | Reason | When |
|---|---|---|---|
| Hero stat: `{accuracy_percent}%` under **"Verified Smart Picks"** (line 143) | Keep the accuracy figure, relabel to **"Model accuracy — verified results"**, and render **"Building verified record"** whenever `total_bets === 0` | Accuracy is not price-dependent and stays valid, but "Verified Smart Picks" reads as a verified *profit* claim. A zero sample must not display a number. | **Deploy** |
| "🔍 **100% Transparent:** These recommendations are logged & tracked on our public track record • All predictions timestamped before kickoff • Real results verified by 3rd party sources" (lines 264–266) | "🔍 **Fully transparent:** Every recommendation is logged before kickoff on our public track record • Published picks are snapshotted and hashed so they can't be edited • Results verified against third-party data" | "100% Transparent" is unsupportable while the pricing record is being rebuilt. The replacement states what is now actually true, including the new immutability guarantee. | **Deploy** |
| "Only top European leagues with verified data sources and proven accuracy" (line 526) | "Selected European leagues with verified data sources" | "Proven accuracy" is a performance claim resting on the contaminated record. | **Marketing** |

## 2. Transparency dashboard — `core/transparency_views.py` (`methodology`, lines 37–43)

| Current | Proposed | Reason | When |
|---|---|---|---|
| `selection_criteria`: "Minimum 60% confidence AND positive Expected Value" | "Minimum 55% confidence for Over/Under 2.5 and 60% for other markets, plus positive expected value at the recorded price" | **Factually wrong today.** `over_under_2.5` ships at 0.55 and 54 published rows sit in 0.55–0.60. | **Deploy** |
| `integrity`: "Historical data never deleted or edited" | "Published claims are immutable: each is snapshotted with a SHA-256 hash when it goes public and is never rewritten. Our live model keeps improving; a published claim does not. Nothing is ever deleted." | **Was not true as written** — the pipeline overwrote odds, confidence and the selection on every re-run, and there was no `updated_at` to prove otherwise. It is true now, for claims. | **Deploy** |
| `verification`: "Third-party API - results cannot be manipulated" | "Match results come from a third-party API and cannot be edited by us. Prices are recorded with their exact market, line, bookmaker and capture time, so any published quote can be independently checked." | True of results, but silent on prices — which is exactly where the defect was. | **Deploy** |
| `timestamp_proof`: "All predictions logged BEFORE matches start" | "Every published claim is timestamped before kickoff." | 2 of 315 legacy rows were logged after kickoff. Scoping this to *published claims* makes it exactly true. | **Deploy** |
| `honesty`: "We show both wins and losses - complete transparency" | **Unchanged** | Accurate, and the differentiator. | — |
| `data_source`, `frequency`, `what_we_track` | **Unchanged** | Verified accurate. | — |
| *(new key)* | `pricing_standard`: "Verified pricing record begins {CUTOFF_DATE}. Earlier predictions are shown but excluded from ROI reporting — their original price snapshots could not be verified to this standard." | The reset must be discoverable from the API, not only the UI. | **Deploy** |

## 3. Accuracy page / methodology block — `core/transparency_views.py:100`

| Current | Proposed | Reason | When |
|---|---|---|---|
| `criteria`: "Minimum 60% confidence + Positive Expected Value" | Same replacement as §2 row 1 | Second copy of the same false claim; both must move together or they will diverge again. | **Deploy** |

## 4. Monitoring page — `app/monitoring/page.tsx`

| Current | Proposed | Reason | When |
|---|---|---|---|
| description: "Real-time monitoring of BetGlitch AI prediction models. Track accuracy, calibration, and performance metrics across all leagues." | "Real-time monitoring of BetGlitch prediction models: accuracy, calibration and verified pricing performance." | "performance metrics" now spans two different universes; naming verified pricing avoids implying the P/L figures cover all history. | **Marketing** |
| *(in-page, new)* | Label above price-dependent blocks: **"Profit figures count verified-pricing results only. Accuracy covers all tracked predictions."** | The page now mixes two universes by design — accuracy on all rows, money on verified rows. Unlabelled, that is misleading. | **Deploy** |

## 5. Leagues — `/api/transparency/leagues/`

| Current | Proposed | Reason | When |
|---|---|---|---|
| Returned 241 rows for 25 leagues; ROI per league from unverified prices | No copy change. Fixed in code (`DISTINCT` bug) and now on the verified universe, so it returns one row per league and is empty until verified results exist. | Public endpoint, no page renders it — a copy change is not required, but it must not serve wrong numbers. | **Deploy** (code, done) |

## 6. Proof page — `app/proof/[fixtureId]/`

| Current | Proposed | Reason | When |
|---|---|---|---|
| Unpublished/missing: "**Proof not found** — This pick isn't in our published, recommended track record." | "**Not published as a claim** — This prediction has not been published as an immutable BetGlitch claim." *(sub-line: "We only publish proof for picks we have snapshotted and hashed before kickoff.")* | "Not found" implies the fixture does not exist. The real state is: it exists but was never published as immutable proof. **Implemented.** | **Deploy** |
| OG card fallback: "Proof not found" | "Not published as a BetGlitch claim" | Same reason; this is the text that unfurls in chat apps. **Implemented.** | **Deploy** |
| Card footer record line | Unchanged wording, but now sourced from the verified universe, and suppressed at zero sample (see §7) | The card must never show a season record the site itself no longer claims. | **Deploy** |

## 7. Empty states

| Surface | Current | Proposed | Reason | When |
|---|---|---|---|---|
| Track record ROI tile | Renders **green "+0%"** when `total_bets === 0` | "**No verified results yet** — Our verified pricing record restarted and fills in as matches settle." | A zero-sample record rendered green reads as break-even performance. **Implemented.** | **Deploy** |
| Homepage hero stat | Shows `0%` | "Building verified record" | Same defect on the highest-traffic surface. | **Deploy** |
| Proof card footer | "0W – 0L · +0% ROI" | "Verified record starts {CUTOFF_DATE}" | Do not print a profit figure on an empty sample. | **Deploy** |

## 8. Pricing page — `app/pricing/PricingContent.tsx`

| Current | Proposed | Reason | When |
|---|---|---|---|
| "Everything you need to win" (line 106) | "Everything in Free, plus full access" | "…to win" is a profit promise, and unsupportable with no verified record. | **Deploy** |
| "Yes! We offer a 30-day money-back guarantee…" (lines 170–171) | **Unchanged** | A refund guarantee is a commercial term, not a performance claim. Legitimate. | — |

*(Payments remain blocked on Polar KYC, so this page is not yet transactable — but the copy should be corrected before it is.)*

## 9. Proposed disclosure (the reset)

Shown wherever ROI or the track record appears.

> **Our verified pricing record begins {CUTOFF_DATE}.**
> We have introduced a stricter standard for recorded prices: every published
> pick is now tied to an exact betting market, line, outcome and bookmaker, with
> the time the price was captured.
>
> Predictions made before this date are still here — nothing has been deleted —
> but they are excluded from ROI and other price-dependent reporting, because
> their original price snapshots cannot be reconstructed to this standard. We
> chose to restart the record rather than estimate prices we could not verify.

**Compact variant** (cards, footers):

> Verified pricing record begins {CUTOFF_DATE}. Earlier predictions are shown but
> excluded from ROI — their original prices could not be verified to our current
> standard.

**One-line variant** (tooltips):

> ROI counts verified-pricing results only, from {CUTOFF_DATE}.

## 10. Standing language rules

**Banned:** guaranteed, lock, banker, sure bet, easy money, "the market is
wrong" as fact, "everything you need to win", any profit promise, win-only
framing, and any ROI figure not computed from `public_universe.priced_qs()`.

**Required:** model probability always shown next to the bookmaker's implied
probability — `confidence` is a provider-derived score and is **not**
empirically calibrated (audit finding F3), so it must never be presented as a
bare probability.

## 11. Sequencing

The copy must ship **with** the corrected dashboard. Publishing the empty record
without the disclosure looks like a bug or a cover-up; publishing the disclosure
while the old ROI is still on screen is a contradiction.

`{CUTOFF_DATE}` is substituted from the validated deployment timestamp
(`PRICING_INTEGRITY_CUTOFF`), rendered as a plain date, e.g. "30 July 2026".
