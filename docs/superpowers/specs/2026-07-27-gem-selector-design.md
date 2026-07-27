# Hidden-Gem Selector — Design Spec (v2)

**Date:** 2026-07-27
**Status:** APPROVE WITH DATA-DEPENDENT PARAMETERS — blocked on prerequisites (§14)
**Author:** Andrei + Claude
**Supersedes:** v1 of this file (commit `158f479`)
**Parent context:** Second build of the growth thread, after the proof-card
generator (`2026-07-25-proof-card-generator-design.md`).

---

## 0. Change log vs v1

| # | Change | Driver |
|---|---|---|
| C1 | **`defensible_edge` formula replaced.** v1's shrink-toward-market provably reduces to `SHRINK × raw_EV` — a no-op on sign. Replaced with an empirical over-confidence haircut in probability space. | Review §1, verified §13.1 |
| C2 | **Cell gate now uses shrunk ROI against a *positive* threshold.** A zero prior with a `> 0` gate is also a no-op; shrinkage only bites against a positive bar. | Review §2, corrected |
| C3 | **Evidence strength added to ranking (30%); obscurity cut 35% → 10%.** | Review §3 |
| C4 | **League-tier context check added — as a veto on known-bad, not a requirement of proven-good.** The strict reading is infeasible at n=276. | Review §4, modified |
| C5 | **Timing window inverted** to favour 6–24h before kickoff. | Review §5, accepted and strengthened |
| C6 | **Odds provenance + immutability**, promoted to a blocking prerequisite: the claim fields are currently overwritten on every re-run. | Review §6, escalated |
| C7 | **CLV forward-compatibility**: metrics namespaced and kept separate. | Review §7 |
| C8 | **Confidence semantics** must be established before launch; `confidence` is a provider-derived score, not a calibrated probability. | Review §8 |
| C9 | **Obscurity mapping** by normalized exact name + explicit `UNKNOWN` (obscurity 0.5, never 1.0). `league_id` is unusable (always null). | Review §9, modified |
| C10 | **Buckets made coarser, not finer** — production data shows the high buckets are nearly empty. | Review §10, direction reversed |
| C11 | **Recent-deterioration check added**, on last-N-resolved rather than calendar windows. | Review §11 |
| C12 | **Response split** into `recommended_for_posting` / `alternatives` / `on_deck`. | Review §12 |
| C13 | **Card content hierarchy + four visual states** specified; implementation deferred to a follow-up task. | Review §13 |
| C14 | **Caption templates** per platform, softened to signal-not-fact. | Review §14 |
| C15 | **Alignment audit** added as a launch gate — a live contradiction already exists. | Review §15 |

## 1. Purpose & positioning (unchanged from v1)

Answer **"which upcoming pick should I post?"** — or **"none this week."**

**Catchy = hidden gem**, not famous teams. Marquee fixtures sit in the sharpest
markets where our edge barely survives; our edge lives in obscure leagues. The
target audience is **value bettors**, who care that the number is good.

**Maximum defensibility**, expressed as a **gate, not a weight**. We have no
credibility reserve to absorb a blowup. The goal is not to maximise posts — it is
to select the few picks we can defend publicly.

**Non-goal:** cards and captions present transparent data, never a profit promise.

## 2. Configuration — all tunable constants in one place

```python
# ── Confidence ────────────────────────────────────────────────────────────
CONF_SCALE_THRESHOLD   = 1.0    # values > 1.0 are treated as 0–100 and divided
MIN_CONF_FLOOR         = 0.55   # absolute floor; per-market gate still applies

# ── Confidence buckets (COARSE — production data is concentrated) ─────────
# 60–65% holds 166/276 rows; >70% holds 4. Finer buckets create unusable cells.
CONF_BUCKETS = [(0.55, 0.60), (0.60, 0.65), (0.65, 1.00)]

# ── Price band ────────────────────────────────────────────────────────────
MIN_ODDS               = 1.40   # below: edge too thin to survive any error
MAX_ODDS               = 3.50   # above: our resolved sample is negligible

# ── Conservative probability (§4.2) ───────────────────────────────────────
SAFETY_EPS             = 0.01   # extra haircut beyond measured over-confidence
MIN_MARGIN_SAMPLE      = 30     # min resolved rows to estimate a market's margin
FALLBACK_MARGIN        = 0.05   # used when a market lacks MIN_MARGIN_SAMPLE
MIN_DEFENSIBLE_EDGE    = 0.02   # required post-haircut edge (2%)

# ── Historical evidence (§4.3) ────────────────────────────────────────────
PRIOR_ROI              = 0.0    # zero prior: most conservative (see §4.3)
PRIOR_STRENGTH_K       = 50     # pseudo-observations pulling toward PRIOR_ROI
MIN_CELL_N             = 40     # DATA-DEPENDENT — confirm via D3 before locking
MIN_SHRUNK_ROI         = 2.0    # percent; MUST be > 0 or shrinkage is a no-op

# ── League-tier context (§4.4) ────────────────────────────────────────────
MIN_TIER_N             = 15     # below this, tier evidence is "insufficient"
TIER_VETO_ROI          = -3.0   # percent; tier with enough n and worse ROI vetoes

# ── Recent deterioration (§4.5) ───────────────────────────────────────────
RECENT_WINDOW_N        = 50     # last N *resolved* rows in the cell (not calendar)
MIN_RECENT_N           = 20     # below this, recency is "insufficient", not a veto
RECENT_VETO_ROI        = -5.0   # percent

# ── Evidence strength (§4.6) ──────────────────────────────────────────────
EVIDENCE_SAT_N         = 200    # sample size at which the size component saturates
EVIDENCE_ROI_FULL      = 10.0   # shrunk ROI (%) scoring full marks

# ── Ranking weights (must sum to 1.0) ─────────────────────────────────────
W_EDGE                 = 0.40
W_EVIDENCE             = 0.30
W_TIMING               = 0.20
W_OBSCURITY            = 0.10
EDGE_NORM_FULL         = 0.15   # defensible edge scoring full marks

# ── Output ────────────────────────────────────────────────────────────────
MAX_INTERNAL_CANDIDATES = 5     # internal shortlist; only ONE is recommended
STALE_ODDS_WARN_HOURS   = 48    # older than this → display a staleness warning
```

Every constant is a module-level named value with a comment. None may be
inlined at a call site.

## 3. Confidence — semantics and normalisation (BLOCKING)

### 3.1 What `confidence` actually is

`PredictionLog.confidence` originates from SportMonks provider probabilities
(e.g. BTTS probability `0.6426`), passed through the engine's market selection.
It is **not an empirically calibrated probability**.

**Consequence:** it must never be presented publicly as an exact probability
without qualification. Cards and captions say **"model probability"** and always
show the **bookmaker implied probability** next to it, so the reader sees the
comparison rather than a bare claim.

### 3.2 Normalisation (single helper, used everywhere)

```python
def normalize_confidence(raw: float | None) -> float | None:
    if raw is None:
        return None
    p = raw / 100.0 if raw > CONF_SCALE_THRESHOLD else raw
    if not (0.0 < p <= 1.0):
        log_anomaly(raw)          # never silently coerce
        return None
    return p
```

`raw == 1.0` is treated as 100%, not 1% (a 1% pick is implausible and would
never have been recommended). This is documented ambiguity, not a silent choice.

**Risk:** bucketing on the wrong scale silently empties the gate — every pick
falls outside every bucket and the selector returns "no gems" forever, looking
like correct conservative behaviour. Diagnostic **D1** (§14) must confirm the
real distribution, and a unit test asserts both scales bucket identically.

## 4. Selection logic

### 4.1 Stage 1 — Defensibility gate (pass/fail, no trade-offs)

A pick is eligible only if **all** hold. Each rule returns a machine-readable
reason on failure, surfaced in the API.

| # | Rule | Constant |
|---|---|---|
| G1 | Live published claim: `is_recommended=True`, `was_correct IS NULL`, `kickoff > now`, `is_audit_excluded=False` | — |
| G2 | Priceable: `odds` not null and `MIN_ODDS <= odds <= MAX_ODDS` | §2 |
| G3 | Confidence normalises successfully and clears the per-market threshold via the existing `_confidence_filter()` | §3.2 |
| G4 | **Broad evidence:** cell `n >= MIN_CELL_N` and `shrunk_roi >= MIN_SHRUNK_ROI` | §4.3 |
| G5 | **League-tier context:** not vetoed | §4.4 |
| G6 | **Recent performance:** not vetoed | §4.5 |
| G7 | **Conservative edge:** `defensible_edge >= MIN_DEFENSIBLE_EDGE` | §4.2 |
| G8 | **Claim integrity:** the pick's claim fields are locked (§9). Unlocked ⇒ ineligible. | §9 |

If nothing passes, return **no gems** — a valid, intended output (§7).

### 4.2 Conservative probability and defensible edge (replaces v1's formula)

**Why v1 was wrong.** With `m = 1/odds`:

```
edge = odds·[m + S·(p − m)] − 1 = S·(p·odds − 1) = S · raw_EV
```

Verified over 100k random cases: identical to 3.6e-15, with **zero** sign
disagreements. So v1's rule "positive shrunk edge" was exactly "positive raw EV",
and its stated rationale (an edge can evaporate under shrinkage) was false.
Multiplicative shrinkage toward the market **cannot** correct a *bias*.

**Replacement — an empirical over-confidence haircut in probability space:**

```python
# Measured per market from resolved history — a LIVE query, never a constant.
margin(market) = max(0, mean_normalized_confidence(resolved rows)
                        − win_rate(resolved rows))
# If the market has < MIN_MARGIN_SAMPLE resolved rows, use FALLBACK_MARGIN.

p_cons          = clamp(p_model − margin(market) − SAFETY_EPS, 0.0, 1.0)
defensible_edge = p_cons · odds − 1
```

**What this means:** *"Even after docking the model by the amount it has
historically been over-confident in this market, plus a safety epsilon, a positive
edge remains at the recorded price."*

**What it does NOT mean:** it is not a calibration, not a calibrated probability,
and not a claim the true probability equals `p_cons`. The calibration study
(`2026-07-22`, verdict DO_NOT_APPLY) found miscalibration is **non-monotone**, so
no global mapping is justified. This is a deliberately blunt conservative haircut.

**It can genuinely flip sign.** Worked example — Cardiff (btts, `p=0.643`,
`odds=1.8`): with `margin=0.06` → `p_cons=0.573`, edge `+3.1%` (passes). With
`margin=0.10` → `p_cons=0.533`, edge `−4.1%` (fails). Unlike v1, the haircut
changes outcomes.

**Deliberately not adopted:** review §1 Option A (a bare `MIN_DEFENSIBLE_EDGE` on
the v1 formula). It is only a rescaled raw-EV bar and would have to be documented
as such; the haircut above is grounded in measured behaviour and self-updates.

### 4.3 Historical evidence — shrunk cell ROI

```python
shrunk_roi = (n / (n + PRIOR_STRENGTH_K)) · cell_roi
           + (PRIOR_STRENGTH_K / (n + PRIOR_STRENGTH_K)) · PRIOR_ROI

# G4:  n >= MIN_CELL_N  AND  shrunk_roi >= MIN_SHRUNK_ROI
```

**`MIN_SHRUNK_ROI` must stay > 0.** With `PRIOR_ROI = 0`, shrinkage preserves
sign in 100% of cases (verified), so a `> 0` gate would be a no-op. Against a
positive bar it bites correctly — smaller samples must show more:

| n | raw ROI needed to clear `shrunk_roi ≥ 2%` |
|---|---|
| 20 | 7.00% |
| 40 | 4.50% |
| 100 | 3.00% |
| 300 | 2.33% |

**Prior justification — `PRIOR_ROI = 0`, chosen over the alternatives:**
- *Overall recommended ROI (+10.6%)* would pull thin cells **upward**, letting a
  weak cell borrow credibility from the portfolio. That is the wrong direction
  for a defensibility gate.
- *Market-level ROI* has the same defect within a market, and risks circularity
  (the market ROI is partly composed of the cell being judged).
- *Zero* assumes no edge until evidence overcomes it. It is the only prior that
  makes the gate strictly harder, which is what "maximum defensibility" means.

**Cell ROI uses the same flat-stake convention as
`AccuracyCalculator.get_roi_simulation()`**, so the gate and the public record
can never disagree.

### 4.4 League-tier context — a veto, not a requirement

**The concern is valid** (review §4): a cell can be profitable because it works in
mainstream leagues while the gem we post is Tier C. That would contradict the
public story that we find edge in overlooked competitions.

**The strict reading is infeasible.** Total resolved n = 276. Splitting
`market_type × bucket` already yields ~12 cells; adding `league_tier` yields ~36,
averaging <8 rows each. Requiring proven-positive tier evidence would return
nothing permanently — which is indistinguishable from a broken tool.

**Adopted rule — asymmetric:**

```
tier_cell = (market_type, conf_bucket, league_tier)

VETO   if tier_n >= MIN_TIER_N and tier_roi < TIER_VETO_ROI
PASS   otherwise
```

- With enough tier evidence that is materially negative → **blocked**.
- With insufficient tier evidence → **passes**, but the response carries
  `tier_evidence: "insufficient"` and the founder sees it before posting.

This blocks the failure mode the review identified (posting into a tier we know
performs badly) without demanding a sample we do not have. Revisit once volume
supports the symmetric rule.

### 4.5 Recent deterioration

Uses the **last `RECENT_WINDOW_N` resolved rows in the cell**, not a calendar
window — fixture volume swings seasonally (the current pre-season lull would make
any calendar window meaningless), and last-N is robust to that.

```
VETO   if recent_n >= MIN_RECENT_N and recent_roi < RECENT_VETO_ROI
PASS   otherwise (including when recent_n is too small to conclude)
```

Deliberately tolerant of a handful of recent losses; it fires only on material
deterioration with adequate sample. Only one window is used — no window sweep, to
avoid selecting a threshold that flatters the current data.

### 4.6 Evidence strength (new ranking component)

All components bounded to `[0, 1]`:

```python
ev_sample    = min(1.0, log(1 + n) / log(1 + EVIDENCE_SAT_N))
ev_roi       = clamp(shrunk_roi / EVIDENCE_ROI_FULL, 0.0, 1.0)
ev_stability = 1.0 if recent_roi >= shrunk_roi            # holding up or improving
               else 0.5 if recent_n < MIN_RECENT_N        # unknown, not penalised hard
               else clamp(recent_roi / shrunk_roi, 0.0, 1.0)

evidence_strength = 0.40·ev_sample + 0.40·ev_roi + 0.20·ev_stability
```

`ev_sample` is logarithmic so that going from n=40 to n=80 matters much more than
n=300 to n=340 — diminishing returns, matching how evidence actually accrues.

### 4.7 Obscurity (revised classification)

`league_id` is **hardcoded `None`** at write time (`api_views.py:771`), so the
review's preferred exact-id mapping is unavailable. Substring matching is rejected
as unsafe — `"Liga"` matches *La Liga*, *Liga MX*, *Primeira Liga* and
*Superliga*, silently misclassifying a Danish fixture as mainstream.

**Adopted:** normalise (casefold, strip punctuation/diacritics, collapse
whitespace) then **exact match** against a centralised map.

| Tier | Score | Members |
|---|---|---|
| A — mainstream | 0.0 | Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, World Cup, European Championship |
| B — well-known second tier | 0.5 | Championship, Eredivisie, Primeira Liga, Scottish Premiership, MLS, Liga MX |
| C — genuine gem | 1.0 | Explicitly mapped members only |
| **UNKNOWN** | **0.5** | Unmapped competitions |

**`UNKNOWN` never receives maximum obscurity** and emits a warning listing the
unmapped name, so the map is maintained by observation rather than assumption.
`UNKNOWN` forms its own league tier for §4.4.

*Optional follow-up (not in scope):* populate `league_id` at write time so future
mapping can key on a stable id.

### 4.8 Timing (revised — v1 was backwards)

**v1 favoured 2–7 days out, reasoning that the audience needs time to return.
That reasoning was wrong**, for a reason the review implies and that the shipped
card makes decisive:

> The card renders `prediction_logged_at`, which is immutable and set when the
> **model** logged the pick — not when we post. Cardiff was logged 14 days out;
> posting it 12 hours before kickoff still renders *"14d 16h before kickoff."*

So **posting later costs nothing in proof strength** while gaining: live team
news, a price closer to what a reader can still get, higher fixture attention,
and a **shorter wait to the result card** — which tightens the return loop rather
than loosening it. A 7-day gap invites the audience to forget.

| Hours to kickoff | Score | Rationale |
|---|---|---|
| `< 2` | 0.3 | too late to be seen and acted on |
| `2–6` | 0.7 | good attention, tight window |
| `6–24` | **1.0** | ideal: team news known, price live, result soon |
| `24–48` | 0.8 | still strong |
| `48–96` | 0.5 | attention fading, price drift risk |
| `> 96` | 0.2 | too far out to hold attention |

Weights and boundaries are constants so the window can later be **learned** from
engagement and odds-movement data rather than argued.

**Interaction with stale odds (§9.2):** posting nearer kickoff makes the recorded
price older relative to the market. This is handled by honest presentation, not by
suppression — see §9.2.

### 4.9 Final gem score

```
gem_score = W_EDGE      · edge_norm            # 0.40
          + W_EVIDENCE  · evidence_strength    # 0.30
          + W_TIMING    · timing               # 0.20
          + W_OBSCURITY · obscurity            # 0.10

edge_norm = clamp(defensible_edge / EDGE_NORM_FULL, 0.0, 1.0)
```

Statistical quality carries **70%** (edge + evidence); presentation and logistics
carry 30%. Obscurity at 0.10 can break ties and add interest but **cannot let a
materially weaker candidate outrank a stronger one** — the review's explicit
requirement. A unit test asserts exactly this.

## 5. Anti-calcification (unchanged requirement, restated)

- **The selector filters what we PUBLISH, never what we PREDICT.** The engine
  keeps recommending across every slice; `PredictionLog` keeps logging all of
  them. There is **no feedback loop into the model** and no slice is starved.
- **Every historical quantity is a live query** — cell ROI, over-confidence
  margin, tier ROI, recent ROI. A slice that becomes profitable **graduates
  automatically**; a decaying slice **drops out automatically**.
- **Hardcoding eligible cells is forbidden.** This is the failure mode the
  section exists to prevent, and it has a dedicated regression test (§12).

## 6. On deck (discovery)

Cells that do not yet qualify, reported so the founder can watch edge forming:

- `ROI > 0` and `MIN_TIER_N <= n < MIN_CELL_N` → `promising_low_n`
- `n >= MIN_CELL_N` and `0 < shrunk_roi < MIN_SHRUNK_ROI` → `below_roi_bar`
- vetoed by §4.4 or §4.5 → `tier_veto` / `recent_veto`

On-deck cells are **reported only** and never make a pick postable.

## 7. The empty state is a feature

No qualifying pick ⇒ empty `recommended_for_posting`, and the page reads
**"No gem worth posting right now."** Tools that always produce an answer pressure
the user into posting weak material.

**Expected at launch.** With n=276 total and `MIN_CELL_N = 40`, only the largest
cells can qualify. Diagnostic **D3** must report how many cells clear the bar
*before* implementation locks the constants, so an empty result is understood as
correct rather than broken.

## 8. Metric separation (CLV forward-compatibility)

Four distinct metrics, **never presented as interchangeable**, each namespaced
separately in responses and on the proof page:

| Metric | Meaning | Available now |
|---|---|---|
| `accuracy` | share of picks that won | yes |
| `realized_roi` | flat-stake profit on settled picks | yes |
| `expected_value` | model's pre-match estimate | yes (uncalibrated, §3.1) |
| `clv` | recorded price vs closing price | **no** — needs closing odds |

CLV is the metric that distinguishes genuine mispricing detection from luck (a
good bet can lose; a bad bet can win). It is **not required for MVP**, but the
architecture must not obstruct it: the response schema reserves a `clv` block,
and §9 records the price and its timestamp so closing-line comparison becomes a
pure addition. Capturing closing odds requires a new field and a scheduled job —
a separate spec.

## 9. Odds provenance and claim immutability (BLOCKING)

### 9.1 The defect

`core/api_views.py:797–802` overwrites **every** field on an existing row on each
re-run, including `odds`, `confidence`, `predicted_outcome` and `market_type`,
while `prediction_logged_at` (`auto_now_add`) never changes. A published card can
therefore display a **different pick or price than the one posted**, while still
claiming the original timestamp.

For a brand whose entire thesis is "we never edit history," this is
disqualifying. **No public posting may occur until it is fixed.**

### 9.2 Requirement

The **claim fields** — `predicted_outcome`, `market_type`, `odds`, `bookmaker`,
`confidence` — must be **immutable once the pick is eligible for publication**.

Two viable approaches; the implementation plan must choose one explicitly:

- **A — first-write-wins on claim fields.** Re-runs may refresh non-claim fields
  only. Simplest; changes engine write behaviour. Needs a decision on whether
  re-runs are *intended* to refine picks.
- **B — publication snapshot.** A small immutable record captures the claim at
  selection time; the card renders the snapshot. Leaves engine behaviour intact;
  requires a migration.

**Provenance inventory** (what exists vs. what is needed):

| Field | Status |
|---|---|
| `odds`, `bookmaker`, `market_type`, `predicted_outcome`, `confidence` | exist — but **mutable** (§9.1) |
| `kickoff`, `prediction_logged_at` | exist, immutable |
| odds capture time | **proxy** — equals `prediction_logged_at` (same pipeline run); must be documented as a proxy, not asserted as measured |
| model run id / version | partial — `ensemble_strategy`, `model_count`, `consensus`, `variance`; no run id |
| closing odds | absent (§8) |
| publication time | absent; not required (posting is manual) |

**Stale price handling.** Because posting now targets 6–24h before kickoff (§4.8)
while the price was recorded at prediction time, the recorded price may be
days old. This is handled by **honest presentation, never suppression**:

- The card shows the recorded price **with its timestamp** — proving foresight,
  not offering a bet slip.
- `odds_age_hours` is returned and displayed; beyond `STALE_ODDS_WARN_HOURS` the
  panel warns the founder.
- The caption directs readers to check the current price.
- **Recommended enhancement (not MVP):** fetch live odds for the ≤5 shortlisted
  fixtures at selection time and display recorded vs current side by side. This
  also lays the groundwork for CLV (§8). The original value is **never**
  overwritten.

## 10. Architecture

### 10.1 Backend

`GET /api/gems/` — staff-only (`IsAdminUser`, matching existing
`permission_classes` usage in `core/`).

```json
{
  "generated_at": "2026-07-27T15:00:00Z",
  "recommended_for_posting": {
    "fixture_id": 19726943,
    "home_team": "Cardiff City", "away_team": "Swindon Town",
    "league": "Carabao Cup", "league_tier": "C",
    "kickoff": "2026-08-08T17:00:00Z", "hours_to_kickoff": 14.2,
    "market_type": "btts", "predicted_outcome": "BTTS Yes",
    "gem_score": 0.68,
    "probability": {
      "model": 0.643,
      "bookmaker_implied": 0.556,
      "conservative": 0.573,
      "note": "model probability is provider-derived and not calibrated"
    },
    "edge": { "defensible_edge": 0.031, "edge_norm": 0.21,
              "margin_applied": 0.06, "margin_source": "measured:btts" },
    "evidence": {
      "cell_key": "btts@0.60-0.65", "n": 96, "cell_roi": 6.2,
      "shrunk_roi": 4.07, "recent_n": 50, "recent_roi": 5.1,
      "tier_evidence": "insufficient", "tier_n": 11,
      "evidence_strength": 0.55
    },
    "components": { "edge_norm": 0.21, "evidence_strength": 0.55,
                    "timing": 1.0, "obscurity": 1.0 },
    "provenance": {
      "odds": 1.80, "bookmaker": "bet365",
      "odds_captured_at": "2026-07-25T00:03:31Z",
      "odds_captured_at_is_proxy": true,
      "odds_age_hours": 63.0, "stale_price_warning": true,
      "prediction_logged_at": "2026-07-25T00:03:31Z",
      "claim_locked": true,
      "ensemble_strategy": "consensus_ensemble", "model_count": 3
    },
    "clv": null,
    "proof_url": "https://www.betglitch.com/proof/19726943",
    "captions": { "x": "…", "reddit": "…", "telegram": "…" }
  },
  "alternatives": [ { "fixture_id": 19714004, "gem_score": 0.51, "…": "…" } ],
  "rejected": [
    { "fixture_id": 19726975, "reasons": ["G3_below_market_threshold"],
      "detail": "1x2 confidence 0.554 < 0.60" }
  ],
  "on_deck": [
    { "cell_key": "double_chance@0.65-1.00", "n": 18, "roi_percent": 4.1,
      "reason": "promising_low_n" }
  ],
  "diagnostics": { "unmapped_leagues": ["Carabao Cup"], "total_candidates": 4 }
}
```

`rejected` with machine-readable `reasons` makes every gate decision auditable —
and makes an empty result explainable rather than mysterious.

### 10.2 Frontend

`/gems` — `noindex`, gated via the existing `AuthContext`, not in public nav.

Layout follows the response: **one** recommended pick shown prominently with its
full evidence breakdown and copy controls; `alternatives` collapsed below;
`rejected` and `on_deck` in a diagnostics section. Empty state per §7.

**The interface must not encourage posting five picks because five exist** — only
`recommended_for_posting` gets primary copy controls.

## 11. Proof card and captions

### 11.1 Card content hierarchy (implementation deferred to a follow-up task)

The card image attracts attention; the **proof page** carries the audit trail.

**On the image — primary:** fixture, league, market + selection, recorded odds,
kickoff.
**On the image — core credibility:** model probability *vs* bookmaker implied
probability, conservative edge, "logged before kickoff" timestamp, "result
verifies automatically after full-time."
**Proof page only — secondary:** cell sample size and shrunk ROI, tier evidence,
bookmaker and capture time, ensemble info, full methodology link, current vs
recorded price.

Do not put every metric on the image.

### 11.2 Four visual states

| State | Trigger | Treatment |
|---|---|---|
| `PICK — PENDING` | `was_correct IS NULL`, kickoff future | blue "LOGGED" pill (shipped) |
| `RESULT — WON` | `was_correct = True` | green "WON" pill (shipped) |
| `RESULT — LOST` | `was_correct = False` | red "LOST" pill — **identical layout, prominence and quality to WON** (shipped) |
| `VOID / CANCELLED` | `match_status` in {`CANC`, `POSTP`, `ABAN`} | **new** — neutral grey "VOID — no result", excluded from record |

The VOID state is a genuine gap: `match_status` already stores `'CANC'`, but the
shipped card treats any unresolved row as pending, so a cancelled fixture would
display "awaiting result" indefinitely.

### 11.3 Caption templates

**Banned vocabulary:** guaranteed, lock, banker, sure bet, easy money, "the
market is wrong" as fact, any profit promise, win-only framing.

Language presents a **model signal**, not an established fact.

**X:**
> Hidden fixture, measurable signal.
> {home} v {away} — {selection} @ {odds}
> Model: {model_p}% · Bookmaker implies: {implied_p}%
> Logged before kickoff, verified after full-time — win or lose.
> {proof_url}

**Reddit** (context-first, link last):
> {league} — {home} v {away}. Our model estimates {model_p}% for {selection};
> the price implies {implied_p}%. Recorded at {odds} on {captured_at} (check the
> current price — it moves). The pick was logged before kickoff and the result
> verifies automatically at full-time, win or lose. Full record, losses
> included: {proof_url}

**Telegram:**
> ⚡ {home} v {away} — {selection} @ {odds}
> Model {model_p}% vs implied {implied_p}%.
> Logged before kickoff. Auto-verified at full-time, win or lose.
> {proof_url}

**Result follow-up — WON:**
> Result: {home} {hs}–{as} {away}. {selection} — won.
> Posted before kickoff at {odds}. Season: {W}W–{L}L · {roi}% ROI.
> {proof_url}

**Result follow-up — LOST** (same prominence, no excuses):
> Result: {home} {hs}–{as} {away}. {selection} — lost.
> Posted before kickoff at {odds}. We post these too.
> Season: {W}W–{L}L · {roi}% ROI. {proof_url}

## 12. Testing

**Gate rules, each isolated:** resolved pick; past kickoff; null odds; odds below
`MIN_ODDS`; odds above `MAX_ODDS`; `is_audit_excluded`; below per-market
threshold; cell `n < MIN_CELL_N`; `shrunk_roi < MIN_SHRUNK_ROI`; tier veto fires;
tier "insufficient" does **not** veto; recent veto fires; recent insufficient does
**not** veto; `defensible_edge < MIN_DEFENSIBLE_EDGE`; unlocked claim rejected.

**Formula correctness:**
- `defensible_edge` **flips sign** when the measured margin grows — the explicit
  regression test for the v1 defect (a pick passing at `margin=0.06` must fail at
  `margin=0.10`).
- `shrunk_roi` with a **positive** bar rejects a high-ROI/low-n cell that a
  `> 0` bar would have accepted — the regression test for the review §2 no-op.
- `normalize_confidence` buckets 0–1 and 0–100 rows identically; out-of-range
  values are rejected and logged, never coerced.
- Evidence and timing components are bounded to `[0, 1]` across extreme inputs.

**Ranking:**
- Deterministic order for synthetic candidates.
- **Obscurity cannot flip a materially stronger candidate below a weaker one**
  (Tier A with strong edge+evidence outranks Tier C with weak edge+evidence).
- Weights sum to 1.0.

**Anti-calcification:** adding resolved rows that flip a cell above the bar makes
a previously-gated pick eligible **with no code change** (§5).

**League mapping:** normalized exact match; `"Superliga"` is **not** classified
mainstream by substring collision; unmapped league yields `UNKNOWN` with
obscurity 0.5 and a warning.

**Output shape:** at most one `recommended_for_posting`; `alternatives` capped at
`MAX_INTERNAL_CANDIDATES − 1`; every rejected candidate carries a reason; empty
state returns HTTP 200 with nulls, not 404.

**Access control:** anonymous rejected; authenticated non-staff rejected; staff
succeeds.

Existing suite stays green. No frontend test framework exists; `/gems` and card
states are verified visually.

## 13. Production diagnostics — run BEFORE locking parameters

| # | Diagnostic | Blocks |
|---|---|---|
| **D1** | Distribution of raw `confidence` — min/max/mean, and count of rows `> 1.0` vs `<= 1.0`, per market. Confirms the storage scale. | §3.2 |
| **D2** | Per-market measured over-confidence: `mean(normalized confidence) − win_rate`, with n. Sets `margin` and validates `FALLBACK_MARGIN`. Also re-tests whether the "~20pp" figure still holds. | §4.2 |
| **D3** | Cell census: for each `(market_type, bucket)` → n, ROI, shrunk ROI. **How many clear `MIN_CELL_N` and `MIN_SHRUNK_ROI`?** If zero, constants must be relaxed or launch deferred. | §4.3, §7 |
| **D4** | Tier census: `(market, bucket, league_tier)` → n, ROI. Confirms whether §4.4's veto ever has enough sample to fire. | §4.4 |
| **D5** | Distinct `league` values with counts, and which fail exact-name mapping. Seeds the tier map. | §4.7 |
| **D6** | Count of rows whose claim fields changed across re-runs (audit `updated_count` history). Quantifies the §9.1 defect. | §9 |
| **D7** | Odds age distribution: `kickoff − prediction_logged_at`. Validates `STALE_ODDS_WARN_HOURS` and the §4.8 window. | §4.8, §9.2 |
| **D8** | Alignment audit (§15 below). | launch |

**Already observed (2026-07-27 production):** n=276 resolved, ROI 10.6%;
confidence buckets 60–65% n=166, 65–70% n=49, 70–100% n=4 — the basis for the
coarse buckets in §2 and the warning in §7. Separately, `accuracy_by_league`
returns 241 rows with duplicated entries (e.g. Eredivisie repeated identically) —
a **pre-existing dashboard bug** that must be investigated before any league-level
figure is published, though it does not block the selector, which computes tiers
from `PredictionLog` directly.

## 14. Prerequisites (blocking)

1. **P1 — Claim immutability (§9).** Choose approach A or B, implement, test. No
   public posting before this lands.
2. **P2 — Confidence scale confirmed (D1).** Bucketing on the wrong scale
   silently empties the gate.
3. **P3 — Cell census (D3) shows at least one qualifying cell**, or constants are
   consciously relaxed with the weakening documented.

## 15. Alignment audit (launch gate)

The live methodology block states **"Minimum 60% confidence AND positive Expected
Value"** while `over_under_2.5` ships at **0.55** — a contradiction visible in
production today. Before promotion, reconcile across the marketing site,
methodology text, proof card, API, selector and engine:

- per-market confidence thresholds (55 vs 60);
- odds band actually applied vs advertised;
- EV definition (`expected_value` vs `raw_expected_value`);
- what "confidence" is claimed to mean (§3.1);
- model/ensemble count claims;
- recommendation criteria.

They must describe **one** system. Fix the text or fix the code — but not
neither.

## 16. Non-goals (YAGNI)

- No auto-posting, scheduling, or digests.
- No share analytics or UTM machinery.
- No public exposure of the panel or ranking.
- No bootstrap CIs per cell in v1 (shrinkage against a positive bar is the
  chosen MVP treatment; CIs revisit at higher volume).
- No change to what the prediction engine recommends.
- No closing-odds capture in v1 (architecture stays open — §8).
- Card redesign (§11.1) is specified here but implemented as a follow-up task.

## 17. Risks

- **Selector returns nothing at current volume.** Most likely failure. Mitigated
  by D3 before implementation, the `rejected` reasons in the response, and
  treating silence as correct behaviour.
- **Over-fitting the gate to 276 rows.** Every threshold is a judgement on a thin
  sample. Mitigated by single-window recency (no sweeps), a zero prior, and
  constants centralised for revision as n grows.
- **Measured margin is itself noisy** (D2). Mitigated by `MIN_MARGIN_SAMPLE`,
  `FALLBACK_MARGIN`, and `SAFETY_EPS`.
- **Claim mutability** (§9) — blocking, addressed by P1.
- **Stale advertised price** — addressed by honest display, not suppression
  (§9.2).
- **Reputational exposure** while the edge is thin — mitigated by the whole
  design: hard gate, conservative haircut, signal-not-fact captions, honest
  losses.

## 18. Success criteria

1. `/gems` returns at most one recommended pick with full evidence, or an honest
   empty state with machine-readable reasons.
2. Every returned gem passes G1–G8, verifiable from the response.
3. `defensible_edge` demonstrably flips sign under a larger measured margin.
4. `shrunk_roi` against a positive bar rejects high-ROI/low-n cells.
5. Obscurity cannot outrank a materially stronger candidate.
6. A newly-profitable slice becomes postable with no code change.
7. Claim fields are immutable post-publication (P1).
8. Backend tests pass; existing suite green.

## 19. Recommendation

**APPROVE WITH DATA-DEPENDENT PARAMETERS.**

The architecture is sound and the review materially improved it. Implementation
must not begin until **P1–P3** (§14) are resolved, and the constants in §2 marked
DATA-DEPENDENT must be set from D1–D7 rather than from the illustrative values
written here.

## 20. Next step

Run diagnostics D1–D7, resolve P1, then invoke `superpowers:writing-plans`.
