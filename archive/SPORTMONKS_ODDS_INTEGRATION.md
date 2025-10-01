# SportMonks Historical Odds Integration Pipeline

## Overview

This pipeline extracts comprehensive historical betting odds from the SportMonks API for all major betting markets and integrates them with your existing Premier League training dataset.

## 🎯 Supported Betting Markets

✅ **Fulltime Result (1X2)** - Match Winner: Home/Draw/Away  
✅ **Over/Under 2.5 Goals** - Total Goals Over/Under 2.5  
✅ **Both Teams To Score (BTTS)** - Yes/No  
✅ **Asian Handicap** - Line betting  
✅ **Correct Score** - Exact final score  
✅ **Double Chance** - 1X/X2/12 combinations  

## 📋 Prerequisites

1. **SportMonks API Account** with odds data access
2. **API Token** with sufficient quota
3. **Python Dependencies**: pandas, requests, python-dotenv
4. **Training Dataset** (your existing Premier League CSV file)

## 🔧 Setup

### 1. Environment Configuration

Create/update your `.env` file:
```bash
SPORTMONKS_TOKEN=your_sportmonks_api_token_here
# OR
SPORTMONKS_API_TOKEN=your_sportmonks_api_token_here
```

### 2. Install Dependencies

```bash
pip install pandas requests python-dotenv
```

## 🚀 Workflow

### Step 1: Test API Connection

Before running the full collection, test your API setup:

```bash
python test_sportmonks_odds.py
```

This will:
- ✅ Verify API token and connection
- 🔍 Discover available markets and bookmakers  
- 🎲 Test odds extraction on sample fixtures
- 💰 Check API quota and estimate costs

### Step 2: Collect Historical Odds

Run the main odds collection:

```bash
python sportmonks_odds_collector.py
```

**Interactive Options:**
- Choose number of fixtures to process (start small for testing)
- Automatic discovery of available markets/bookmakers
- Progressive logging and error handling

## 📊 Expected Results

### Data Enhancement

**Before:** 22 columns per fixture
```
fixture_id, home_team, away_team, date, home_goals, away_goals, etc.
```

**After:** 40+ columns per fixture
```
Original columns + odds features:
- 1x2_home_odds, 1x2_draw_odds, 1x2_away_odds
- 1x2_market_margin, 1x2_market_efficiency  
- over_under_25_over_odds, over_under_25_under_odds
- btts_yes_odds, btts_no_odds
- asian_handicap_home_odds, asian_handicap_away_odds
- double_chance_1x_odds, double_chance_x2_odds, double_chance_12_odds
- correct_score_available, correct_score_1_0_odds, etc.
- has_odds (availability flag)
```

### Coverage Expectations

- **Recent seasons (2020-2024):** 70-95% coverage
- **Older seasons (2014-2019):** 30-70% coverage  
- **Premium bookmakers:** Pinnacle, Bet365, Betfair prioritized
- **Market availability:** Varies by season and bookmaker

## 🎯 Bookmaker Priority

The system automatically selects the best available bookmaker for each market:

1. **Pinnacle** - Sharp bookmaker with efficient odds
2. **Bet365** - Comprehensive market coverage
3. **Betfair** - Exchange odds, often best value
4. **Marathonbet** - Good historical coverage
5. **William Hill** - Traditional bookmaker
6. **Unibet** - European coverage
7. **Ladbrokes** - UK traditional
8. **Betway** - Growing coverage

## 📁 Output Files

The pipeline generates several files with timestamps:

### 1. Raw Odds Data
`sportmonks_raw_odds_YYYYMMDD_HHMMSS.csv`
- Complete extracted odds data
- All markets, bookmakers, and outcomes
- Useful for detailed analysis

### 2. Enhanced Training Dataset  
`enhanced_training_with_odds_YYYYMMDD_HHMMSS.csv`
- Original training data + odds features
- Ready for ML model training
- Wide format with structured columns

### 3. Collection Summary
`sportmonks_collection_summary_YYYYMMDD_HHMMSS.json`
- Statistics and metadata
- Coverage percentages
- Market/bookmaker breakdown

### 4. Logs and Errors
- `sportmonks_odds_collection_YYYYMMDD_HHMMSS.log`
- `failed_fixtures_YYYYMMDD_HHMMSS.json` (if any failures)

## 🔧 Feature Engineering

### 1X2 Market Features
```python
1x2_home_odds          # Home win odds
1x2_draw_odds          # Draw odds  
1x2_away_odds          # Away win odds
1x2_home_prob          # Implied probability (if available)
1x2_draw_prob          # Implied probability (if available)
1x2_away_prob          # Implied probability (if available)
1x2_market_margin      # Bookmaker margin (overround)
1x2_market_efficiency  # Market efficiency (1 / (1 + margin))
```

### Over/Under 2.5 Goals Features  
```python
over_under_25_over_odds   # Over 2.5 goals odds
over_under_25_under_odds  # Under 2.5 goals odds
over_under_25_line        # Line value (2.5)
```

### Both Teams To Score Features
```python
btts_yes_odds  # Both teams to score - Yes
btts_no_odds   # Both teams to score - No
```

### Asian Handicap Features
```python
asian_handicap_home_odds  # Home team handicap odds
asian_handicap_away_odds  # Away team handicap odds  
asian_handicap_line       # Handicap line (e.g., -1.5, +0.5)
```

### Double Chance Features
```python
double_chance_1x_odds  # Home or Draw
double_chance_x2_odds  # Draw or Away
double_chance_12_odds  # Home or Away
```

### Correct Score Features
```python
correct_score_available    # 1 if market available, 0 otherwise
correct_score_num_outcomes # Number of score outcomes
correct_score_1_0_odds     # 1-0 odds (if available)
correct_score_0_1_odds     # 0-1 odds (if available)
correct_score_1_1_odds     # 1-1 odds (if available)
# ... other common scores
```

## 💰 API Cost Considerations

### Rate Limiting
- Conservative 1.5 second delay between requests
- Automatic retry logic with exponential backoff
- Rate limit detection and handling

### Quota Management
- 1 API call per fixture for odds data
- ~1,520 fixtures = ~1,520 API calls
- Estimated time: ~40 minutes for full dataset

### Cost Optimization
- Start with small samples (10-50 fixtures)
- Test market availability before full collection
- Priority bookmaker selection reduces redundant data

## 🔍 Troubleshooting

### Common Issues

**1. No odds data found**
```
- Check API subscription includes odds data
- Verify SportMonks v3 API access  
- Test with recent fixtures first (better coverage)
```

**2. Rate limiting errors**
```
- Increase rate_limit_delay in collector
- Check API quota status
- Consider spreading collection over multiple days
```

**3. Missing target markets**
```
- Run test_sportmonks_odds.py to discover available markets
- Update market IDs in sportmonks_odds_collector.py
- Some markets may not be available for older seasons
```

**4. Bookmaker not found**
```
- Check available bookmakers with test script
- Update priority_bookmakers list
- Some bookmakers may have limited historical data
```

### Debug Steps

1. **Test API Connection**
   ```bash
   python test_sportmonks_odds.py
   ```

2. **Check Sample Fixture**
   ```bash
   # Manually test a fixture ID
   curl "https://api.sportmonks.com/v3/football/fixtures/YOUR_FIXTURE_ID?include=odds&api_token=YOUR_TOKEN"
   ```

3. **Start Small**
   ```bash
   # Test with 5-10 fixtures first
   python sportmonks_odds_collector.py
   # Enter: 10
   ```

## 📈 Expected Performance

### Coverage by Season
- **2023/24:** 90-95% fixtures with odds
- **2022/23:** 85-95% fixtures with odds  
- **2021/22:** 80-90% fixtures with odds
- **2020/21:** 75-85% fixtures with odds
- **2019/20:** 60-80% fixtures with odds
- **2018/19:** 50-70% fixtures with odds
- **2017/18:** 40-60% fixtures with odds
- **Older seasons:** 20-50% fixtures with odds

### Market Availability
- **1X2:** Highest availability (~95% where odds exist)
- **Over/Under 2.5:** Very high (~90% where odds exist)
- **BTTS:** High (~85% where odds exist)
- **Asian Handicap:** Medium (~60% where odds exist)
- **Double Chance:** Medium (~70% where odds exist)  
- **Correct Score:** Lower (~40% where odds exist)

## 🎯 Integration with ML Pipeline

### Feature Selection
```python
# Core odds features for model training
odds_features = [
    '1x2_home_odds', '1x2_draw_odds', '1x2_away_odds',
    '1x2_market_margin', '1x2_market_efficiency',
    'over_under_25_over_odds', 'over_under_25_under_odds', 
    'btts_yes_odds', 'btts_no_odds',
    'has_odds'
]
```

### Handling Missing Values
```python
# Features are NaN where odds not available
# Use has_odds flag to filter or impute
df_with_odds = df[df['has_odds'] == True]

# Or fill missing odds features
df['1x2_home_odds'].fillna(df['1x2_home_odds'].median(), inplace=True)
```

### Market Efficiency Indicators
```python
# Use market margins as features
# Lower margin = more efficient market = better signal
efficient_markets = df[df['1x2_market_margin'] < 0.05]  # <5% margin
```

## 🚀 Next Steps

After successful odds integration:

1. **Feature Engineering:** Create derived features from odds
2. **Model Enhancement:** Include odds features in training
3. **Backtesting:** Validate model performance with historical odds
4. **Live Integration:** Use OddsAPI for future predictions

## 📞 Support

For issues or questions:
1. Check the log files for detailed error messages
2. Run the test script to diagnose API issues
3. Review SportMonks API documentation
4. Verify your subscription includes historical odds data

---

**Happy modeling with enhanced odds features! 🎯📊**