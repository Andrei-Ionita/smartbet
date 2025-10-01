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