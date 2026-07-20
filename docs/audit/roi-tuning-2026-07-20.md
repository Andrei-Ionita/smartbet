# ROI Tuning Report — 2026-07-20

**Executive verdict:** SHIP — 2 experiment(s) reached the ship bar: ['E4', 'E5']. Proposed production changes: 2 item(s) below.

---

## Data provenance

- Snapshot file: `docs/audit/snapshot-2026-07-16.sqlite` (319,488 bytes)
- Universe size: 275 rows
- Report generated at: 2026-07-20 18:27 UTC
- Same snapshot as `docs/audit/roi-audit-2026-07-16.md`, post-backfill.

---

## E1 - Confidence threshold sweep

**Hypothesis:** current `>= 0.60` filter is not optimal; the 0.55-0.60 bucket carries edge that is currently discarded.

```
  threshold   n     ROI       CI_lo    CI_hi    verdict
   0.50    270   +3.66%   -7.68%  +15.23%  INVESTIGATE
   0.51    270   +3.66%   -7.68%  +15.23%  INVESTIGATE
   0.52    269   +4.05%   -7.13%  +15.92%  INVESTIGATE
   0.53    269   +4.05%   -7.13%  +15.92%  INVESTIGATE
   0.54    267   +4.83%   -6.27%  +16.57%  INVESTIGATE
   0.55    267   +4.83%   -6.27%  +16.57%  INVESTIGATE
   0.56    267   +4.83%   -6.27%  +16.57%  INVESTIGATE
   0.57    257   +3.87%   -7.61%  +15.64%  INVESTIGATE
   0.58    247   +2.88%   -8.70%  +14.24%  DISCARD
   0.59    226   +0.14%  -11.83%  +11.90%  DISCARD
   0.60    210   -1.98%  -14.02%  +10.25%  DISCARD
   0.61    170   -2.59%  -16.05%  +10.74%  DISCARD
   0.62    129   -5.12%  -19.26%   +8.83%  DISCARD
   0.63     93   -2.99%  -18.51%  +12.78%  DISCARD
   0.64     67   -6.82%  -23.43%   +9.17%  DISCARD
   0.65     51   -2.91%  -21.33%  +15.04%  DISCARD
   0.66     33   +0.42%  -21.74%  +21.12%  DISCARD
   0.67     21  +10.74%  -15.00%  +31.48%  INVESTIGATE
   0.68     14  +26.89%   +5.68%  +39.64%  INVESTIGATE
   0.69      7  +18.00%  -22.43%  +41.14%  INVESTIGATE
   0.70      4  +35.62%  +29.75%  +39.37%  INVESTIGATE
   0.71      1  +27.00%  +27.00%  +27.00%  INVESTIGATE
   0.72      0     n/a       n/a      n/a      DISCARD
   0.73      0     n/a       n/a      n/a      DISCARD
   0.74      0     n/a       n/a      n/a      DISCARD
   0.75      0     n/a       n/a      n/a      DISCARD
```

## E2 - EV shrinkage factor sweep

**Hypothesis:** model's EV is ~20 pp too optimistic; shrinkage factor before the `ev >= 0.05` filter keeps only genuinely-value picks.

```
  factor   n     ROI       CI_lo    CI_hi    verdict
  0.50   252   +4.66%   -7.08%  +16.67%  INVESTIGATE
  0.55   257   +4.63%   -7.18%  +16.37%  INVESTIGATE
  0.60   258   +4.96%   -6.76%  +16.78%  INVESTIGATE
  0.65   265   +2.91%   -8.99%  +14.76%  DISCARD
  0.70   265   +2.91%   -8.99%  +14.76%  DISCARD
  0.75   268   +2.44%   -9.11%  +13.95%  DISCARD
  0.80   270   +2.95%   -8.36%  +14.31%  DISCARD
  0.85   270   +2.95%   -8.36%  +14.31%  DISCARD
  0.90   271   +3.22%   -8.17%  +14.74%  INVESTIGATE
  0.95   272   +2.84%   -8.57%  +14.01%  DISCARD
  1.00   275   +2.98%   -8.23%  +14.28%  DISCARD
```

## E3 - League blacklist/whitelist

**Hypothesis:** a few leagues drag overall ROI down; removing them lifts total edge.

**Per-league (n >= 15):**

```
  league                        n     ROI       CI_lo    CI_hi    category
  Eredivisie                     33   +3.56%  -26.27%  +34.52%  neutral
  Serie B                        24  -18.94%  -55.42%  +17.46%  neutral
  Bundesliga                     21   +2.50%  -27.93%  +31.98%  neutral
  La Liga 2                      20   +8.05%  -41.75%  +62.93%  neutral
  La Liga                        17  +19.32%  -29.82%  +70.94%  neutral
  Premier League                 16  -22.75%  -66.25%  +21.50%  neutral
  Super League                   16  +22.53%  -18.28%  +65.53%  neutral
  Eliteserien                    15  -28.10%  -67.80%  +10.43%  neutral
```

**Scenarios:**

```
  scenario                                n     ROI       CI_lo    CI_hi    verdict
  current                                 275   +2.98%   -8.23%  +14.28%  DISCARD
  blacklist_applied (0 leagues removed)   275   +2.98%   -8.23%  +14.28%  DISCARD
  whitelist_only (0 leagues kept)           0    +nan%    +nan%    +nan%  DISCARD
```

## E4 — Market × confidence 2D grid

**Hypothesis:** edge lives in specific market-confidence combinations, not uniformly.

```
  market            bucket        n     ROI       CI_lo    CI_hi    verdict
  1x2               0.55–0.60     2  +93.50%  +77.00%  +110.00%  INVESTIGATE
  1x2               0.60–0.70     4   -3.75%  -100.00%  +92.50%  DISCARD
  1x2               0.70–0.80     0     n/a       n/a      n/a      DISCARD
  1x2               0.80–1.00     0     n/a       n/a      n/a      DISCARD
  btts              0.55–0.60     6   -4.50%  -68.67%  +60.83%  DISCARD
  btts              0.60–0.70     3  +16.33%  -100.00%  +83.00%  INVESTIGATE
  btts              0.70–0.80     0     n/a       n/a      n/a      DISCARD
  btts              0.80–1.00     0     n/a       n/a      n/a      DISCARD
  over_under_2.5    0.55–0.60    49  +31.50%   +1.36%  +63.02%  SHIP
  over_under_2.5    0.60–0.70   199   -2.97%  -15.45%   +9.59%  DISCARD
  over_under_2.5    0.70–0.80     4  +35.62%  +29.75%  +39.37%  INVESTIGATE
  over_under_2.5    0.80–1.00     0     n/a       n/a      n/a      DISCARD
  double_chance     0.55–0.60     0     n/a       n/a      n/a      DISCARD
  double_chance     0.60–0.70     0     n/a       n/a      n/a      DISCARD
  double_chance     0.70–0.80     0     n/a       n/a      n/a      DISCARD
  double_chance     0.80–1.00     0     n/a       n/a      n/a      DISCARD
```

## E5 — Kelly stake sizing simulation

**Hypothesis:** flat $10 stakes leave value on the table; Kelly-optimal fractional stakes capture more.

- Starting bankroll: $1000.00
- Bets simulated: 275
- **Flat $10:** final $1081.85, max drawdown 20.3%
- **Kelly (k=0.25):** final $6932.01, max drawdown 39.6%
- Kelly vs Flat improvement: +540.75%

### E5 recommendation: SHIP



## Combined recommendation

**SHIP experiments:** ['E4', 'E5']

**Proposed production changes:**

- E4: set per-market confidence thresholds {'over_under_2.5': 0.55}
- E5: change default stake sizing strategy to Kelly (k=0.25)

---

## Non-goals (this tuning does NOT test)

- Feature engineering (xG, lineups, injuries, referee, weather)
- New model IP (own trained model, ensemble with SportMonks)
- Reprocessing historical SportMonks responses
- New markets or leagues
- User-facing UI redesign
- Prospective forward-test (Phase 2 territory)

---

*Report generated by `docs/audit/roi-tuning-2026-07-20.py`. Re-run against a fresh snapshot to regenerate.*
