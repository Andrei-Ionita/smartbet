# OddsAPI Integration Workflow for Training Dataset Enhancement

This guide explains how to fetch historical odds from the paid OddsAPI service and integrate them with your existing Premier League training dataset to create enhanced features for machine learning models.

## 🎯 Overview

The workflow consists of three main scripts:

1. **`oddsapi_collector.py`** - Basic API connection test and setup verification
2. **`odds_integrator.py`** - Fetches historical odds and creates enhanced dataset
3. **`merge_datasets.py`** - Merges original training data with odds data

## 📋 Prerequisites

### 1. OddsAPI Account & API Key
- Sign up at [The Odds API](https://the-odds-api.com)
- Choose a paid plan that includes historical data access
- Get your API key from the dashboard

### 2. Environment Setup
Create a `.env` file in the project root:
```
ODDSAPI_KEY=your_actual_api_key_here
```

### 3. Python Dependencies
Ensure you have the required packages:
```bash
pip install requests pandas python-dotenv numpy
```

## 🚀 Step-by-Step Workflow

### Step 1: Test API Connection
```bash
python oddsapi_collector.py
```

**What it does:**
- Tests your API key and connection
- Shows remaining request quota
- Loads and displays sample of training dataset
- Verifies everything is ready for odds collection

**Expected output:**
```
✅ API key found
✅ API connection successful
📊 Requests remaining: 4500
✅ Loaded 1521 training records
📋 Sample of training data:
   fixture_id       date    home_team        away_team  season_name
0   19134453 2024-08-16  Manchester United       Fulham    2024/2025
```

### Step 2: Collect Historical Odds
```bash
python odds_integrator.py
```

**What it does:**
- Fetches historical odds from OddsAPI for your training fixtures
- Groups fixtures by date to minimize API calls
- Matches Premier League teams between your dataset and OddsAPI
- Extracts odds for multiple markets: 1X2, Over/Under, BTTS
- Handles rate limiting and API errors gracefully
- Saves enhanced dataset with odds features

**Key features:**
- **Smart team matching:** Handles team name variations (e.g., "Man United" → "Manchester United")
- **Multiple markets:** 1X2 (Match Winner), Over/Under 2.5, Both Teams to Score
- **Multiple bookmakers:** Pinnacle, Bet365, Betfair, etc.
- **Rate limiting:** Respects API limits with 1.5-second delays
- **Error handling:** Continues processing even if some dates fail

**Configuration options:**
```python
# In odds_integrator.py main() function
max_requests=15  # Start conservative, increase based on your plan
```

**Expected output:**
```
🚀 Starting odds integration
✅ API connected. Requests remaining: 4500
📂 Loading premier_league_complete_4_seasons_20250624_175954.csv
✅ Processing 1521 fixtures
📅 2024-08-16: 3 fixtures
✅ Manchester United vs Fulham
✅ Arsenal vs Wolverhampton Wanderers
✅ Integration complete!
📊 285/450 fixtures with odds (63.3%)
💾 Saved to: enhanced_training_data_20250124_143022.csv
🔥 Used 15 API requests
```

### Step 3: Merge with Original Dataset
```bash
python merge_datasets.py
```

**What it does:**
- Finds the most recent odds dataset automatically
- Merges odds features with your original training dataset
- Preserves all original features and records
- Handles missing odds data gracefully
- Creates final enhanced dataset for ML training

**Expected output:**
```
📂 Original dataset: premier_league_complete_4_seasons_20250624_175954.csv
📂 Odds dataset: enhanced_training_data_20250124_143022.csv
✅ Original: 1521 records, 21 features
✅ Odds: 450 records, 35 features
🎲 Odds features to merge: 30
✅ Merged dataset: 1521 records, 51 features
📊 Records with odds: 285/1521 (18.7%)
💾 Final dataset saved: complete_training_dataset_with_odds_20250124_143530.csv
```

## 📊 Enhanced Features

The integration adds comprehensive odds-based features:

### Basic Odds Features
- `pinnacle_home`, `pinnacle_draw`, `pinnacle_away` - 1X2 odds from Pinnacle
- `bet365_home`, `bet365_draw`, `bet365_away` - 1X2 odds from Bet365
- `pinnacle_over25`, `pinnacle_under25` - Over/Under 2.5 goals from Pinnacle
- `betfair_btts_yes`, `betfair_btts_no` - Both Teams to Score from Betfair

### Market Analysis Features
- `has_odds` - Boolean flag indicating if odds are available
- `avg_home_odds`, `avg_draw_odds`, `avg_away_odds` - Average across bookmakers
- `implied_prob_home`, `implied_prob_draw`, `implied_prob_away` - Implied probabilities
- `market_margin` - Bookmaker margin calculation
- `market_efficiency` - Market efficiency metric

## 💡 Usage Tips

### 1. API Request Management
- Start with low `max_requests` (10-20) for testing
- Historical data is expensive - plan your requests carefully
- Group multiple fixtures per date to minimize API calls
- Monitor your quota with each run

### 2. Team Name Matching
The system handles common team name variations:
- Manchester United ↔ Man United, Man Utd
- Tottenham Hotspur ↔ Tottenham, Spurs
- Brighton & Hove Albion ↔ Brighton
- AFC Bournemouth ↔ Bournemouth

### 3. Data Quality Considerations
- Older matches (pre-2018) may have limited odds availability
- Recent matches have higher odds coverage
- Missing odds are handled gracefully with default values

### 4. Error Recovery
If a script fails:
- Check your API key and quota
- Reduce `max_requests` parameter
- Review the log files for specific errors
- Scripts can be rerun safely

## 📈 Expected Results

### Odds Availability by Season
Based on OddsAPI historical data coverage:

- **2023/24 Season:** ~90% coverage (recent, high availability)
- **2022/23 Season:** ~85% coverage 
- **2021/22 Season:** ~80% coverage
- **2020/21 Season:** ~70% coverage
- **Earlier seasons:** Lower coverage, may require alternative sources

### Feature Enhancement
- **Original dataset:** 21 features per fixture
- **Enhanced dataset:** 40-60 features per fixture
- **New feature categories:** Market odds, implied probabilities, efficiency metrics

## 🔧 Troubleshooting

### Common Issues

1. **"ODDSAPI_KEY not found"**
   - Create `.env` file in project root
   - Add `ODDSAPI_KEY=your_key` to the file

2. **"API test failed with status: 401"**
   - Check API key is correct
   - Verify account is active and has credits

3. **"Rate limited, waiting..."**
   - Normal behavior - script will pause and retry
   - Consider reducing request frequency

4. **Low odds match rate**
   - Team names may not match perfectly
   - Check log files for specific mismatches
   - Consider adjusting team name mappings

### Log Files
Each script creates detailed log files:
- `odds_integration_YYYYMMDD_HHMMSS.log` - Detailed execution logs
- Check these for debugging API issues or match failures

## 🎯 Next Steps

After successful integration:

1. **Analyze the enhanced dataset** to understand odds coverage
2. **Feature engineering** - create additional derived features
3. **Model training** - use enhanced features for better predictions
4. **Backtesting** - validate model performance with historical odds

## 💰 Cost Considerations

OddsAPI pricing (approximate):
- Basic plan: $50/month, 10K requests
- Professional: $150/month, 50K requests
- Enterprise: Custom pricing

**Cost optimization tips:**
- Group fixtures by date (1 request = all matches for that date)
- Focus on recent seasons with better coverage
- Start with small batches to test effectiveness

---

🎉 **Your training dataset is now enhanced with comprehensive odds data for advanced machine learning models!** 