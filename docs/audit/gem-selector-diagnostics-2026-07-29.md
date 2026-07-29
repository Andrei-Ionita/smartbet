# Hidden-Gem Selector — Production Diagnostics (D1–D7 + P1–P3)

**Date:** 2026-07-29
**Scope:** Read-only diagnostics against production, run before implementing the
selector specified in `docs/superpowers/specs/2026-07-27-gem-selector-design.md`.
**Decision:** 🔴 **BLOCKED — DO NOT IMPLEMENT, DO NOT PUBLISH**

---

## 0. Executive summary

The diagnostics were intended to calibrate the selector's parameters. They
instead surfaced a defect that invalidates the evidence base the selector would
rest on.

**Headline finding (F1): the recorded `odds` are systematically wrong — they are
frequently taken from a different betting market than the one we grade against.**

- The odds-matching logic accepts **any** SportMonks market whose name or label
  contains the string `"2.5"`, then takes the **first** match in arbitrary API
  order. SportMonks returns ~38 such entries per fixture across at least seven
  different `market_id`s.
- Verified live: for **SC Cambuur v Excelsior** we store **3.50**; the true goals
  market (`market_id 7`) prices Over 2.5 at **1.60** — a **2.19×** overstatement.
- **Every** live Over/Under pick checked is overstated (1.11× to 2.19×).

**Consequence:** the published ROI is not real. Removing the contaminated
long-odds tail turns the recommended portfolio from **+5.59% to −4.90%**.

| Basis | n | ROI |
|---|---|---|
| As published today (dashboard + proof cards) | 276 | **+10.61%** |
| Audit standard (excl. quarantined/archived) | 268 | **+5.59%** |
| Audit standard, excl. contaminated odds ≥ 3.0 | 246 | **−4.90%** |

Three independent problems each inflate the public number, and they compound.
The selector cannot be calibrated on this data, and the currently-live proof
cards are publishing an inflated record.

---

## 1. Method and safety

**Access:** Railway CLI → `DATABASE_PUBLIC_URL` (TCP proxy) → psycopg2.

**Read-only enforcement,** verified before any query:

```python
conn.set_session(readonly=True, autocommit=True)
cur.execute("SET default_transaction_read_only = on")
```

Probe result: `CREATE TEMP TABLE` → `cannot execute CREATE TABLE in a read-only
transaction`. Every statement was `SELECT`/`WITH`; a guard in `db.q()` refuses
anything else. **No rows modified, no migrations, no constants changed, no code
altered, nothing published.**

**Artifacts** (committed alongside this report): `analysis.py` (D3–D7 census),
`sim.py` (gate simulation). The credentialed `db.py`/`pull.py` remain local and
are not committed.

**Universe definitions used throughout:**

- **Universe A** — what `AccuracyCalculator` actually computes, i.e. what the
  public dashboard and every proof card display:
  `is_recommended AND actual_outcome IS NOT NULL AND <per-market conf gate>`
- **Universe B** — the audit standard used by every script in `docs/audit/`:
  Universe A **plus** `NOT is_audit_excluded AND match_status <> 'archived'`

---

## 2. Findings

### F1 🔴 Odds are captured from the wrong market (CRITICAL)

**Inspection method.** Read `smartbet-frontend/app/api/recommendations/route.ts`
lines 476–515, then fetched live SportMonks odds for four pending fixtures and
replayed the production matcher against the real payload.

**The defect** (`route.ts:477-485`):

```ts
const nameMatch = odd.name?.toLowerCase().includes('2.5') ||
                  odd.label?.toLowerCase().includes('2.5')
```

Any market containing `"2.5"` passes this filter. The loop then accepts the
**first** entry whose label contains `over`/`under` with a value in
`[1.30, 3.50]`, and `break`s — so selection depends on arbitrary API ordering,
not on market identity. This is why the recorded `bookmaker` differs on almost
every row.

**Raw evidence** — fixture 19714700 (SC Cambuur v Excelsior), 491 odds entries,
38 containing `"2.5"`, spanning `market_id` 7, 37, 53, 80, 86, 105, 107:

| market_id | label | name | total | value |
|---|---|---|---|---|
| **7** (true goals O/U) | Over | Over | 2.5 | **1.60** |
| 7 | Under | Under | 2.5 | 2.20 |
| 105 | Over | 2.5 | 2.5 | 1.60 |
| 107 | Over | 2.5 | 2.5 | 5.75 |
| 37 | Over | 2 | 2.5 | 3.60 |
| **53** | Over | 2.5 | — | **3.50** ← what we stored |
| 86 | 1 | — | Under 2.5 | 1.20 |

**Stored vs. true price, all live O/U picks:**

| Fixture | Stored | True (`market_id 7`) | Overstatement |
|---|---|---|---|
| Falkirk v St. Mirren | 2.05 | 1.78 | 1.15× |
| Aberdeen v Hearts | 1.87 | 1.68 | 1.11× |
| Celtic v Dundee | 3.00 | *no mkt-7 data* | unverifiable |
| SC Cambuur v Excelsior | 3.50 | 1.60 | **2.19×** |

**Statistical signature in the historical data.** If the odds were genuine, win
rate should track implied probability. It does — *except* in the tail:

| Odds band | n | win rate | implied | gap | ROI |
|---|---|---|---|---|---|
| 1.0–1.5 | 75 | 70.7% | 73.0% | −2.3 | −4.14% |
| 1.5–1.8 | 95 | 52.6% | 61.3% | −8.7 | −13.90% |
| 1.8–2.2 | 59 | 54.2% | 52.5% | +1.7 | +3.43% |
| 2.2–2.6 | 5 | 40.0% | 43.3% | −3.3 | −7.40% |
| 2.6–3.0 | 4 | 50.0% | 36.4% | +13.6 | +37.50% |
| **3.0–3.6** | **22** | **68.2%** | **30.2%** | **+38.0** | **+122.95%** |

A sustained +38pp edge over 22 bets is not credible. The mechanism explains it:
these are high-scoring fixtures (Barcelona v Betis, Villarreal v Atlético,
Racing 4–1, Villarreal 5–1) where the *true* Over 2.5 price is short (~1.4–1.6)
and some other 2.5-labelled market is long. We record the long price, then grade
against goals — which duly land.

**Impact:** those 22 rows contribute **+270.5** P/L against a portfolio total of
**+149.8** — i.e. **180%** of all profit. Excluding them, ROI is **−4.90%**.

**Interpretation.** Grading is correct (all 13 longshots verified: Over 2.5 = 3+
goals, correctly settled). The defect is purely in **price capture**. It inflates
EV at selection time, inflates ROI after settlement, and would publish prices no
reader can obtain.

**Parameter impact:** invalidates D2, D3, D4 and the entire gate calibration.
**No parameter set can be finalised until this is fixed and the odds backfilled.**

---

### F2 🔴 Quarantined bad-data rows are counted in public stats

**Method:** compared Universe A vs Universe B.

```sql
-- Universe A: is_recommended AND actual_outcome IS NOT NULL AND <conf gate>
-- Universe B: + NOT is_audit_excluded AND match_status <> 'archived'
```

| Universe | n | W | L | ROI |
|---|---|---|---|---|
| A — dashboard + proof cards | 276 | 166 | 110 | **+10.61%** |
| B — audit standard | 268 | 159 | 109 | **+5.59%** |

**Cause:** `AccuracyCalculator._recommended_base_qs()`
(`core/services/accuracy_calculator.py:52-58`) filters `is_recommended` and
`actual_outcome__isnull=False` plus the confidence gate — but **never excludes
`is_audit_excluded`**, while every script in `docs/audit/` does.

**The 8 offending rows** all share `expected_value = 0.5` exactly and **NULL
odds** — the residue of the known back-calc-from-EV bug. Seven of eight are
"wins" with fabricated payouts (+178.75% ROI as a group).

**Interpretation:** rows explicitly quarantined as untrustworthy are inflating
the headline by **+5.0pp**, and that inflated number is **already rendered on
every live proof card** ("161W – 106L · +9.6% ROI" and its successors).

**Parameter impact:** all cell statistics must use Universe B. The public
dashboard must be corrected independently of the selector.

---

### F3 🟡 Confidence: uniform 0–1, and far less over-confident than assumed

**D1 — storage scale.**

```sql
SELECT count(*), count(*) FILTER (WHERE confidence > 1.0) AS gt_1,
       min(confidence), max(confidence) FROM core_predictionlog;
```

| rows | `> 1.0` | NULL | min | max |
|---|---|---|---|---|
| 795 | **0** | 0 | 0.4276 | 0.7401 |

**Resolved: the scale is uniformly 0–1.** No mixed-scale rows exist. The
`models.py:30` comment `# e.g., 62.5` is **stale and misleading** — it implies
0–100 and was the basis for the spec's blocking concern.

**D2 — measured over-confidence** (Universe B), `mean(confidence) − win_rate`:

| Market | n | measured margin |
|---|---|---|
| over_under_2.5 | 260 | **+0.0304** |
| btts | 4 | −0.1229 (noise) |
| 1x2 | 4 | +0.1259 (noise) |
| **Overall** | **268** | **+0.0296** |

**Interpretation:** over-confidence is **~3pp, not ~20pp**. The "≈20pp" figure
carried in project memory and repeated in the v2 spec is **not supported** by
current data. `FALLBACK_MARGIN = 0.05` is conservative and reasonable.

**Caveat:** this margin is computed against *contaminated* outcomes-vs-price data
(F1 does not affect win rate, so the margin itself is probably sound — margin
depends only on confidence and win/loss, not odds).

**Semantics:** `confidence` is a SportMonks provider probability passed through
market selection. It is **not empirically calibrated** → must not be published as
a bare probability. Spec §3.1 stands.

**D2c — calibration by bucket (non-monotone, confirming the July study):**

| Bucket | n | mean conf | win rate | margin | avg odds | ROI |
|---|---|---|---|---|---|---|
| 0.55–0.60 | 54 | 0.583 | 61.1% | −0.028 | 2.238 | **+30.90%** |
| 0.60–0.65 | 163 | 0.621 | 55.8% | +0.063 | 1.741 | −0.13% |
| 0.65–0.70 | 47 | 0.668 | 66.0% | +0.008 | 1.483 | −6.19% |
| 0.70+ | 4 | 0.707 | 100% | −0.293 | 1.356 | +35.63% |

Higher confidence does **not** mean higher ROI — 0.65–0.70 is well-calibrated yet
loses money because the prices are too short (avg 1.483).

---

### F4 🔴 Only one cell qualifies — and it is contaminated and fragile

**D3 — cell census** (Universe B; bootstrap CI = 10,000 resamples, seed 42):

| Cell | n | W | L | avg odds | raw ROI | shrunk ROI | CI 95% | last-20 ROI |
|---|---|---|---|---|---|---|---|---|
| over_under_2.5@0.60-0.65 | 155 | 86 | 69 | 1.739 | −0.84% | −0.64% | [−16.02, +14.52] | +91.75% |
| **over_under_2.5@0.55-0.60** | **54** | 33 | 21 | 2.238 | **+30.90%** | **+16.04%** | **[+0.11, +62.04]** | +16.25% |
| over_under_2.5@0.65+ | 51 | 35 | 16 | 1.473 | −2.91% | −1.47% | [−21.57, +15.09] | −2.05% |
| 1x2@0.60-0.65 | 4 | 2 | 2 | 1.810 | −3.75% | −0.28% | [−100, +92.5] | — |
| btts@0.60-0.65 | 4 | 3 | 1 | 1.768 | +31.00% | +2.30% | [−56.25, +79.0] | — |

**Exactly one cell** clears `n ≥ 40 AND shrunk_roi ≥ 2%`:
`over_under_2.5@0.55-0.60`. Its bootstrap lower bound is **+0.11%** — significant
by the thinnest possible margin.

**Fragility — where its profit comes from:**

| Odds band | n | W | L | ROI | P/L contribution |
|---|---|---|---|---|---|
| 1.4–1.8 | 9 | 9 | **0** | +59.17% | +53.3 |
| 1.8–2.2 | 26 | 14 | 12 | +3.19% | +8.3 |
| 2.2–3.0 | 5 | 1 | 4 | −55.80% | −27.9 |
| **3.0–5.0** | **13** | 8 | 5 | **+100.00%** | **+130.0** |

**78% of the cell's profit comes from the 13 contaminated longshots** identified
in F1. Leave-one-out confirms the concentration:

| Drop top k winners | n | ROI | shrunk |
|---|---|---|---|
| 0 | 54 | +30.90% | +16.04% |
| 1 | 53 | +26.76% | +13.77% |
| 3 | 51 | +18.30% | +9.24% |
| 5 | 49 | **+9.56%** | +4.73% |

Five bets out of 54 carry two-thirds of the edge.

**Counter-evidence (in fairness):** the cell is *chronologically* stable — first
half +29.39%, second half +32.41%. But both halves draw on the same contaminated
price source, so stability does not rescue it.

**Interpretation:** the one cell the selector would publish from is precisely the
cell most contaminated by F1. This is not a coincidence — the bad prices are long
odds, and long odds concentrate in the low-confidence bucket.

---

### F5 🟢 League-tier veto would not fire (and the gem thesis holds directionally)

**D4/D5 — 25 distinct leagues, Universe B.** Tier totals:

| Tier | n | ROI |
|---|---|---|
| A (mainstream) | 73 | **−1.53%** |
| B (second tier) | 113 | +12.76% |
| C / UNKNOWN | 82 | +2.05% |

Within the qualifying cell, **all three tiers are positive** (A +40.18% n=11,
B +28.38% n=25, C +28.72% n=18), so no tier veto fires and spec §4.4's concern
does not materialise — *on contaminated data*.

Mainstream leagues being the *worst* tier is directionally consistent with the
hidden-gem thesis.

**Mapping caveat:** the provisional tier map needs founder review. `Premiership`
(Scottish) vs `Premier League`, `Super League` (Swiss/Greek/other), `Premier
League (additional)` and `Superliga` are all ambiguous by name, and `league_id`
is **hardcoded `None`** at write time (`api_views.py:771`), so exact-id mapping
is unavailable.

---

### F6 🟡 Lead time contradicts the revised timing window

**D7 —** `kickoff − prediction_logged_at`, n=268:

| Statistic | Value |
|---|---|
| min | **−4.5h** |
| p25 | 76.2h |
| median | **122.3h (5.1 days)** |
| p75 | 237.5h (9.9 days) |
| max | 355.7h |

| Bucket | count | share |
|---|---|---|
| 0–6h | 4 | 1.5% |
| 6–24h | 24 | 9.0% |
| 24–48h | 14 | 5.2% |
| 48–96h | 62 | 23.1% |
| 96h+ | **162** | **60.4%** |

**Interpretation:** spec §4.8 scores 6–24h as ideal, but only **10.5%** of picks
are logged that close. Since prices are captured at logging time, posting at
6–24h means advertising a price recorded a **median 5 days earlier** — on top of
F1. The timing table is defensible only once prices are re-verified near posting
time (spec §9.2's "recommended enhancement" becomes **mandatory**).

**Also:** 2 recommended rows were logged **after** kickoff (Liverpool v Chelsea
−5h, Sampdoria v Palermo −2h). They must never receive a "logged before kickoff"
proof claim.

---

### F7 🔴 P1 — claim mutability confirmed by code; direct history unavailable

**Code path** (`core/api_views.py:797-802`):

```python
if existing:
    for key, value in prediction_data.items():
        setattr(existing, key, value)     # overwrites odds, confidence,
    existing.is_recommended = True        # predicted_outcome, market_type
    existing.save()
```

Every re-run overwrites the claim fields. `prediction_logged_at` is
`auto_now_add` and never moves.

**Can past mutation be proven?** **No.** There is no `updated_at` column and no
history table, so prior overwrites are unrecoverable. This is itself a finding:
**we cannot currently prove any published claim was never altered** — which is
the exact property the transparency brand asserts.

**Does `/api/proof/` read mutable fields?** **Yes** — `proof_card_data` reads
`odds`, `confidence`, `predicted_outcome`, `market_type` live from
`PredictionLog`. A public proof URL can therefore change its displayed claim
while keeping its original timestamp.

**Cached assets:** the `opengraph-image` route re-renders from the same live
data, and social platforms cache the *image*. So a changed claim can also produce
a permanent mismatch between the cached social card and the live page.

**Timestamp integrity:** 2 of 315 recommended rows logged after kickoff; 0 results
logged before kickoff.

---

### F8 🟡 `accuracy_by_league` duplication — root cause found

**Symptom:** `/api/transparency/leagues/` returns **241** entries for **25**
distinct leagues (e.g. `Eredivisie` repeated identically 12+ times).

**Cause:** `accuracy_calculator.py:160`

```python
leagues = completed.values_list('league', flat=True).distinct()
```

`PredictionLog.Meta.ordering = ['-kickoff']` (`models.py:103`) injects `kickoff`
into the SELECT for ORDER BY, so `DISTINCT` de-duplicates on `(league, kickoff)`
pairs rather than `league`. Classic Django `distinct()` + default-`ordering`
trap. Fix would be `.order_by().values_list('league', flat=True).distinct()`.

**Blast radius:** the endpoint is **public** (`AllowAny`) and `total_leagues`
reports 241 instead of 25. **No frontend page renders it**, so no published page
currently shows wrong league statistics. Per instructions, **not fixed** during
diagnostics.

---

### F9 🟡 Website-vs-production alignment

| Claim (live `methodology` block) | Reality | Status |
|---|---|---|
| "Minimum 60% confidence AND positive Expected Value" | `over_under_2.5` ships at **0.55**; 54 published rows sit in 0.55–0.60 | ❌ **contradicted** |
| "Historical data never deleted or edited" | claim fields overwritten on every re-run (F7) | ❌ **contradicted** |
| "We show both wins and losses — complete transparency" | true, but ROI includes quarantined rows (F2) | ⚠️ misleading |
| "Real match results from SportMonks API" | true; grading verified correct | ✅ |
| "Third-party API — results cannot be manipulated" | results yes; **prices** are mis-captured (F1) | ⚠️ misleading |
| "All predictions logged BEFORE matches start" | 2 rows logged after kickoff (F6) | ⚠️ 99.4% true |
| Published ROI (+9.6% / +10.6%) | defensible figure is **−4.90%** | ❌ **contradicted** |
| "Top 10 best value bets updated daily" | top-10 slice confirmed in `route.ts:916` | ✅ |

No claims of user counts or guaranteed profit were found on the audited surfaces.
The odds band actually applied (`1.30–3.50` in `route.ts`) is not advertised
anywhere, so no contradiction — but it is also the band that admits the
contaminated prices.

---

## 3. Parameter simulation

Three configurations were run end-to-end against 268 resolved rows and 15 live
pending picks. **All results below are computed on contaminated data (F1) and are
therefore indicative only.**

| Config | MIN_CELL_N | MIN_SHRUNK_ROI | MIN_EDGE | odds band | Eligible cells | **Live gems** | Historical passes | ≈ posts/week |
|---|---|---|---|---|---|---|---|---|
| **Conservative** | 60 | 5.0% | 0.04 | 1.4–3.5 | **0** | **0** | 0 / 268 | 0.0 |
| **Balanced** | 40 | 2.0% | 0.02 | 1.4–3.5 | 1 | **3** | 36 / 268 | ~1.3 |
| **Permissive** | 25 | 1.0% | 0.01 | 1.3–5.0 | 1 | **3** | 38 / 268 | ~1.3 |

### Sensitivity

The outcome is governed almost entirely by **`MIN_CELL_N` against a single cell
of n = 54**:

| MIN_CELL_N | Eligible cells | Live gems | Note |
|---|---|---|---|
| ≤ 54 | 1 | 3 | the 0.55–0.60 cell qualifies |
| ≥ 55 | **0** | **0** | knife-edge — nothing qualifies |

Balanced and Permissive produce **identical** cell eligibility and live-gem
counts; loosening thresholds further adds nothing because no second cell is
anywhere near the bar (next best shrunk ROI is **−0.64%**). The selector is
therefore **not** sensitive to fine threshold tuning — it is sensitive to a
single binary question about one cell.

### Live gems under Balanced (what would have been posted)

| Pick | Stored odds | **True odds** | Verdict |
|---|---|---|---|
| Falkirk v St. Mirren, Over 2.5 | 2.05 | 1.78 | edge overstated |
| Celtic v Dundee, Over 2.5 | 3.00 | unverifiable | implausible price |
| SC Cambuur v Excelsior, Over 2.5 | 3.50 | **1.60** | **would publish a false price** |

Recomputing SC Cambuur at the true price: `p_cons = 0.5887 − 0.0304 − 0.01 =
0.548`; `edge = 0.548 × 1.60 − 1 = −12.3%` → it **fails** the gate. The gate
works; the inputs are wrong.

**Rejection reasons across all 15 live picks (Balanced):** 6 ×
`G3_below_market_threshold`, 4 × `G4_cell_n_too_small` (btts/1x2 have only n=4),
1 × `G4_no_cell_history`, 1 × `G7_edge_below_bar`, 1 ×
`G2_odds_out_of_band` (Shakhtar v Kudrivka, 1x2 @ **21.0** — a further price
anomaly), 3 × PASS.

---

## 4. P1 — claim-immutability architecture

### Recommendation: **immutable `PublishedClaim` snapshot** (the founder's preferred direction, and the correct one)

| Approach | Integrity | Migration risk | Proof-page compat | CLV-ready | Auditability | Effort |
|---|---|---|---|---|---|---|
| **A** — first-write-wins on `PredictionLog` | Medium — freezes the live view too; loses genuine refinements | Low (no schema change) | High | Poor | Low — no publication record | Low |
| **B** — `PublishedClaim` snapshot model | **High** — live and published views cleanly separated | Medium (one additive table) | High (proof reads snapshot) | **Good** | **High** — one immutable row per claim | Medium |
| C — full audit/history table | High | High | Medium | Good | Very high | High |

**Choose B.** A conflates two genuinely different objects: *the model's current
best estimate* and *the public promise we made*. The engine should stay free to
refine its live view; what must never change is what we published.

**Proposed model** (additive only — no change to `PredictionLog`):

```
PublishedClaim
  claim_id            UUID, primary key
  prediction          FK -> PredictionLog  (source reference)
  fixture_id, home_team, away_team, league, league_id
  kickoff, kickoff_tz
  market_type, predicted_outcome
  confidence                      # value at publication
  odds, odds_bookmaker            # price at publication
  odds_market_id                  # NEW: which SportMonks market the price came from
  odds_captured_at                # real capture time, not a proxy
  prediction_generated_at         # copy of prediction_logged_at
  published_at                    # when the claim became public
  model_version / run_id
  claim_hash                      # sha256 over the claim fields
  -- results live elsewhere and never rewrite the above
```

**Rules.** Insert-only; no `UPDATE` path in application code. `/api/proof/<id>/`
resolves the `PublishedClaim` first and falls back to `PredictionLog` only for
unpublished picks. Result/settlement data is read from `PredictionLog` and
rendered in a separate region of the card. `claim_hash` makes tampering
externally checkable and is the natural anchor if we ever publish a verification
feed.

**Migration plan (no backfill of history).**
1. Add the table (additive; zero risk to existing reads).
2. Write a snapshot at selection time in `/gems`; nothing else writes it.
3. Point the proof endpoint at the snapshot when one exists.
4. **Do not** retro-create claims for the 315 existing rows — we cannot prove
   what they contained at publication. Historical cards should be labelled as
   pre-dating the immutability guarantee rather than given a false one.

`odds_market_id` is included specifically so F1 can never recur silently.

---

## 5. Recommended parameter set

**Status: PROVISIONAL — must be re-derived after F1 is fixed and odds backfilled.**

```python
# ── Confirmed by diagnostics ──────────────────────────────────────────────
CONF_SCALE            = "0-1 uniform"   # D1: 0 rows > 1.0; keep the defensive
                                        # normaliser, but it is not a live risk
CONF_BUCKETS          = [(0.55,0.60), (0.60,0.65), (0.65,1.00)]  # D2c
FALLBACK_MARGIN       = 0.05            # measured overall margin is 0.0296
MIN_MARGIN_SAMPLE     = 30              # btts/1x2 have n=4 -> fallback applies
UNIVERSE              = "B"             # F2: must exclude is_audit_excluded
                                        #     and match_status='archived'

# ── Provisional, pending re-derivation on clean odds ──────────────────────
MIN_CELL_N            = 40              # knife-edge at 54; revisit post-fix
MIN_SHRUNK_ROI        = 2.0             # must stay > 0 (shrinkage no-op proof)
PRIOR_ROI             = 0.0
PRIOR_STRENGTH_K      = 50
MIN_DEFENSIBLE_EDGE   = 0.02
MIN_ODDS, MAX_ODDS    = 1.40, 3.50      # NOTE: 3.50 is exactly the contaminated
                                        # tail's ceiling — tighten to ~2.60 until
                                        # F1 is fixed and re-measured
MIN_TIER_N            = 15
TIER_VETO_ROI         = -3.0
RECENT_WINDOW_N       = 20              # 50 exceeds most cells; 20 is feasible
MIN_RECENT_N          = 20
RECENT_VETO_ROI       = -5.0
W_EDGE, W_EVIDENCE, W_TIMING, W_OBSCURITY = 0.40, 0.30, 0.20, 0.10
```

**Changed from the spec by evidence:** `CONF_BUCKETS` (0.70+ has n=4 → merged);
`RECENT_WINDOW_N` 50 → 20 (no cell has 50 recent rows to spare);
`MIN_MARGIN_SAMPLE` confirmed necessary (btts/1x2 at n=4);
`MAX_ODDS` flagged for tightening.

---

## 6. Uncertainty and limitations

- **All ROI-derived parameters are computed on contaminated prices (F1)** and
  will shift — likely downward — once fixed.
- **Historical odds cannot be reconstructed.** SportMonks odds endpoints are
  point-in-time; pre-match prices for settled fixtures are not reliably
  retrievable. A backfill may be **impossible**, in which case the honest options
  are to (a) restate the record as unverifiable before a cut-off date, or
  (b) restart the published record from the fix date.
- **Past claim mutation is unprovable** (no `updated_at`, no history).
- `market_id` semantics (7 vs 37/53/80/86/105/107) were inferred from payload
  shape; the authoritative market names were not fetched. `market_id 7` is
  confirmed as the standard goals Over/Under by its `total=2.5` + Over/Under
  label pairing and plausible prices.
- Bootstrap CIs assume i.i.d. bets; correlated fixtures (same league/round) would
  widen them.
- League tiers are a **provisional** name-based map needing founder review.
- Only 4 live fixtures were price-verified against SportMonks (rate-limit
  prudence); the pattern was consistent across all 4.

---

## 7. Decision

### 🔴 BLOCKED — pending fixes

**Not "implement but expect an empty state."** The Balanced config *would* return
3 live gems — but one of them (SC Cambuur) would publish **Over 2.5 @ 3.50** when
the real price is **1.60**. Shipping that is worse than shipping nothing: it is
precisely the fabricated-screenshot behaviour the brand exists to oppose.

### Required implementation order

| # | Action | Blocks |
|---|---|---|
| **1** | **Fix odds capture (F1).** Match on `market_id` + `total == 2.5` + exact `Over`/`Under` label; select deterministically (e.g. median across bookmakers, or a named book); record `odds_market_id`. Add a regression test using the real 491-entry payload. | everything |
| **2** | **Decide the historical record's fate.** Backfill if feasible; otherwise restate publicly. Until then the published ROI is not defensible. | all publishing |
| **3** | **Exclude `is_audit_excluded` + archived from `AccuracyCalculator` (F2).** One-line universe fix; corrects dashboard **and** every proof card. | all publishing |
| **4** | **Implement `PublishedClaim` (F7 / P1).** | public posting |
| **5** | Re-run D2–D4 on clean data; finalise constants. | selector |
| **6** | Implement the selector. | — |
| **7** | Fix `accuracy_by_league` (F8) and reconcile the methodology text (F9). | promotion |

### Can BetGlitch begin public posting after P1 alone?

**No.** P1 (immutability) guarantees we won't *change* a claim — but F1 means the
claim would be **wrong at the moment it is made**, and F2 means the record shown
beside it is **inflated**. Fixing only P1 would faithfully preserve a false
statement.

Minimum bar for public posting: **items 1, 2, 3 and 4.**

### One thing that is genuinely good news

Every gate in the design **worked correctly** on the data it was given. It
rejected 12 of 15 live picks for sound, individually-explained reasons, and
recomputing SC Cambuur at its true price correctly flips it to a rejection. The
architecture is sound; the inputs are not. The diagnostics did exactly what they
were commissioned to do — they caught this **before** anything was published.
