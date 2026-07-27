# Hidden-Gem Selector — Design Spec

**Date:** 2026-07-27
**Status:** Approved for planning
**Author:** Andrei + Claude
**Parent context:** Second build of the growth thread, following the proof-card
generator (`2026-07-25-proof-card-generator-design.md`). The cards work; the
open question was *which fixture to post*. This spec answers that.

---

## 1. Purpose

Give the founder a ranked, defensible answer to **"which upcoming pick should I
post to socials this week?"** — or an explicit **"none this week."**

### 1.1 The reframe that drives this

The initial framing was "catchy = famous teams." That was wrong, and it fought
our actual strengths. Marquee fixtures (EPL, UCL) sit in the sharpest, most
efficient markets, where the ROI audit showed our edge barely survives. Our
genuine edge lives in obscure leagues nobody is modelling closely.

The correct framing, from the founder: **catchy = a hidden gem** — an unglamorous
fixture with a real, defensible mispricing. This is what the engine already does
(scan 27 leagues nightly for value), so we lead with our strength instead of
apologising for our weakness.

It also self-selects the right audience. We are not chasing "football fans"; we
are chasing **value bettors**, who care that the number is good, not that the
teams are famous — and who respect a timestamped, transparent record over a
hype-man. The hook writes itself: *"Nobody's talking about this one. Our model
says the market has it wrong. Logged before kickoff — come back and check."*

### 1.2 Defensibility over spectacle

The founder chose **maximum defensibility**. The design expresses that as a
**gate, not a weight**: a blended score would let a shaky-but-thrilling pick buy
its way to the top on obscurity points, and that is precisely the pick that blows
up in public.

The asymmetry justifies it. We have no audience to lose, but also **no
credibility reserve to absorb a blowup**. The record is n=267. One loud
overclaim that loses, in front of sharp bettors who *will* check, costs the only
asset the brand has.

**Explicit non-goal, inherited from the parent thread:** cards and captions
present transparent data, never a profit promise.

## 2. Scope

### What we build
- A two-stage selector (defensibility gate → gem ranking) computed from data
  already in `PredictionLog`.
- One staff-only Django endpoint returning ranked gems + an "on deck" list.
- One private frontend page (`/gems`) with copy-to-clipboard link and caption.

### What already exists (reuse, do not rebuild)
- `PredictionLog` — every field needed: `fixture_id`, `home_team`, `away_team`,
  `league`, `league_id`, `kickoff`, `market_type`, `predicted_outcome`,
  `confidence`, `odds`, `expected_value`, `was_correct`, `is_recommended`,
  `is_audit_excluded`. Indexed on `('is_recommended', '-kickoff')`.
- `core/services/accuracy_calculator.py` — `_confidence_filter()` and
  `PER_MARKET_CONF_THRESHOLDS` are the **single source of truth** for the
  per-market confidence gate. Reuse; do not fork.
- `/api/proof/<fixture_id>/` and `/proof/<fixtureId>` — the card and share
  surface. The selector only produces a fixture_id and a link to it.
- DRF auth (`permission_classes`, Bearer tokens) and frontend `AuthContext`.

### Not in scope
No new model, no migration, no change to the prediction engine, no change to
what gets recommended.

## 3. Selection logic

### 3.1 Stage 1 — Defensibility gate (pass/fail, no trade-offs)

A pick is eligible only if **all** of the following hold:

1. **Live published claim:** `is_recommended=True`, `was_correct IS NULL`,
   `kickoff > now`, `is_audit_excluded=False`.
2. **Priceable:** `odds` is not null and `1.4 <= odds <= 3.5`. Outside that band
   our sample is too thin to defend.
3. **Clears the per-market confidence threshold**, via the existing
   `_confidence_filter()` (0.55 for `over_under_2.5`, 0.60 otherwise).
4. **Proven cell:** the pick's `(market_type, confidence_bucket)` slice has
   **`roi_percent > 0` on our own resolved history** with **n >= 30**. All ROI
   figures in this spec are percentages, matching
   `get_roi_simulation()['roi_percent']`.
5. **Positive shrunk edge:** `defensible_edge > 0` (see §3.3). If the edge
   evaporates once we correct for model over-confidence, it is not a gem.

If nothing passes, the selector returns **no gems**. This is a valid, intended
output — see §3.5.

**Confidence buckets** are fixed 0.05-wide bands on the 0–1 scale:
`[0.55,0.60)`, `[0.60,0.65)`, `[0.65,0.70)`, `[0.70,0.75)`, `[0.75,1.00]`.
Picks below 0.55 cannot pass rule 3 and are never bucketed.

**Cell ROI** is computed over resolved, non-audit-excluded, `is_recommended=True`
rows in that cell, using the same profit convention as
`AccuracyCalculator.get_roi_simulation()` (flat stake), so the gate and the
public record never disagree.

### 3.2 Anti-calcification (a required property, not an optimisation)

The gate must **not** freeze us into the slices that worked historically.

- **The gate filters what we POST, never what we PREDICT.** The engine keeps
  recommending across every slice; `PredictionLog` keeps logging all of them;
  the track record keeps accumulating everywhere. Selection for publication is
  strictly downstream of selection for prediction, so there is **no feedback
  loop into the model** and no slice is starved of data.
- **Cell ROI is a live query, not a hardcoded whitelist.** It is computed from
  `PredictionLog` at request time. Therefore a slice that becomes profitable
  **graduates in automatically** with no code change or redeploy, and a slice
  that decays **drops out automatically**. Every engine improvement (confluence
  filters, SportMonks squeeze, future calibration) flows straight through.
- **Hardcoding eligible cells as a constant is explicitly forbidden** by this
  spec. It is the failure mode this section exists to prevent.

### 3.3 Stage 2 — Gem ranking (survivors only)

`gem_score = 0.45 * edge_norm + 0.35 * obscurity + 0.20 * timing`

Weights are named constants, tunable in one place.

**Defensible edge** — deliberately *not* raw model EV, which runs ~20pp hot per
the calibration study (`2026-07-22` study, verdict DO_NOT_APPLY for correction,
but the direction of the bias is established).

```
market_implied = 1 / odds
shrunk_prob    = market_implied + SHRINK * (model_conf - market_implied)   # SHRINK = 0.5
defensible_edge = shrunk_prob * odds - 1
edge_norm      = clamp(defensible_edge / 0.15, 0, 1)                        # +15% edge = full marks
```

`1 / odds` includes the bookmaker's vig, so it *overstates* the market's true
probability and therefore *understates* our edge. That conservative direction is
intentional; de-vigging is not worth the complexity here.

**Obscurity** — the hidden-gem hook. Three tiers matched on `league` name
(case-insensitive substring; `league_id` may be null so name is authoritative):

- **Tier A — mainstream (0.0):** Premier League, La Liga, Serie A, Bundesliga,
  Ligue 1, Champions League, Europa League, World Cup, European Championship.
- **Tier B — well-known second tier (0.5):** Championship, Eredivisie,
  Primeira Liga, Scottish Premiership, MLS, Liga MX.
- **Tier C — everything else (1.0):** the real gems. Default tier.

In practice obscurity mostly acts as a **penalty for mainstream** rather than a
fine-grained differentiator, since most qualifying picks are Tier C. That is
accepted and honest.

**Timing fit** — a step function on hours-to-kickoff, chosen over interpolation
because it is trivial to test and reason about:

| Hours to kickoff | Score | Rationale |
|---|---|---|
| `< 24` | 0.1 | too late to post and still get a return loop |
| `24–48` | 0.5 | usable but tight |
| `48–168` (2–7d) | 1.0 | ideal: time to post, time for people to come back |
| `168–240` (7–10d) | 0.6 | getting stale |
| `> 240` | 0.3 | too far out to hold attention |

Return **at most the top 5** gems, ordered by `gem_score` descending.

### 3.4 On deck (discovery, not selection)

The panel also surfaces slices *close to graduating*, so the gate reads as a
discovery dashboard rather than a fence, and the founder can watch new edge
forming:

- cells with `ROI > 0` and `10 <= n < 30` (promising, not yet proven), or
- cells with `n >= 30` and `-5 <= ROI <= 0` (borderline, may recover).

On-deck cells are **reported only** — they never make a pick postable.

### 3.5 The empty state is a feature

If no pick clears the gate, the response is an empty gem list and the page says
**"No gem worth posting right now."** Tools that always produce an answer quietly
pressure the user into posting garbage on a slow week. Silence protects the feed.

**Expected at launch:** with only ~4 live picks and a thin record, the gate may
legitimately return nothing. Implementation must report what the real data
yields so the founder knows whether the tool is working-but-quiet or broken.

## 4. Architecture

### 4.1 Confidence scale — pin this down first

`PredictionLog.confidence` is documented as "e.g., 62.5" (0–100), while
`PER_MARKET_CONF_THRESHOLDS` uses 0.55/0.60 (0–1), and `/api/proof/` normalises
defensively (`c * 100 if c <= 1 else c`). This ambiguity is a live bug risk for
any threshold comparison.

**Requirement:** the selector defines **one** normalisation helper converting
confidence to the 0–1 scale, uses it for every comparison and bucketing, and the
implementation **verifies the real distribution in production data** before
trusting either convention. Bucketing on the wrong scale silently empties the
gate.

### 4.2 Backend

`GET /api/gems/` — staff-only (`IsAdminUser`, matching the existing
`permission_classes` pattern in `core/`).

```json
{
  "generated_at": "2026-07-27T09:00:00Z",
  "gems": [
    {
      "fixture_id": 19726943,
      "home_team": "Cardiff City", "away_team": "Swindon Town",
      "league": "Carabao Cup",
      "kickoff": "2026-08-08T17:00:00Z",
      "market_type": "btts", "predicted_outcome": "BTTS Yes",
      "odds": 1.8, "confidence": 0.643,
      "gem_score": 0.71,
      "components": {
        "edge_norm": 0.52, "defensible_edge": 0.079,
        "obscurity": 1.0, "timing": 1.0
      },
      "cell": { "key": "btts@0.60-0.65", "n": 41, "roi_percent": 6.2 },
      "proof_url": "https://www.betglitch.com/proof/19726943",
      "caption": "Nobody's talking about this one..."
    }
  ],
  "on_deck": [
    { "key": "double_chance@0.65-0.70", "n": 18, "roi_percent": 4.1,
      "reason": "promising_low_n" }
  ]
}
```

`components` and `cell` are returned so the founder can see **why** a pick ranked
first and overrule it. An opaque score would be untrustworthy.

### 4.3 Frontend

`/gems` — `noindex`, gated through the existing `AuthContext`. Per gem: the
pick, its score breakdown, the proven-cell stats, **Copy proof link**, **Copy
caption**. Below: the on-deck list. Empty state per §3.5.

Not linked from public navigation.

### 4.4 The caption

A **starting draft the founder edits**, never an auto-post. Honest framing, no
profit promise:

> Nobody's talking about this one. Our model has the market mispriced here.
> Logged before kickoff — result auto-verifies at full-time, win or lose.
> <proof_url>

### 4.5 Data flow

```
/gems → gate → rank → founder copies link + caption
      → posts to a value-betting community
      → link unfurls into the Pick card (pre-kickoff proof)
      → audience returns after full-time for the Result card
```

## 5. Testing

Backend unit tests in `core/tests.py`:

- **Each gate rule in isolation:** resolved pick excluded; past kickoff excluded;
  null odds excluded; odds outside 1.4–3.5 excluded; below-threshold confidence
  excluded; `is_audit_excluded` row excluded; unproven cell (n < 30) excluded;
  negative-ROI cell excluded; negative shrunk edge excluded.
- **Empty state:** no qualifying picks → `gems: []`, HTTP 200 (not 404).
- **Ranking order:** given three synthetic survivors, assert the expected order
  and that weights produce it.
- **Cell ROI is live:** adding resolved rows that flip a cell positive makes a
  previously-gated pick eligible **without any code change** — the explicit
  regression test for §3.2.
- **Confidence normalisation:** rows stored on both 0–1 and 0–100 scales bucket
  identically.
- **Access control:** anonymous and non-staff authenticated users are rejected;
  staff succeeds.
- **On deck:** a cell with n=18 and positive ROI appears in `on_deck` and its
  picks do **not** appear in `gems`.

Existing suite must stay green. No frontend test framework exists; the page is
verified visually (consistent with the parent thread).

## 6. Non-goals (YAGNI)

- **No auto-posting** to any platform. The founder posts by hand; automation is
  premature before we know anyone cares.
- **No scheduling / weekly digest / email.**
- **No share analytics or UTM machinery.**
- **No public exposure** of the panel or the gem ranking.
- **No new model, migration, or change to the prediction engine.**
- **No bootstrap confidence intervals per cell** — `n >= 30 AND ROI > 0` is the
  v1 gate. Tightening to a CI lower bound is a future option once volume
  supports it; applied now it would gate out everything.

## 7. Risks

- **Gate returns nothing at launch** (§3.5). Mitigated by treating that as a
  valid output and by reporting real-data results during implementation.
- **Small-n luck:** a cell can look positive by chance at n=30. Mitigated by
  displaying n and ROI so the founder can eyeball solidity, and by the deferred
  CI tightening in §6.
- **Confidence-scale mismatch** (§4.1) silently empties the gate. Mitigated by a
  single normalisation helper, a dedicated test, and production verification.
- **Obscurity tier lists drift** as leagues are added. Mitigated by keeping them
  as short, clearly-commented constants in one place.
- **Reputational exposure**, inherited: posting makes BetGlitch more visible
  while the edge is thin. Mitigated by the entire design — defensibility as a
  hard gate, shrunk edge rather than raw EV, and captions that sell transparency
  rather than profit.

## 8. Success criteria

1. `/gems` returns a ranked, defensible shortlist — or an honest empty state.
2. Every returned gem passes all five gate rules, verifiable from the response.
3. The founder can see *why* each pick ranked, and overrule it.
4. One click yields a proof link and a caption ready to paste.
5. A newly-profitable slice becomes postable with **no code change** (§3.2 test).
6. Backend tests pass; existing suite stays green.

## 9. Next step

Invoke `superpowers:writing-plans` to produce the task-by-task implementation
plan (confidence-scale verification → cell-ROI service + tests → gate + ranking
+ tests → endpoint + access control → `/gems` page → real-data validation).
