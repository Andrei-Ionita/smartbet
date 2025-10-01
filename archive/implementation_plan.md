# 🏗️ Model Features Implementation Plan

## 📊 Current Status: API Testing Complete

### ✅ **SportMonks API Access Confirmed**
- **Working Endpoints**: `leagues`, `seasons`, `fixtures`, `teams`
- **Available Data**: Basic match and team metadata
- **League Tested**: Premier League (ID: 8)
- **Limitation**: No direct odds or detailed statistics access

### 🎯 **12 Key Model Features Breakdown**

| Feature | Source Needed | Status | Implementation |
|---------|---------------|---------|----------------|
| **Odds Features (7)** | Betting Markets | ❌ Missing | Use OddsAPI |
| `true_prob_draw` | Odds | ❌ | OddsAPI → 1X2 market |
| `log_odds_home_draw` | Odds | ❌ | OddsAPI → log(home/draw) |
| `prob_ratio_draw_away` | Odds | ❌ | OddsAPI → prob_draw/prob_away |
| `log_odds_draw_away` | Odds | ❌ | OddsAPI → log(draw/away) |
| `market_efficiency` | Odds | ❌ | OddsAPI → 1/margin |
| `prob_ratio_home_draw` | Odds | ❌ | OddsAPI → prob_home/prob_draw |
| `bookmaker_margin` | Odds | ❌ | OddsAPI → sum(1/odds) - 1 |
| **Team Stats (4)** | Match Results | 🔄 Calculable | SportMonks fixtures |
| `goals_for_away` | Team Stats | 🔄 | Calculate from fixtures |
| `goals_against_home` | Team Stats | 🔄 | Calculate from fixtures |
| `attack_strength_home` | Team Stats | 🔄 | Goals vs league average |
| `goals_against_away` | Team Stats | 🔄 | Calculate from fixtures |
| **Form Features (1)** | Recent Results | 🔄 Calculable | SportMonks fixtures |
| `recent_form_home` | Form | 🔄 | Points from last 5-10 matches |

## 🚀 **Implementation Strategy**

### **Phase 1: Data Pipeline Architecture** 
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ SportMonks  │    │   OddsAPI   │    │ Feature     │
│ Fixtures    │───▶│  Betting    │───▶│ Engineering │
│ Teams       │    │  Odds       │    │ Pipeline    │
│ Seasons     │    │  Markets    │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

### **Phase 2: Feature Calculation Methods**

#### **A. Odds Features (7) - OddsAPI Integration**
```python
def calculate_odds_features(odds_home, odds_draw, odds_away):
    """Calculate all 7 odds-based features from 1X2 market"""
    
    # Implied probabilities  
    impl_home = 1 / odds_home
    impl_draw = 1 / odds_draw
    impl_away = 1 / odds_away
    total = impl_home + impl_draw + impl_away
    
    # Normalized probabilities
    prob_home = impl_home / total
    prob_draw = impl_draw / total
    prob_away = impl_away / total
    
    return {
        'true_prob_draw': prob_draw,
        'log_odds_home_draw': log(odds_home / odds_draw),
        'prob_ratio_draw_away': prob_draw / prob_away,
        'log_odds_draw_away': log(odds_draw / odds_away),
        'market_efficiency': 1 / (total - 1),
        'prob_ratio_home_draw': prob_home / prob_draw,
        'bookmaker_margin': total - 1
    }
```

#### **B. Team Statistics (4) - SportMonks Calculation**
```python
def calculate_team_stats(team_id, recent_fixtures):
    """Calculate team stats from recent fixture results"""
    
    home_goals_for = []
    home_goals_against = []
    away_goals_for = []
    away_goals_against = []
    
    for fixture in recent_fixtures:
        if fixture['home_team_id'] == team_id:
            home_goals_for.append(fixture['home_score'])
            home_goals_against.append(fixture['away_score'])
        elif fixture['away_team_id'] == team_id:
            away_goals_for.append(fixture['away_score'])
            away_goals_against.append(fixture['home_score'])
    
    return {
        'goals_for_away': mean(away_goals_for),
        'goals_against_home': mean(home_goals_against),
        'goals_against_away': mean(away_goals_against),
        'attack_strength_home': mean(home_goals_for) / league_avg_goals
    }
```

#### **C. Form Features (1) - SportMonks Calculation**
```python
def calculate_recent_form(team_id, recent_fixtures, num_matches=5):
    """Calculate recent form from last N matches"""
    
    recent_results = get_last_n_matches(team_id, recent_fixtures, num_matches)
    points = 0
    
    for match in recent_results:
        if match['result'] == 'win':
            points += 3
        elif match['result'] == 'draw':
            points += 1
    
    return {
        'recent_form_home': points / (num_matches * 3) * 10  # Scale to 0-10
    }
```

### **Phase 3: API Integration Plan**

#### **1. SportMonks Integration**
- ✅ **Confirmed Working**: Basic endpoints
- 🎯 **Use For**: Fixtures, teams, seasons, match results
- 📊 **Provides**: 5 features (4 team stats + 1 form)

#### **2. OddsAPI Integration** 
- 🎯 **Use For**: Live betting odds
- 📊 **Provides**: 7 odds features
- 🔧 **Endpoint**: `https://api.the-odds-api.com/v4/sports/soccer_epl/odds`

#### **3. Combined Pipeline**
```python
class ModelFeatureCollector:
    def __init__(self):
        self.sportmonks = SportMonksClient()
        self.odds_api = OddsAPIClient()
    
    def collect_match_features(self, match_id):
        # Get match data from SportMonks
        match = self.sportmonks.get_match(match_id)
        
        # Get odds from OddsAPI  
        odds = self.odds_api.get_match_odds(match['home_team'], match['away_team'])
        
        # Calculate all 12 features
        features = {}
        features.update(self.calculate_odds_features(odds))
        features.update(self.calculate_team_stats(match))
        features.update(self.calculate_form_features(match))
        
        return features
```

## 📅 **Implementation Timeline**

### **Week 1: Foundation**
- [ ] Set up OddsAPI integration
- [ ] Test OddsAPI with Premier League
- [ ] Verify 1X2 odds availability

### **Week 2: Feature Engineering**
- [ ] Implement odds feature calculations (7 features)
- [ ] Implement team stats calculations (4 features)  
- [ ] Implement form calculations (1 feature)

### **Week 3: Pipeline Integration**
- [ ] Create unified data collector
- [ ] Test with Premier League matches
- [ ] Validate all 12 features

### **Week 4: Production**
- [ ] Deploy to production environment
- [ ] Monitor feature quality
- [ ] Scale to multiple leagues

## 🎯 **Success Metrics**

- ✅ **100% Feature Coverage**: All 12 features calculated
- ✅ **Data Quality**: <5% missing data
- ✅ **API Reliability**: >99% uptime
- ✅ **Performance**: <2 second feature calculation

## 💡 **Key Insights**

1. **SportMonks Limitation**: No direct odds access, but excellent for match/team data
2. **OddsAPI Necessity**: Required for 7 most important features (58% of model)
3. **Hybrid Approach**: Combine both APIs for complete feature set
4. **Calculation Strategy**: Build team stats from fixture results
5. **Implementation Ready**: Clear path to 100% feature coverage 