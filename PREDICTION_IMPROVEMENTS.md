# BetGlitch Prediction System: Analysis & Improvement Proposal

**Author:** Andrei Ionita
**Date:** April 17, 2026
**Branch:** `experiment/prediction-improvements`

---

## Table of Contents

1. [Current System Analysis](#1-current-system-analysis)
2. [Identified Weaknesses](#2-identified-weaknesses)
3. [Proposed Improvements](#3-proposed-improvements)
4. [Implementation Details](#4-implementation-details)
5. [Expected Impact](#5-expected-impact)
6. [Implementation Plan](#6-implementation-plan)

---

## 1. Current System Analysis

### 1.1 Architecture Overview

BetGlitch does **not** train its own ML models. The prediction pipeline is:

```
SportMonks Predictions API (3 AI models: type_ids 233, 237, 238)
    │
    ├── Fetched per fixture for 27 European leagues
    │
    ▼
Consensus Ensemble (simple average of 3 models)
    │
    ├── Average probabilities for Home/Draw/Away
    ├── Select outcome with highest average probability
    ├── Calculate confidence = highest average probability
    │
    ▼
Multi-Market Selection (best market across 1X2, BTTS, O/U 2.5, DC)
    │
    ├── MarketScore = (prob_gap × 0.4) + (EV × 0.3) + (confidence × 0.3)
    │
    ▼
Quality Filtering (PredictionEnhancer)
    │
    ├── Confidence floor: 60% for Safe Bets, 35%+ with 10% EV for Value Bets
    ├── Max odds: 2.50 (hard cap)
    ├── League blacklist: Admiral Bundesliga, Liga Portugal, Super Lig
    ├── Quality score (0-100): confidence + EV + odds range + prob gap + variance + outcome penalties
    │
    ▼
Top 10 Recommendations → Frontend
```

### 1.2 SportMonks Models Used

| Type ID | Market | Outcomes |
|---------|--------|----------|
| 233 | 1X2 (Match Result) | Home / Draw / Away |
| 237 | 1X2 (Match Result) | Home / Draw / Away |
| 238 | 1X2 (Match Result) | Home / Draw / Away |
| 231 | BTTS | Yes / No |
| 235 | Over/Under 2.5 | Over / Under |
| 239 | Double Chance | 1X / X2 / 12 |

Additional types available but currently unused: 232 (Grid), 234/236 (BTTS variants), 240 (Exact Score), 326-334 (Goal markets), 1679-1690 (Advanced goal predictions).

### 1.3 How Predictions Are Combined

**Current method: Simple arithmetic average (equal weights)**

```
avg_home = (model_233.home + model_237.home + model_238.home) / 3
avg_draw = (model_233.draw + model_237.draw + model_238.draw) / 3
avg_away = (model_233.away + model_237.away + model_238.away) / 3
```

All three models contribute equally regardless of their individual accuracy.

### 1.4 Current Filtering Thresholds

| Parameter | Value | Source |
|-----------|-------|--------|
| Confidence floor (Safe) | 60% | `prediction_enhancer.py` |
| Confidence floor (Value) | 35% + 10% EV | `prediction_enhancer.py` |
| Max odds | 2.50 | Data-driven (Feb 2026, 46 predictions) |
| Min probability gap (1X2) | 12% | `recommendations/route.ts` |
| Min probability gap (Draw) | 15% | `recommendations/route.ts` |
| Min EV for recommendation | 5% | `recommendations/route.ts` |
| Market score threshold | 0.15 | `recommendations/route.ts` |

### 1.5 Quality Score Formula (V1)

| Factor | Points | Condition |
|--------|--------|-----------|
| Confidence | 0-40 | 70%+=40, 65%+=30, 60%+=20, 55%+=10 |
| Expected Value | 0-25 | 25%+=25, 20%+=20, 15%+=15, 10%+=10, 5%+=5 |
| Odds range | -10 to 15 | 1.6-2.5=15, 1.4-3.0=10, >3.5=-10 |
| Probability gap | 0-15 | 40%+=15, 25%+=12, 20%+=5 |
| Variance | 0-10 | <0.1=10, <0.2=5 |
| Under penalty | -10 | If predicted Under 2.5 |
| Over bonus | +5 | If predicted Over 2.5 |
| League blacklist | -15 | Admiral Bundesliga, Liga Portugal, Super Lig |
| League watchlist | -5 | Eredivisie, Pro League |

### 1.6 EV Calculation

```
EV = (win_probability × decimal_odds) - 1
```

EV > 0 means the predicted probability exceeds what the odds imply, suggesting a value bet.

### 1.7 Data-Driven Insights (from Feb 2026 analysis of 46 recommended predictions)

- **Under 2.5 accuracy: 41.7%** vs Over 2.5: **77.4%**
- Probability gap ≥25% → **83.3% accuracy**
- Admiral Bundesliga / Liga Portugal / Super Lig → **0% accuracy** in recommendations
- Incorrect predictions had average odds of **3.20** vs correct at **2.19**

---

## 2. Identified Weaknesses

### 2.1 Equal Model Weighting

**Problem:** All three SportMonks models (233, 237, 238) are averaged with equal weight. If model 237 is consistently more accurate than 233, we're diluting its signal.

**Evidence:** The system has no mechanism to track individual model accuracy. The `model_count` and `variance` fields in PredictionLog store aggregate metadata but don't map predictions back to specific models.

**Impact:** Estimated 2-5% accuracy improvement from proper model weighting based on literature on ensemble methods.

### 2.2 One-Size-Fits-All Thresholds

**Problem:** The same 60% confidence threshold applies to all 27 leagues, despite massive accuracy variation:
- Premier League predictions may be highly reliable at 55%
- Super Lig predictions are unreliable even at 70%

**Evidence:** League-specific accuracy analysis shows a range from 0% to >70% accuracy across leagues at the same confidence threshold.

**Impact:** We're likely over-filtering strong leagues (missing good picks) and under-filtering weak leagues (including bad picks).

### 2.3 Hard Odds Cap Too Aggressive

**Problem:** The 2.50 max odds cap was set based on 46 predictions from Feb 2026. This is a very small sample size for such a significant filter.

**Evidence:** The odds range 2.50-3.50 likely contains legitimate value bets with moderate risk that are being completely excluded. The analysis showed accuracy "collapses" above 2.50, but with only 46 data points, this could be noise.

**Impact:** Excluding all odds >2.50 removes potential value bets, particularly in markets where underdogs offer genuine edges.

### 2.4 Draw Prediction Weakness

**Problem:** Draw predictions are not penalized enough in the recommendation pipeline. Draws are inherently harder to predict (3-way market with ~28% base rate).

**Evidence:** The V1 enhancer applies only a -10 score penalty for Under 2.5 but doesn't apply a similar penalty for draw predictions in 1X2.

**Impact:** Draw predictions likely pull down overall accuracy.

### 2.5 No Market-Specific Strategy

**Problem:** All markets (1X2, BTTS, O/U 2.5, Double Chance) use the same filtering logic and quality scoring, despite having fundamentally different characteristics:
- 1X2: 3 outcomes, hardest to predict, draws are the weak link
- BTTS/O-U: 2 outcomes, ~50% base rate, easier to achieve edge
- Double Chance: 2-of-3 coverage, high probability but low odds

**Impact:** A prediction that's excellent for Double Chance might be mediocre for 1X2, but both get the same score.

### 2.6 Under 2.5 Goals Still Recommended

**Problem:** Despite 41.7% accuracy, Under 2.5 predictions can still be recommended as "Value Bets" if EV ≥ 10%.

**Evidence:** Historical data shows Under 2.5 is the worst performing prediction type. The -10 quality score penalty isn't enough if the base score is high.

**Impact:** Continued losses on Under 2.5 bets drag down overall ROI.

### 2.7 No Stale Model Detection

**Problem:** If one of SportMonks' three models starts performing poorly (model drift, data issues), we have no mechanism to detect or compensate.

**Evidence:** No monitoring exists for individual model accuracy over time.

**Impact:** A degraded model would pollute the consensus for weeks/months before being noticed.

### 2.8 EV Zone Not Aggressive Enough

**Problem:** The current system applies some EV zone filtering but still recommends predictions with suspiciously high EV values (>30%) which typically indicate odds errors rather than genuine value.

**Evidence:** V1's `evaluateValueZone()` in the frontend applies mild penalties. Very high EV predictions have historically performed worse than moderate EV.

### 2.9 No Time-to-Kickoff Signal

**Problem:** Predictions made 7 days before kickoff are treated identically to those made 2 hours before. Closer to kickoff, more information is available (lineups, injuries, weather).

**Impact:** Early predictions have higher uncertainty but no confidence adjustment.

### 2.10 Calibration Issues

**Problem:** The system doesn't verify that a "60% confidence" prediction actually wins 60% of the time. If 60% confidence picks win 75% of the time, we're under-confident (leaving money on the table). If they win 45%, we're over-confident (losing money).

**Evidence:** The `analyze_prediction_patterns.py` command has calibration analysis, but the results don't feed back into the prediction system.

---

## 3. Proposed Improvements

### 3.1 Dynamic Model Weighting (High Impact)

**What:** Track each SportMonks model's accuracy over a rolling 60-day window and weight them proportionally.

**How:**
```python
# Instead of:
avg_home = (m233.home + m237.home + m238.home) / 3

# Use:
weights = {233: 1.2, 237: 0.9, 238: 0.9}  # Based on accuracy
weighted_home = (m233.home * w233 + m237.home * w237 + m238.home * w238) / sum_weights
```

**Expected Impact:** +2-5% accuracy improvement. Even small weighting adjustments compound over hundreds of predictions.

**Implementation:** `ModelPerformanceTracker` class in `prediction_enhancer_v2.py`.

### 3.2 League-Specific Calibration (High Impact)

**What:** Group leagues into performance tiers with different confidence thresholds.

| Tier | Leagues | Min Confidence | Min EV |
|------|---------|---------------|--------|
| Tier 1 (Strong) | PL, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie | 58% (global) | 5% |
| Tier 2 (Moderate) | Championship, Serie B, La Liga 2, Ekstraklasa, etc. | 62% | 8% |
| Tier 3 (Weak) | Admiral Bundesliga, Liga Portugal, Super Lig, etc. | 68% | 12% |
| Cups | FA Cup, Copa Del Rey, Coppa Italia, etc. | 65% | 10% |

**Expected Impact:** +3-7% accuracy improvement on aggregate by avoiding bad bets in weak leagues while capturing more good bets in strong leagues.

**Implementation:** `LeagueCalibrator` class in `prediction_enhancer_v2.py`.

### 3.3 Market-Specific Strategies (Medium Impact)

**What:** Different quality scoring weights and thresholds per market type.

| Market | Min Gap | Key Adjustment |
|--------|---------|----------------|
| 1X2 | 12% | Draw penalty (-8%), higher bar |
| BTTS | 15% | Higher EV weight |
| O/U 2.5 | 15% | Under penalty (-10%) |
| Double Chance | 8% | Higher confidence weight |

**Expected Impact:** +1-3% per market by tailoring scoring to market characteristics.

**Implementation:** `MarketStrategy` class in `prediction_enhancer_v2.py`.

### 3.4 Three-Tier Bet Classification (Medium Impact)

**What:** Replace the binary Safe/Value classification with Premium/Safe/Value tiers.

| Tier | Criteria | Expected Accuracy |
|------|----------|------------------|
| Premium | Confidence ≥68%, EV ≥10%, Quality ≥60 | 75%+ |
| Safe | Confidence ≥ league threshold, Quality ≥35 | 60-75% |
| Value | EV ≥ league threshold, Confidence ≥42%, Quality ≥25 | 45-60% |

**Expected Impact:** Better user guidance on stake sizing. Premium picks deserve larger stakes; Value picks should be smaller.

### 3.5 Relaxed but Smarter Odds Cap (Medium Impact)

**What:** Replace the hard 2.50 cap with market-specific caps and a graduated penalty system.

| Market | Max Odds | Rationale |
|--------|----------|-----------|
| 1X2 | 3.50 | Allows moderate underdogs |
| BTTS | 2.50 | Binary market, less variance |
| O/U 2.5 | 2.80 | Moderate range |
| DC | 2.00 | Low odds by nature |

**Expected Impact:** Captures 10-20% more genuine value bets that were incorrectly excluded.

### 3.6 Stale Model Detection (Low-Medium Impact)

**What:** Monitor each model's rolling accuracy and flag/downweight models performing worse than random (< 35% for 1X2).

**How:** When a model is flagged as stale, reduce its weight to 0.3× in the ensemble.

**Expected Impact:** Prevents catastrophic accuracy drops when a model degrades. Insurance policy.

### 3.7 Time-to-Kickoff Decay (Low Impact)

**What:** Apply a small quality multiplier based on when the prediction is being served.

| Hours to Kickoff | Multiplier | Reason |
|-----------------|------------|--------|
| < 2 hours | 1.05× | Lineups confirmed |
| 2-6 hours | 1.02× | Most info available |
| 6-24 hours | 1.00× | Normal |
| 24-72 hours | 0.97× | Some uncertainty |
| > 72 hours | 0.93× | High uncertainty |

### 3.8 Improved EV Zone Filtering (Low Impact)

**What:** More aggressive penalties for suspiciously high EV.

| EV Range | Adjustment |
|----------|------------|
| 3-18% | No adjustment (optimal zone) |
| 18-30% | -8% EV, small score penalty |
| 30-50% | -20% EV, moderate penalty |
| 50%+ | Cap at 20%, heavy penalty |

---

## 4. Implementation Details

### 4.1 New Files Created

| File | Purpose |
|------|---------|
| `core/services/prediction_enhancer_v2.py` | Enhanced prediction filtering and scoring |
| `scripts/analyze_predictions.py` | Backtesting and comparison tool |
| `PREDICTION_IMPROVEMENTS.md` | This document |

### 4.2 Key Classes

**`ModelPerformanceTracker`** — Tracks per-model accuracy with exponential decay weighting over a rolling window. Calculates performance-based model weights.

**`LeagueCalibrator`** — Maps leagues to performance tiers and provides league-specific confidence/EV thresholds.

**`MarketStrategy`** — Contains market-specific scoring weights, penalties, and minimum thresholds for each betting market type.

**`PredictionEnhancerV2`** — Main enhancer class combining all improvements. Drop-in replacement for V1 with a `compare_with_v1()` method for A/B testing.

### 4.3 No Production Files Modified

All changes are additive — the existing `prediction_enhancer.py` is untouched. V2 can run alongside V1 for comparison.

### 4.4 Backtesting Script

`scripts/analyze_predictions.py` supports three data sources:
1. **Database:** Loads from `PredictionLog` (requires Django)
2. **CSV:** Loads from `analysis_export.csv` or specified path
3. **Simulated:** Generates realistic synthetic data for testing

The script simulates both V1 and V2 filtering on every historical prediction and compares accuracy, ROI, volume, and per-league/per-market breakdowns.

---

## 5. Expected Impact

### 5.1 Conservative Estimates

| Improvement | Accuracy Delta | ROI Delta | Confidence |
|-------------|---------------|-----------|------------|
| Model weighting | +2-5% | +3-8% | Medium (needs data) |
| League calibration | +3-7% | +5-10% | High |
| Market strategies | +1-3% | +2-5% | Medium |
| Odds cap relaxation | Neutral | +3-6% | Medium |
| Stale model detection | 0% (insurance) | 0% (insurance) | Low |
| Time decay | +0.5-1% | +1-2% | Low |
| **Combined** | **+5-12%** | **+8-15%** | **Medium** |

### 5.2 Risk Assessment

- **Low risk:** All changes are additive. V1 remains untouched.
- **Reversible:** V2 can be disabled instantly by switching back to V1.
- **Testable:** The `compare_with_v1()` method enables A/B comparison on every prediction.
- **Data-dependent:** Model weighting requires historical data accumulation (30+ predictions per model).

### 5.3 Volume Impact

V2 is expected to:
- **Accept 10-20% more** predictions overall (due to relaxed odds cap and league-specific thresholds)
- **Reject** predictions from weak leagues that V1 currently allows
- **Capture** value bets in the 2.50-3.50 odds range that V1 excludes

---

## 6. Implementation Plan

### Phase 1: Shadow Mode (Week 1-2)

1. Deploy `prediction_enhancer_v2.py` alongside V1
2. Run both V1 and V2 on every prediction
3. Log V2 decisions in parallel (add `v2_should_recommend`, `v2_quality_score`, `v2_bet_type` to PredictionLog or a separate table)
4. Compare V1 vs V2 decisions after 2 weeks of data

### Phase 2: A/B Testing (Week 3-4)

1. Show V2 recommendations to a subset of users
2. Track engagement metrics (click-through, actual betting behavior)
3. Compare accuracy of V2-recommended vs V1-recommended predictions

### Phase 3: Gradual Rollout (Week 5-6)

1. If V2 outperforms: gradually increase V2 traffic
2. Keep V1 as fallback
3. Monitor daily for regression

### Phase 4: Full Deployment (Week 7+)

1. Switch primary recommendation engine to V2
2. Keep V1 code for reference/fallback
3. Begin model weight accumulation
4. Schedule monthly review of league tiers

### Integration Points

To fully deploy V2 in production, these files would need updates (NOT done in this branch):

| File | Change Needed |
|------|--------------|
| `smartbet-frontend/app/api/recommendations/route.ts` | Use weighted consensus instead of simple average |
| `core/api_views.py` | Import V2 enhancer instead of V1 |
| `core/models.py` | Add V2-specific fields (optional) |
| `core/management/commands/log_predictions_batch.py` | Log V2 metadata |
| `core/management/commands/mark_recommended_predictions.py` | Use V2 scoring |

---

## Appendix A: SportMonks Type IDs Reference

| ID | Market | Notes |
|----|--------|-------|
| 233 | 1X2 Model A | Currently used |
| 237 | 1X2 Model B | Currently used |
| 238 | 1X2 Model C | Currently used |
| 231 | BTTS | Currently used |
| 235 | O/U 2.5 | Currently used |
| 239 | Double Chance | Currently used |
| 232 | Grid (complex) | Not used |
| 234, 236 | BTTS variants | Not used |
| 240 | Exact Score | Not used — could add for entertainment |
| 326-334 | Goal markets | Not used — potential future expansion |
| 1679-1690 | Advanced goals | Not used |

## Appendix B: League Coverage (27 Leagues)

| ID | League | Tier (V2) |
|----|--------|-----------|
| 8 | Premier League | Tier 1 |
| 564 | La Liga | Tier 1 |
| 384 | Serie A | Tier 1 |
| 82 | Bundesliga | Tier 1 |
| 301 | Ligue 1 | Tier 1 |
| 72 | Eredivisie | Tier 1 |
| 9 | Championship | Tier 2 |
| 387 | Serie B | Tier 2 |
| 567 | La Liga 2 | Tier 2 |
| 453 | Ekstraklasa | Tier 2 |
| 271 | Superliga | Tier 2 |
| 244 | 1. HNL | Tier 2 |
| 501 | Premiership | Tier 2 |
| 573 | Allsvenskan | Tier 2 |
| 444 | Eliteserien | Tier 2 |
| 208 | Pro League | Tier 2 |
| 181 | Admiral Bundesliga | Tier 3 |
| 462 | Liga Portugal | Tier 3 |
| 600 | Super Lig | Tier 3 |
| 486 | Russian Premier League | Tier 3 |
| 591 | Super League | Tier 3 |
| 24 | FA Cup | Cups |
| 27 | Carabao Cup | Cups |
| 570 | Copa Del Rey | Cups |
| 390 | Coppa Italia | Cups |
| 1371 | UEFA Europa League Play-offs | Cups |
