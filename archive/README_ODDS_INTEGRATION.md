# OddsAPI Integration for Training Dataset Enhancement

## 🎯 Overview
This workflow integrates historical odds from the paid OddsAPI service with your Premier League training dataset to create enhanced features for machine learning models.

## 📁 Files Created
- `oddsapi_collector.py` - Test API connection and verify setup
- `odds_integrator.py` - Fetch historical odds and create enhanced dataset  
- `merge_datasets.py` - Merge original training data with odds data

## 🔧 Setup

### 1. Get OddsAPI Key
- Sign up at [The Odds API](https://the-odds-api.com)
- Choose a paid plan with historical data access
- Get your API key

### 2. Environment Configuration
Create `.env` file in project root:
```
ODDSAPI_KEY=your_actual_api_key_here
```

### 3. Dependencies
```bash
pip install requests pandas python-dotenv numpy
```

## 🚀 Workflow

### Step 1: Test Setup
```bash
python oddsapi_collector.py
```
Verifies API connection and dataset availability.

### Step 2: Collect Odds
```bash
python odds_integrator.py
```
Fetches historical odds for training fixtures. Start with low `max_requests` for testing.

### Step 3: Merge Data
```bash
python merge_datasets.py
```
Combines original training data with collected odds features.

## 📊 Enhanced Features

### Odds Data
- 1X2 odds from multiple bookmakers (Pinnacle, Bet365, Betfair)
- Over/Under 2.5 goals odds
- Both Teams to Score odds
- Market efficiency metrics

### Derived Features
- Implied probabilities
- Market margins
- Best odds across bookmakers
- Odds availability flags

## 💡 Key Benefits

1. **Real market data** - Actual bookmaker odds provide market sentiment
2. **Multiple markets** - 1X2, O/U, BTTS for comprehensive analysis
3. **Premium sources** - Pinnacle and other sharp bookmakers
4. **Smart matching** - Handles team name variations automatically
5. **Graceful degradation** - Missing odds handled appropriately

## 📈 Expected Results

- **Enhanced features:** 40-60 features per fixture (vs 21 original)
- **Coverage:** 60-90% depending on season (newer = better)
- **API efficiency:** 1 request covers all matches for a date

## ⚠️ Important Notes

- Historical odds data requires a paid OddsAPI plan
- Start with small request limits to test
- Older seasons have lower odds availability
- Rate limiting is built-in for API compliance

## 🎉 Final Output

Enhanced training dataset ready for ML models with comprehensive odds-based features for better prediction accuracy. 