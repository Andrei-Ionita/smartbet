# ROI Calibration Study — Segmented Diagnostic Design Spec

**Date:** 2026-07-22
**Status:** Approved for execution
**Author:** Andrei + Claude
**Parent context:** Follow-on to `docs/superpowers/specs/2026-07-20-roi-tuning-design.md`. The tuning shipped E4 (per-market threshold) + E5 (Kelly badge), moving live ROI 1.3% → 9.6%. The whole-branch review flagged probability calibration as the single highest-leverage follow-up. This spec is that follow-up: a diagnostic-first calibration study on BetGlitch's `confidence` field.

---

## 1. Purpose

Answer one question: **is BetGlitch's displayed probability (SportMonks output + our form-momentum and value-zone adjustments) well-calibrated on the fixtures we actually bet on, and if not, where does the miscalibration live?**

Success looks like: "produce a diagnostic report with an unambiguous per-app-target verdict — for each of {display, Kelly sizing, filter re-selection}, tell me whether calibration is worth applying, and if so, hand off to a follow-on implementation spec."

Not in scope here: production code changes. Calibration wrapper deployment gets its own spec if this diagnostic recommends `APPLY`.

**Framing:** BetGlitch does not train the underlying model — probabilities come from SportMonks. What we calibrate is a wrapper on top of `SportMonks raw → normalize → form momentum → value zone → confidence`. The calibrator corrects for whatever systematic bias accumulates across that chain (including our own adjustments), on the narrow slice we actually bet on.

## 2. Scope & data source

### Universe

Same snapshot as prior audit and tuning: `docs/audit/snapshot-2026-07-16.sqlite` (post-backfill). Filter to:

- `is_recommended=True AND actual_outcome IS NOT NULL AND match_status != 'archived' AND is_audit_excluded != True`
- `market_type = 'over_under_2.5'`
- `profit_loss_10 IS NOT NULL` and `confidence IS NOT NULL`

Expected count: ~252 rows (per prior audit universe).

### Target and feature

- **Feature (X):** `confidence` — the probability of the picked side (over or under 2.5 goals) after the pipeline's adjustments.
- **Target (y):** `was_correct` — binary, 1 if the picked side won, 0 otherwise.

### Excluded markets

`1x2`, `btts`, and `double_chance` combined total n≈23 across the universe. Insufficient for defensible calibration. Documented as such in the report; no calibration attempted on these.

### Analysis phase only

All work in this spec is read-only on production. Production code changes require a separate spec triggered by an `APPLY` verdict.

## 3. Methodology

### Core calibration

**Method:** Platt scaling. Fit a logistic regression `sigmoid(a · confidence + b)` on the training folds, evaluate on held-out folds. `scikit-learn`'s `LogisticRegression` (or hand-fit with numpy — either fine).

**Why Platt:** at n≈252, isotonic and beta calibration risk overfitting the sample. Platt is the standard low-variance choice for calibration at small-to-mid sample sizes. The relationship between confidence and win rate is expected to be monotonic and sigmoid-shaped; Platt is the right functional family.

### Validation

**5-fold cross-validation.** Each fold uses ~200 training rows and ~50 test rows. Fit Platt on training, evaluate all metrics on held-out test, average across folds. Standard `sklearn.model_selection.StratifiedKFold` with `random_state=42`.

**Final reported calibrator:** fit on all 252 rows (used for the reliability diagram and the calibrator that would be applied if verdict is `APPLY`). Cross-validated metrics used for the verdict.

### Diagnostic metrics

- **Brier score** — mean squared error `(prob − outcome)²`. Reported as pre-calibration vs post-calibration; lower is better. Standard proper scoring rule.
- **Reliability diagram** — 10 equal-width bins of predicted probability; plot mean predicted vs empirical rate per bin. Rendered as ASCII table in the report (following audit/tuning convention).
- **Expected Calibration Error (ECE)** — mean absolute gap between predicted and empirical rates, weighted by bin size. Reported pre and post.
- **Bootstrap 95% CI on ECE** — 10,000 resamples, seed 42 (matches audit/tuning convention). Reported for both pre and post.

### Segmentation (Approach C addition)

Compute calibration diagnostics per subgroup — **do NOT fit separate per-subgroup calibrators**. Just report the miscalibration heatmap so we know where the model is worst.

Subgroups:

1. **Confidence bucket** — edges `[0.55, 0.60, 0.70, 0.80, 1.001]` (same as audit/tuning). For each bucket, report n, mean predicted, mean actual, gap. Flag n<15 as "underpowered".
2. **League** — top 5 leagues by O/U 2.5 volume. Same fields as buckets. Flag n<15.
3. **Time period** — chronological halves (first half = older bets, second half = newer). Same fields. Reveals whether the model is drifting.

### Sample-size gates

- **Hard stop:** if universe (after filters) has n < 100, verdict = `INSUFFICIENT_SIGNAL` with reason "sample too small for Platt fit." Current data (n≈252) is comfortably above.
- **Subgroup flag:** any subgroup with n < 15 marked "directional only; sample insufficient for defensible calibration curve."

## 4. Per-app-target decision framework

Every diagnostic produces THREE verdicts — one per potential application target — plus an overall verdict.

### Target A: Display (show calibrated probability in UI)

**APPLY if:**
- Post-calibration Brier score improves by ≥5% (relative — `(brier_pre − brier_post) / brier_pre ≥ 0.05`) AND
- ECE reduces by ≥30% (relative)

**Rationale:** display is low-risk. Even modest improvement in the truthfulness of the displayed number is worth showing users honest data.

### Target B: Kelly stake sizing

**APPLY if:**
- Model is systematically over-confident (raw predicted > empirical rate) in the buckets that receive most stake weight (0.60–0.80 confidence range) AND
- Post-calibration Brier score improves by ≥5% (relative — `(brier_pre − brier_post) / brier_pre ≥ 0.05`) AND
- Bootstrap CI on the "raw − calibrated" gap in those buckets excludes zero

**Rationale:** Kelly stakes scale with `prob × odds − 1`. Over-confident probs → over-sized stakes → over-leveraging → larger drawdowns than backtested. This is the highest-impact target if the diagnostic shows over-confidence.

**DO_NOT_APPLY if:** model is well-calibrated OR under-confident. Applying calibration in the under-confident case would grow stakes and increase risk.

### Target C: Filter re-selection

**APPLY if:**
- Re-filter using `calibrated_prob ≥ 0.55` (matches the SHIPed E4 threshold from tuning); compute ROI + bootstrap CI on the re-filtered subset AND
- Re-filtered ROI > current subset ROI by ≥2pp AND
- Bootstrap CI lower bound on re-filtered ROI is ≥ +1% (matches tuning verdict criteria)

**Rationale:** this is where calibration can produce an indirect ROI lift, by selecting a different subset of picks that map onto true probability ≥0.55 rather than raw ≥0.55.

**DO_NOT_APPLY if:** re-filtered ROI is same or worse. Filter re-selection is the highest-risk target; only apply if we have direct evidence of ROI improvement.

### Overall verdict

- `APPLY` — at least one target has `APPLY`. Follow-on implementation spec triggered.
- `INSUFFICIENT_SIGNAL` — sample size hard-stop OR all targets show `DO_NOT_APPLY` because improvements are within noise.
- `DO_NOT_APPLY` — model is already well-calibrated (Brier score barely changes) OR calibration would make things worse.

## 5. Deliverables

### Analysis script

**Path:** `docs/audit/roi-calibration-2026-07-22.py`

Single-file Python script (`pandas`, `numpy`, `sklearn.linear_model.LogisticRegression`, `sklearn.model_selection.StratifiedKFold`). Reads sqlite snapshot. Emits printed diagnostic sections; when `--out <path>` supplied, writes the assembled report.

Reuses helpers from prior scripts where possible (`bootstrap_ci`, `_coerce_bool`, `TRUE_STRINGS`) — copy-paste is fine given the same-directory convention already established.

CLI:
```bash
python docs/audit/roi-calibration-2026-07-22.py \
  --snapshot docs/audit/snapshot-2026-07-16.sqlite \
  --out docs/audit/roi-calibration-2026-07-22.md
```

### Diagnostic report

**Path:** `docs/audit/roi-calibration-2026-07-22.md`

**Structure:**

1. **Executive verdict** (single paragraph) — Overall verdict + per-target verdicts (Display / Kelly / Filter) on one line each.
2. **Data provenance** — snapshot path, size, universe count, filter applied, run timestamp.
3. **Global calibration**
   - Fitted Platt coefficients (a, b)
   - Brier score pre vs post
   - ECE pre vs post with bootstrap 95% CIs
   - ASCII reliability diagram
4. **Segmentation heatmap** — three subsections (confidence bucket, league, time period). Each shows per-subgroup n, mean predicted, mean actual, gap, flag for underpowered.
5. **Per-target decision** — for each of {Display, Kelly, Filter}: verdict, criteria met/not met, one-sentence justification.
6. **Recommended next step** — either "invoke follow-on implementation spec" (with concrete file targets) or "collect more data, re-audit at n=500".
7. **Non-goals** (see §7 below).

### Reproducibility

- Analysis script committed. Anyone with the snapshot can regenerate the report.
- Tests file `docs/audit/test_roi_calibration_helpers.py` for pure helpers (Platt fit-and-predict on synthetic data with known truth; ECE on synthetic input with known gap).

## 6. Success criteria for the spec itself

- Analysis runs end-to-end in a single focused session (~3-4 hours).
- Report committed to git with all numbers, CIs, and heatmaps; no placeholders.
- Executive verdict is unambiguous — Andrei can act on a single sentence.
- Per-target verdicts are directly actionable — "APPLY to Kelly" means the follow-on spec has a clear target.

## 7. Explicit non-goals

Documented so the report does not overclaim:

- **No production code changes in this spec.** Deployment is a separate decision + separate spec if triggered.
- **No retraining SportMonks' model** — impossible, they own it.
- **No modifying form-momentum or value-zone adjustments** — those are separate refactorings; calibration wraps whatever comes out of them.
- **No per-league or per-time-period separate calibrators** — segmentation is diagnostic only; per-slice sample sizes are too small for defensible per-slice fits.
- **No comparison of multiple calibrator methods** (Platt vs isotonic vs beta) — Approach B was explicitly rejected during brainstorming. Platt is the right tool at n≈252.
- **No 1x2 / BTTS / DC calibration** — combined n=23 is insufficient. Documented explicitly in report.
- **No prospective forward-test** — this analysis is retrospective on the existing snapshot. Any calibrator we later apply gets its own forward validation.
- **No SportMonks vendor comparison** — we do not evaluate whether a different data provider would be better-calibrated. Out of scope.

## 8. Risks

- **Sample-size stress on the segmentation.** 252 rows split across 5 confidence buckets averages 50/bucket; 5 leagues averages 50/league; but the actual distribution is skewed (most bets in one bucket, one league). Expect some segments to hit the n<15 underpowered flag. Mitigation: honest flagging in the report; do not act on underpowered segments.
- **Platt assumes sigmoid relationship.** If the true miscalibration is not sigmoid-shaped (e.g., over-confidence at one range, under-confidence at another), Platt cannot capture it and the Brier improvement will be small. Mitigation: reliability diagram in the report will show if this is the case; verdict criteria are strict enough to catch it.
- **Retrospective vs prospective.** Calibrator fitted on this snapshot may not generalize to future SportMonks updates (they can change their model without notice). Mitigation: non-goal explicitly notes any calibrator we apply needs forward validation; report recommends periodic re-fit.
- **Segmentation could mislead if user acts on tiny slice.** e.g., "Bundesliga is 20pp over-confident on n=12" is directional only; user might over-index on it. Mitigation: underpowered flag on any subgroup with n<15; report explicitly warns against acting on underpowered segments.

## 9. Next step after user approval

Invoke `superpowers:writing-plans` to produce a step-by-step execution plan (which analysis to run first, checkpoints, how to structure the final report). Same shape as audit and tuning plans.
