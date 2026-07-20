# ROI Tuning — Approach 1 (Tactical Quick-Wins) Design Spec

**Date:** 2026-07-20
**Status:** Approved for execution
**Author:** Andrei + Claude
**Parent context:** Follow-on to `docs/superpowers/specs/2026-07-16-roi-audit-design.md`. The audit revealed real-odds ROI is near-zero (−2% UI-matching, +3% unfiltered) once legacy rows were backfilled. This spec tests whether the audit's own action items can lift ROI meaningfully on existing data before we invest in a deeper model rebuild.

---

## 1. Purpose

Answer one question: **is there enough edge in BetGlitch's existing prediction pipeline to make it a viable consumer product, or do we need a deeper rebuild?**

Success looks like: "run 5 cheap experiments against the existing snapshot; at the end, either a concrete set of production changes that moves ROI to a defensible positive number, or a clear signal that Approach 2 (Deep Model Rebuild) or Approach 3 (Niche Specialization) is required."

This spec is the first step of a **Path A (consumer product)** roadmap toward a €1M acquisition, following the 2026-07-16 ROI audit that hard-blocked the current published number.

## 2. Scope & data source

### Universe

Same snapshot as the 2026-07-16 audit: `docs/audit/snapshot-2026-07-16.sqlite`, refreshed post-backfill. 275 rows in the audit universe (recommended, resolved, non-archived, non-excluded). 210 UI-matching (confidence ≥ 0.60), 275 unfiltered.

All experiments read from this snapshot. No production DB writes during the experiment phase — that comes only after the report is written, reviewed, and decisions are locked.

### Two-phase execution

1. **Analysis phase** — script runs, report is written to `docs/audit/roi-tuning-2026-07-20.md`, committed to git. Zero production impact.
2. **Deployment phase** — only if the report contains ≥1 `SHIP` verdict. Concrete production changes then follow (see §5).

### Statistical rigor

Every experimental result carries a bootstrap 95% confidence interval (10,000 resamples, seed 42 — same convention as the audit script). Point estimates without CI are noise-magnifiers; the CI is what determines whether a change is worth deploying.

## 3. The 5 experiments

### E1 — Threshold sweep (confidence lower bound)

**Hypothesis:** The current UI filter `confidence ≥ 0.60` is not optimal. Audit Q4 showed the 0.55–0.60 bucket has +29.89% ROI on 57 unfiltered bets; the current threshold cuts it out.

**Method:**
- Sweep confidence lower bound from 0.50 to 0.75 in 0.01 steps.
- For each threshold `t`, compute: `n`, `ROI point estimate`, `ROI 95% CI` on the subset with `confidence ≥ t`.
- Emit: table + ASCII line chart of ROI vs threshold.

**Success (SHIP):** find a threshold `t*` where `CI_lo > +1%` AND `n ≥ 100`.

**Deliverable:** recommended threshold value + expected ROI + CI at that threshold.

### E2 — EV shrinkage factor

**Hypothesis:** The model's EV estimates are systematically ~20 percentage points too optimistic (audit backfill finding). A shrinkage factor `k` applied to the model's EV before the display filter would keep only picks with genuine value.

**Method:**
- Sweep shrinkage factor `k` from 0.5 to 1.0 in 0.05 steps.
- For each `k`, apply `ev_shrunk = ev * k` and re-filter with `ev_shrunk ≥ 0.05` (matches current frontend filter).
- Compute ROI + CI on the surviving subset.

**Success (SHIP):** find a `k*` where `CI_lo > +1%` AND `n ≥ 100`.

**Deliverable:** recommended shrinkage factor + expected ROI + CI at that factor.

### E3 — League filtering (blacklist losers, whitelist winners)

**Hypothesis:** A few leagues (Serie B, Eliteserien, Premier League were strongly negative in the audit) drag overall ROI down. Removing them raises overall edge.

**Method:**
- For each league with `n ≥ 15` in the universe, compute ROI + bootstrap CI.
- Identify:
  - **Blacklist candidates:** CI entirely below zero (`CI_hi < 0`).
  - **Whitelist candidates:** CI entirely above zero (`CI_lo > 0`).
  - **Neutral:** everything else.
- Simulate three scenarios: (a) current pipeline, (b) blacklist applied, (c) whitelist-only applied. Report ROI + CI for each.

**Success (SHIP):** blacklist scenario has `CI_lo > +1%` AND retained `n ≥ 100`.

**Deliverable:** proposed additions to `PHASE_2A_BLACKLISTED_LEAGUES` (if any).

### E4 — Market × confidence 2D grid

**Hypothesis:** The edge lives in specific market-confidence combinations, not uniformly across the pipeline. E.g., "O/U 2.5 in the 0.55–0.60 bucket" may be the real product.

**Method:**
- Grid: 4 markets (`1x2`, `btts`, `over_under_2.5`, `double_chance`) × 4 confidence buckets (`[0.55, 0.60)`, `[0.60, 0.70)`, `[0.70, 0.80)`, `[0.80, 1.00]`).
- Compute ROI, `n`, and CI per cell. Flag cells with `n < 30` as underpowered.
- Emit as a heatmap-style table.

**Success (SHIP):** find ≥1 cell with `CI_lo > +1%` AND `n ≥ 30` (looser sample threshold because the cell-level pipeline is a proposal for a *market-specific* filter, not the universal one from E1).

**Deliverable:** proposed market-specific confidence thresholds (e.g., "keep `over_under_2.5` at `≥ 0.55`; block `1x2` entirely regardless of confidence").

### E5 — Kelly sizing simulation

**Hypothesis:** Flat $10 stakes leave value on the table. Kelly-optimal fractional stakes (bigger bets on higher-edge picks, smaller on marginal ones) may capture materially more of the model's expected value.

**Method:**
- Simulate chronologically through the 275 resolved bets in the universe.
- Starting bankroll: $1000.
- Kelly formula: `stake = bankroll × k_fraction × (p × odds − 1) / (odds − 1)` where `p = confidence`, `odds` = the real backfilled odds, `k_fraction` = 0.25 (quarter-Kelly, standard conservative default).
- Compare vs a flat-$10 baseline sim.
- Report: final bankroll for each, max drawdown, geometric ROI.

**Success (SHIP):** Kelly final bankroll > Flat final bankroll by ≥5% AND max drawdown ≤50%.

**Deliverable:** stake-sizing recommendation for the frontend (either "use Kelly at k=0.25" or "flat is fine, Kelly adds volatility").

## 4. Deliverables

### 4.1 Analysis script

**Path:** `docs/audit/roi-tuning-2026-07-20.py`

Single-file Python script (pandas, numpy, no Django ORM). Reads from the sqlite snapshot. Emits printed sections for each experiment and, when `--out <path>` is passed, writes the assembled Markdown report.

CLI:
```bash
python docs/audit/roi-tuning-2026-07-20.py \
  --snapshot docs/audit/snapshot-2026-07-16.sqlite \
  --out docs/audit/roi-tuning-2026-07-20.md
```

Reuses helpers from the audit script where possible (bootstrap CI, load_and_filter, ASCII chart).

### 4.2 Tuning report

**Path:** `docs/audit/roi-tuning-2026-07-20.md`

**Structure:**

1. **Executive verdict** — single paragraph above the fold. Either:
   - "Ship: [concrete list of production changes with expected ROI impact]," or
   - "No ship: current pipeline cannot support a defensible positive ROI on this dataset; escalate to Approach 2 or 3."
2. **Baseline recap** — current ROI, CI, sample size (from the 2026-07-16 audit).
3. **E1–E5 sections** — each contains:
   - Hypothesis (from this spec)
   - Method summary
   - Result table with CI on every number
   - Chart (ASCII where applicable)
   - **Verdict:** `SHIP` / `INVESTIGATE` / `DISCARD`
4. **Combined recommendation** — if ≥1 SHIP, the concrete production diffs to make.
5. **Limits / non-goals** (see §6).

## 5. Decision framework and production changes

### 5.1 Per-experiment verdict criteria

| Verdict | Criterion |
|---|---|
| **SHIP** | Bootstrap 95% CI lower bound > +1% AND sample size ≥ 100 (or ≥30 for E4 market-specific cells) |
| **INVESTIGATE** | Point estimate > +3% but CI still crosses zero, OR sample size below the ship threshold |
| **DISCARD** | Point estimate ≤ 0% or clearly noise |

### 5.2 Combined action logic

- **≥1 SHIP** → deploy the corresponding production changes (see §5.3). Verify live number moves as expected. Wait 2 weeks for new data before re-audit.
- **0 SHIP but ≥2 INVESTIGATE** → design a follow-up experiment or expand sample first (audit's Action #8: continue collecting to n=500). Do NOT ship on INVESTIGATE-tier results.
- **All DISCARD** → escalate to Approach 2 (Deep Model Rebuild) or Approach 3 (Niche Specialization). Approach 1's cheap-tunings hypothesis is falsified.

### 5.3 Concrete production changes if experiments SHIP

| Experiment | File to edit | Nature of change |
|---|---|---|
| E1 (threshold) | `core/services/accuracy_calculator.py:149` (`confidence__gte=0.60`) + `smartbet-frontend/app/api/recommendations/route.ts:405` (`gap >= minGap && ev >= 0.05`) | Lower the confidence threshold to `t*` |
| E2 (EV shrinkage) | `smartbet-frontend/app/api/recommendations/route.ts` (near line 386, 510, 573 where `ev` is computed) | Multiply `ev` by `k*` before the `ev >= 0.05` filter |
| E3 (league filter) | `core/api_views.py` (Phase 2a blacklist constant) | Append blacklist candidates to `PHASE_2A_BLACKLISTED_LEAGUES` |
| E4 (market × conf) | `core/services/accuracy_calculator.py` (`get_roi_simulation` filter logic) | Add market-specific confidence thresholds |
| E5 (Kelly sizing) | `smartbet-frontend/app/components/StakeRecommendation.tsx` and bankroll widget | Switch default stake sizing to Kelly at `k=0.25` |

### 5.4 Post-deployment verification

- Immediately after redeploy, poll `/api/transparency/dashboard/` and confirm the live ROI moves in the expected direction (with the caveat that any change to the confidence filter will exclude older rows too, so live ROI may jump immediately, not gradually).
- Weekly poll for 2 weeks; confirm the number stabilizes near the projected value.
- Rollback path: every change is a single-file diff; `git revert` and redeploy is < 5 minutes.

## 6. Explicit non-goals

Documented so the tuning report does not overclaim:

- **No new model IP** — that is Approach 2's territory. This spec is tunings on the existing pipeline, not new signals.
- **No feature engineering** — no xG, no lineups, no injuries, no referee data. Same input features throughout.
- **No SportMonks response reprocessing** — we do not re-derive probabilities. We only tune the filters applied to what the existing pipeline outputs.
- **No new markets or leagues** — only tunings on what is already covered.
- **No user-facing UI redesign beyond the potential confidence threshold display change.**
- **No prospective forward-test** — everything is retrospective on the existing 275-bet snapshot. Phase 2 (sealed forward-test) is deferred until Approach 1's changes are shipped and stable.
- **No changes to user-facing pricing, subscription, or Polar plumbing.**

## 7. Success criteria for this spec itself

- All 5 experiments run end-to-end in one focused session (~3-4 hours).
- Report committed to git with all numbers and CIs, no placeholders.
- Each experiment carries an explicit `SHIP` / `INVESTIGATE` / `DISCARD` verdict.
- If any experiment SHIPs, the corresponding production diff is straightforward from §5.3.
- The Executive verdict at the top of the report is unambiguous — Andrei can decide "deploy" or "escalate to Approach 2/3" without needing to re-interpret the data.

## 8. Risks

- **Sample size too small even after tuning.** n=275 is on the low end; splitting by market and confidence bucket makes some cells vanish. Mitigation: bootstrap CI honestly reflects this uncertainty; verdict criteria enforce a floor.
- **Correlation between experiments.** E1 (threshold) and E4 (market × confidence) overlap — a global threshold change and a market-specific threshold change are alternatives, not additive. Mitigation: combined recommendation section explicitly picks one or the other, not both.
- **Over-fitting to this specific snapshot.** All 5 experiments are optimizing against 275 known outcomes. The "tuned" filters may look great on this data and fail on new data. Mitigation: honest bootstrap CI narrows the risk; Phase 2 sealed forward-test is the ultimate check.
- **Production change lands during World Cup break with no data to observe.** New bets are thin through late July 2026. Mitigation: the immediate ROI number will still move (because it's computed on historical data with the new filter), and the "wait 2 weeks for new data" step in §5.4 becomes "wait until August fixture volume returns."

## 9. Next step after user approval

Invoke `superpowers:writing-plans` to produce a step-by-step execution plan (which experiment to run first, checkpoints, how to structure the final report).
