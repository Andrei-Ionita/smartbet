# Home Win Diagnostic Summary

## Problem Statement
Our LightGBM model achieves only 53.5% precision on Home Win predictions, below the 60% threshold needed for profitable betting.

## Key Findings

### Confusion Matrix Results
- Total Home Win predictions: 114/177 matches (64.4%)
- Correct predictions: 61 (53.5% precision)
- False positives: 53 (46.5%)
  - 29 Away wins predicted as Home (54.7% of false positives)
  - 24 Draws predicted as Home (45.3% of false positives)

### Performance Metrics
- Home Win Precision: 53.5% (POOR)
- Home Win Recall: 81.3% (EXCELLENT)
- Away Win Precision: 61.9% (GOOD)
- Overall Accuracy: 56.5%

### SHAP Analysis
**Top features for TRUE POSITIVE home wins:**
1. home_big_club (0.163)
2. prob_ratio_home_draw (0.070)
3. away_team_frequency (0.066)

**Top features for FALSE POSITIVE home wins:**
1. home_big_club (0.099)
2. away_team_frequency (0.080)
3. prob_ratio_home_draw (0.063)

**Critical Issue:** Model over-relies on team reputation (home_big_club)

### Odds Bucket Analysis
- Very Low odds: 52.7% precision (91 predictions)
- Medium odds: 100.0% precision (1 prediction) ⭐
- Very High odds: 60.0% precision (5 predictions)

### Time Trend
- January 2025: 35.3% precision
- May 2025: 60.0% precision
- Improvement: +5.7% per month (POSITIVE TREND)

## Root Causes

1. **Over-aggressive threshold** - Predicts home wins too frequently
2. **Team reputation bias** - Over-relies on big club status
3. **Missing home advantage factors** - No venue-specific features
4. **Draw confusion** - Cannot distinguish close games

## Immediate Recommendations

### 1. Adjust Prediction Thresholds
- Increase home win confidence threshold to 60%
- Reduce false positive rate

### 2. Selective Betting Strategy
- AVOID home win bets with current model
- FOCUS on away wins (61.9% precision)
- Only bet Medium/Very High odds buckets for homes

### 3. Feature Engineering
- Add venue-specific factors
- Include recent home form (last 5 home games)
- Reduce reliance on team reputation

## Expected Improvements
- Target precision: 65%+
- Reduce false positives by 50%
- Maintain high recall (80%+)

## Conclusion
Model has strong foundation (high recall, improving trend) but needs calibration to reduce false positives. Focus on threshold adjustment and feature engineering rather than complete rebuild. 