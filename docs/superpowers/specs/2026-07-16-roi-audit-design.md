# ROI Audit — Design Spec

**Date:** 2026-07-16
**Status:** Approved for execution
**Author:** Andrei + Claude
**Deliverable:** Written audit report at `docs/audit/roi-audit-2026-07-16.md` + reproducible script

---

## 1. Purpose

Determine whether the ROI figure currently published on BetGlitch's public track record page (`/track-record`, typically shown as ~19%) is a **defensible measurement of forecasting edge** or an **artifact of variance, selection bias, or sample-size noise**.

The audit is the first step of a two-phase validation program:

- **Phase 1 (this spec):** Retrospective statistical audit of the existing `PredictionLog` history.
- **Phase 2 (deferred, contingent on Phase 1):** Sealed forward-test — a `verified_track_start` timestamp captured today, all future recommendations tagged, exposed separately on-site as an audit-immune track record.

Phase 2 is out of scope for this spec but its viability depends on Phase 1's verdict. If Phase 1 reveals systemic problems (bad odds capture, off-by-one match reconciliation, cherry-picked filters), those get fixed before Phase 2 launches on a broken foundation.

## 2. Scope & data source

### Universe

Rows in `PredictionLog` where **all** apply:

- `is_recommended = True`
- `actual_outcome IS NOT NULL` (resolved bets only)
- `match_status != 'archived'` (exclude SportMonks 404s)
- `is_audit_excluded != True` (respect existing exclusion flag)

### Time window

Full history in production DB. If sample size supports it, also produce a trailing-90-day view for recency comparison.

### Two filter variants, always computed side-by-side

1. **UI-matching filter** — additionally requires `confidence >= 0.60`. Reproduces the number the site currently shows.
2. **Unfiltered** — no confidence floor. Shows what the raw pipeline produces before the display threshold.

Reporting both makes it obvious whether the 19% is a real edge or a display-threshold artifact.

### Data access

Read-only snapshot pulled via Railway CLI (`railway connect Postgres` → `pg_dump` → local sqlite). No write access to production. Snapshot timestamp recorded in the audit report's provenance section.

## 3. Audit questions

Eight questions, ranked by likelihood of invalidating the headline number if the answer is bad. Each will be answered for both filter variants (UI-matching + unfiltered).

### Q1 — Sample size and time coverage

- How many resolved recommended bets exist?
- Over what date range (`MIN`/`MAX(prediction_logged_at)`)?
- Distribution of bets per month.

**Falsifies if:** Total resolved bets < ~100. Below that threshold, no ROI number is statistically meaningful.

### Q2 — Point estimate and 95% confidence interval

- ROI point estimate: `SUM(profit_loss_10) / (COUNT * 10) * 100`
- 95% CI via bootstrap: resample 10,000 times with replacement, report 2.5th / 50th / 97.5th percentiles.

**Falsifies if:** CI includes zero or a large negative value. "19% ± 25%" means we can't distinguish signal from noise.

### Q3 — Monthly ROI stability

- Group bets by `DATE_TRUNC('month', prediction_logged_at)`.
- Compute ROI per month, plus bet count.
- Visualize as ASCII bar chart in the report.

**Falsifies if:** One or two hot-streak months carry the whole number while other months are flat or negative. Consistent skill produces consistently positive months, not one big spike.

### Q4 — Confidence bucket effect

- Bucket bets: `[0.55, 0.60), [0.60, 0.70), [0.70, 0.80), [0.80, 1.00]`.
- ROI per bucket, sample size per bucket.
- Flag buckets with n < 30 as underpowered.

**Falsifies if:** ROI is negative or zero in the low-confidence buckets and only strongly positive in the top bucket. The display threshold would then be dishonestly low — real edge starts at 0.70 (or whatever bucket is actually profitable), not 0.55.

### Q5 — Market breakdown

- Group by `market_type` (`1x2`, `btts`, `over_under_2.5`, `double_chance`).
- ROI, bet count, win rate per market.
- Flag markets with n < 30 as underpowered (same threshold as Q4, Q6).

**Falsifies if:** One market accounts for essentially all profit while others are near-zero or negative. Not "diversified skill" — one-trick model.

### Q6 — League breakdown

- Top 10 leagues by bet count.
- ROI, bet count, win rate per league.
- Flag leagues with n < 30 as underpowered.

**Falsifies if:** One or two leagues dominate profit. Same failure mode as Q5 — narrow edge rather than transferable skill.

### Q7 — Profit concentration

- Sort `profit_loss_10` values descending.
- Report the % of total profit contributed by the top 1, top 5, top 10, top 25 bets.
- Compare to what would be expected under a null hypothesis (uniform contribution).

**Falsifies if:** Top 5 bets contribute > 60% of total profit. Fragile track record — remove those 5 wins and the edge collapses. Real skill produces a broad distribution, not fat-tailed by a few lucky longshots.

### Q8 — Odds sanity

- Compute `AVG(odds)` per confidence bucket.
- Expected pattern: higher confidence → lower odds (bookmakers agree with our high-conf picks).
- Flag any inversion (high-conf picks with high odds) — likely a data-quality issue, not real value.

**Falsifies if:** Odds distribution is internally inconsistent. Suggests something's wrong with how odds get captured or stored — undermines every other question because the entire P&L calc rests on the odds field.

## 4. Deliverable

### Written report

**Path:** `docs/audit/roi-audit-2026-07-16.md` (committed to git).

**Structure:**

1. **Executive verdict** (single paragraph, above the fold): `TRUST` / `CONDITIONAL TRUST` / `DO NOT PUBLISH` with a one-sentence reason.
2. **Data provenance:** snapshot timestamp, DB size, sample count, filter applied.
3. **Q1–Q8 sections:** each contains the number(s), an ASCII chart where helpful, and a one-line interpretation.
4. **Findings:** bulleted list of what the audit revealed — both confirmatory and concerning.
5. **Recommended actions:** concrete changes to make before Phase 2 (sealed forward-test) launches. Examples might include: raise display confidence threshold, exclude a leaky market, fix an odds-capture bug, add a data-quality gate on ingestion.

### Reproducible script

**Path:** `docs/audit/roi-audit-2026-07-16.py` — self-contained Python script (pandas + numpy, no Django ORM dependency, reads from the sqlite snapshot). Anyone can re-run it on a fresh snapshot to regenerate the report.

## 5. Explicit non-goals — what this audit will NOT answer

Documented so we do not overclaim from the results:

- **Odds achievability** — we log a specific bookmaker's odds at fixture-fetch time. This audit cannot verify that a real user could actually place a bet at those odds 30 minutes before kickoff. That question requires historical odds-drift snapshots we may not currently store.
- **Real-world friction** — no accounting for bookmaker limits or bans on winning accounts, minimum stake constraints, currency conversion, tax on winnings.
- **Prospective validity** — everything is retrospective. Even a perfectly clean audit does not prove the *future* will look the same. That is exactly what Phase 2 (sealed forward-test) is designed to answer, and is the reason it must exist regardless of Phase 1's result.
- **Model quality attribution** — the audit measures the pipeline's output, not which model / signal / feature is producing the edge. That is a separate model-attribution study.

## 6. Success criteria for the spec itself

- Audit runs end-to-end in a single session (~2 hours).
- Report is committed to git with all numbers, no placeholders.
- Reproducible script re-runs on demand.
- Verdict is unambiguous — Andrei can make a go/no-go decision on Phase 2 without needing to re-interpret the data.

## 7. Risks to the audit process

- **Snapshot staleness** — DB state at snapshot time is frozen; new picks resolved after that point are not counted. Acceptable — the snapshot timestamp is recorded and the audit can be re-run.
- **Sample too small for meaningful CI** — Q1 might reveal the total is under ~100 bets, in which case Q2–Q8 answers become directionally informative but statistically weak. The verdict handles this: `DO NOT PUBLISH` with reason "sample too small; re-audit after N more bets."
- **Discovering a bug mid-audit** — e.g., Q8 reveals odds are being stored wrong. If so, audit pauses, bug is fixed, DB is re-processed if possible, audit re-runs. Prevents publishing on top of a broken pipeline.

## 8. Next step after user approval

Invoke `superpowers:writing-plans` to produce a step-by-step execution plan (which queries to run in what order, how outputs get combined into the final report, checkpoints for early-exit).
