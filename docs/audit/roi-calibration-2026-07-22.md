# ROI Calibration Report — 2026-07-22

**Overall verdict:** `DO_NOT_APPLY`. Display: `DO_NOT_APPLY`. Kelly sizing: `DO_NOT_APPLY`. Filter re-selection: `DO_NOT_APPLY`.

---

## Data provenance

- Snapshot file: `docs/audit/snapshot-2026-07-16.sqlite` (319,488 bytes)
- Universe size: 252 rows (over_under_2.5, recommended, resolved)
- Report generated at: 2026-07-23 06:41 UTC
- Same snapshot as prior audit and tuning; post-backfill state.
- Fitted Platt (full-sample): `sigmoid(4.980 * confidence + -2.718)`

---

## Global calibration (5-fold CV)

**Fitted Platt (full-sample):** `sigmoid(4.980 * confidence + -2.718)`

**Brier score:** 0.2405 -> 0.2419 (-0.6% relative)

**ECE:** 0.0599 (CI 0.0165 -> 0.1217) -> 0.0133 (CI 0.0098 -> 0.0836)  (+77.8% relative)

### Reliability diagram

**Pre-calibration (raw confidence)**

```
  bin_lo  bin_hi   n     mean_pred   mean_actual   gap
   0.00   0.10    0     n/a         n/a           n/a
   0.10   0.20    0     n/a         n/a           n/a
   0.20   0.30    0     n/a         n/a           n/a
   0.30   0.40    0     n/a         n/a           n/a
   0.40   0.50    0     n/a         n/a           n/a
   0.50   0.60   50   0.584        0.640       -0.056
   0.60   0.70  198   0.632        0.576       +0.056
   0.70   0.80    4   0.707        1.000       -0.293
   0.80   0.90    0     n/a         n/a           n/a
   0.90   1.00    0     n/a         n/a           n/a
```

**Post-calibration (held-out CV)**

```
  bin_lo  bin_hi   n     mean_pred   mean_actual   gap
   0.00   0.10    0     n/a         n/a           n/a
   0.10   0.20    0     n/a         n/a           n/a
   0.20   0.30    0     n/a         n/a           n/a
   0.30   0.40    0     n/a         n/a           n/a
   0.40   0.50    3   0.488        0.667       -0.178
   0.50   0.60  156   0.575        0.564       +0.011
   0.60   0.70   92   0.632        0.641       -0.009
   0.70   0.80    1   0.728        1.000       -0.272
   0.80   0.90    0     n/a         n/a           n/a
   0.90   1.00    0     n/a         n/a           n/a
```
## Segmentation heatmap

**By confidence bucket**

```
  segment                       n     pred_pre  actual   gap_pre   pred_post  gap_post   underpowered
  0.55-0.60                      49    0.584     0.633  -0.049    0.548    -0.085   False
  0.60-0.70                     199    0.632     0.578  +0.054    0.606    +0.028   False
  0.70-0.80                       4    0.707     1.000  -0.293    0.679    -0.321    True *
  0.80-1.00                       0     n/a       n/a      n/a       n/a         n/a       yes
```

**By league (top 5 by volume)**

```
  segment                       n     pred_pre  actual   gap_pre   pred_post  gap_post   underpowered
  Eredivisie                     33    0.642     0.636  +0.005    0.616    -0.020   False
  Serie B                        22    0.612     0.455  +0.157    0.578    +0.123   False
  Bundesliga                     21    0.645     0.714  -0.069    0.616    -0.098   False
  La Liga 2                      16    0.600     0.562  +0.038    0.578    +0.016   False
  Super League                   16    0.632     0.750  -0.118    0.599    -0.151   False
```

**By time period (chronological halves)**

```
  segment                       n     pred_pre  actual   gap_pre   pred_post  gap_post   underpowered
  first half (older)            126    0.626     0.571  +0.055    0.598    +0.026   False
  second half (newer)           126    0.621     0.619  +0.002    0.593    -0.026   False
```
## Per-target verdicts

- **Display:** `DO_NOT_APPLY` — Brier -0.6% (need >= 5%), ECE +77.8% (need >= 30%).
- **Kelly sizing:** `DO_NOT_APPLY` — Brier improvement -0.6% < 5%.
- **Filter re-selection:** `DO_NOT_APPLY` — Re-filtered ROI -0.88% vs current +4.34% (delta -5.22pp < 2pp).
  - Current subset ROI: +4.34%
  - Re-filtered ROI: -0.88% (n=228, CI_lo -13.06%)

### Overall verdict: `DO_NOT_APPLY`


## Recommended next step

No production changes recommended. The model is either well-calibrated on this slice or calibration would not improve the targets we care about. Revisit at n≥500 if the situation changes.

**Filter target actively worsens ROI** (-5.22pp): applying Platt-in-the-loop for selection would push out the 0.55-0.60 confidence bucket (currently the platform's best empirical bucket). Do NOT attempt calibrated-threshold filtering until either (a) that bucket has enough n to fit a shape that respects its high empirical rate, or (b) a non-parametric calibrator (isotonic at n>=500) is available.

---

## Methodology notes

**Platt implementation deviation from canonical (1999):** this study fits Platt using `sklearn.linear_model.LogisticRegression(C=1e10)` on raw binary targets. Canonical Platt (Platt, 1999) trains on Bernoulli-smoothed targets `y+ = (N+ + 1) / (N+ + 2)` and `y- = 1 / (N- + 2)` to prevent overfitting at small `n`; `sklearn.calibration.CalibratedClassifierCV(method='sigmoid')` implements this smoothing. At `n=252` the effect is small, but the fitted `(a, b)` may differ marginally from a canonical Platt fit — particularly in extreme bins where the empirical rate is 0.0 or 1.0 (here: the 0.70–0.80 bucket, `actual=1.000` on n=4).

---

## Non-goals (this study does NOT test)

- Production code changes (deployment triggered by APPLY verdict gets a separate spec).
- Retraining SportMonks' underlying model (impossible).
- Modifying form-momentum or value-zone adjustments (calibration wraps them).
- Per-league or per-time-period separate calibrators (segmentation is diagnostic only).
- Multiple calibrator methods (Platt only; isotonic and beta explicitly out of scope).
- 1x2 / BTTS / DC calibration (combined n=~23 insufficient).
- Prospective forward-test.

---

*Report generated by `docs/audit/roi-calibration-2026-07-22.py`. Re-run against a fresh snapshot to regenerate.*
