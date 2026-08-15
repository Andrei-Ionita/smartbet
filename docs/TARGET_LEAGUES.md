# Target Leagues - SportMonks IDs Reference

## 🎯 Overview

This document lists all target leagues for the SmartBet prediction platform, along with their official SportMonks API IDs.

---

## 🏆 Primary Target Leagues (Top 5 European Leagues)

These are the main leagues where we have the most comprehensive data and highest prediction accuracy:

| League | Country | SportMonks ID | Status |
|--------|---------|---------------|--------|
| **Premier League** | 🏴󐁧󐁢󐁥󐁮󐁧󐁿 England | `8` | ✅ Active |
| **La Liga** | 🇪🇸 Spain | `564` | ✅ Active |
| **Serie A** | 🇮🇹 Italy | `384` | ✅ Active |
| **Bundesliga** | 🇩🇪 Germany | `82` | ✅ Active |
| **Ligue 1** | 🇫🇷 France | `301` | ✅ Active |

---

## 🌍 Additional European Leagues

Extended coverage for additional betting opportunities:

| League | Country | SportMonks ID | Status |
|--------|---------|---------------|--------|
| **Romanian SuperLiga (provider: Liga 1)** | 🇷🇴 Romania | `474` | Active and payload-verified |
| **Danish Superliga** | 🇩🇰 Denmark | `271` | 📋 Configured |
| **Eredivisie** | 🇳🇱 Netherlands | `72` | 📋 Configured |
| **Belgian Pro League** | 🇧🇪 Belgium | `208` | 📋 Configured |
| **Austrian Bundesliga** | 🇦🇹 Austria | `181` | 📋 Configured |
| **Croatian 1. HNL** | 🇭🇷 Croatia | `244` | 📋 Configured |
| **Polish Ekstraklasa** | 🇵🇱 Poland | `453` | 📋 Configured |
| **Portuguese Primeira Liga** | 🇵🇹 Portugal | `462` | 📋 Configured |
| **Swedish Allsvenskan** | 🇸🇪 Sweden | `573` | 📋 Configured |
| **Swiss Super League** | 🇨🇭 Switzerland | `591` | 📋 Configured |
| **Turkish Super Lig** | 🇹🇷 Turkey | `600` | 📋 Configured |
| **Norwegian Eliteserien** | 🇳🇴 Norway | `444` | 📋 Configured |
| **Scottish Premiership** | 🏴󐁧󐁢󐁳󐁣󐁴󐁿 Scotland | `501` | 📋 Configured |
| **Ukrainian Premier League** | 🇺🇦 Ukraine | `609` | 📋 Configured |

---

## 🏆 European Competitions

International club competitions:

| Competition | Level | SportMonks ID | Status |
|-------------|-------|---------------|--------|
| **UEFA Champions League** | 🌟 Elite | `5` | ✅ Active |
| **UEFA Europa League** | 🌟 Major | `6` | ✅ Active |

---

## 📊 League Priority Tiers

### Tier 1: Premium Coverage (Top 5)
- Premier League (8)
- La Liga (564)
- Serie A (384)
- Bundesliga (82)
- Ligue 1 (301)

**Features:**
- ✅ Full historical data
- ✅ Real-time predictions
- ✅ Comprehensive statistics
- ✅ Highest prediction accuracy
- ✅ Most betting opportunities

### Tier 2: Extended Coverage
- Romanian SuperLiga (474) — active and payload-verified
- UEFA Champions League (5)
- UEFA Europa League (6)

**Features:**
- ✅ Regular predictions
- ✅ Good data coverage
- ✅ Reliable accuracy

### Tier 3: Additional Coverage
All other leagues listed above

**Features:**
- 📋 Basic predictions
- 📋 Standard data coverage
- 📋 Experimental accuracy

---

## 🔧 Configuration

All league configurations are stored in:
```
config/league_config.json
```

### Configuration Format
```json
{
  "name_en": "Premier League",
  "sportmonks_id": 8,
  "country": "England"
}
```

---

## 🎯 API Usage

### Fetching Fixtures for Target Leagues

```python
# Python Example
TARGET_LEAGUE_IDS = [8, 564, 384, 82, 301]

endpoint = f"{SPORTMONKS_BASE_URL}/fixtures/upcoming"
params = {
    "leagues": ",".join(map(str, TARGET_LEAGUE_IDS)),
    "include": "predictions,participants,league"
}
```

```typescript
// TypeScript Example
const TARGET_LEAGUE_IDS = [8, 564, 384, 82, 301];

const url = `${SPORTMONKS_BASE_URL}/fixtures/upcoming?leagues=${TARGET_LEAGUE_IDS.join(',')}&include=predictions,participants,league`;
```

---

## 📈 Data Quality by League

### Prediction Model Coverage

| League | Models Available | Avg Confidence | Data Quality |
|--------|-----------------|----------------|--------------|
| Premier League | 3-5 models | 62% | ⭐⭐⭐⭐⭐ |
| La Liga | 3-5 models | 61% | ⭐⭐⭐⭐⭐ |
| Serie A | 3-5 models | 60% | ⭐⭐⭐⭐⭐ |
| Bundesliga | 3-5 models | 61% | ⭐⭐⭐⭐⭐ |
| Ligue 1 | 3-5 models | 59% | ⭐⭐⭐⭐⭐ |
| Romanian SuperLiga | Available | Available | Production payload verified 2026-08-15 |
| Champions League | 3-5 models | 58% | ⭐⭐⭐⭐⭐ |
| Europa League | 3-4 models | 57% | ⭐⭐⭐⭐ |

---

## 🎲 Betting Markets Available

### Market Coverage by League

**Top 5 Leagues:**
- ✅ Fulltime Result (1X2)
- ✅ Over/Under 2.5 Goals
- ✅ Both Teams To Score
- ✅ Asian Handicap
- ✅ Double Chance
- ✅ Correct Score
- ✅ Goal Line

**Other Leagues:**
- ✅ Fulltime Result (1X2)
- ✅ Over/Under 2.5 Goals
- ⚠️ Limited additional markets

---

## 🔄 Update Schedule

### Data Refresh Rates
- **Fixtures:** Every 6 hours
- **Predictions:** Every 12 hours (closer to kickoff: every 2 hours)
- **Odds:** Real-time (via SportMonks API)
- **Results:** Post-match (within 1 hour)

---

## 📝 Quick Reference

### Most Commonly Used IDs

```python
# Primary Leagues (Copy-Paste Ready)
PREMIER_LEAGUE = 8
LA_LIGA = 564
SERIE_A = 384
BUNDESLIGA = 82
LIGUE_1 = 301

# Extended
LIGA_I = 486
CHAMPIONS_LEAGUE = 5
EUROPA_LEAGUE = 6

# All Primary
ALL_PRIMARY = [8, 564, 384, 82, 301]

# All Active
ALL_ACTIVE = [8, 564, 384, 82, 301, 486, 5, 6]
```

---

## 🚀 Adding New Leagues

To add a new league to the system:

1. **Get SportMonks League ID** from their API documentation
2. **Update** `config/league_config.json`:
   ```json
   {
     "name_en": "New League Name",
     "sportmonks_id": YOUR_LEAGUE_ID,
     "country": "Country Name"
   }
   ```
3. **Test** predictions fetch for the new league
4. **Validate** data quality and model availability
5. **Update** this documentation

---

## 📊 Historical Notes

### Verified Romanian League ID
SportMonks' public coverage catalog listed the Romanian top division as
`Liga 1 #474` on 2026-08-13. BetGlitch selected it in the production account on
that date as a no-cost replacement for Russian Premier League #486. Production
fixture, prediction, odds, bookmaker, timestamp and context payloads were
verified on 2026-08-15.

### Common Pitfalls
- ⚠️ Some SportMonks IDs changed between API versions
- ⚠️ League ID 486 is the Russian Premier League, not Romania
- ⚠️ League ID 271 is the Danish Superliga, not Romania
- ⚠️ League ID 609 is the Ukrainian Premier League
- ⚠️ Always verify new IDs with actual API responses

---

## 🔗 Related Documentation

- [SportMonks Predictions System](./SPORTMONKS_PREDICTIONS_SYSTEM.md)
- [API Integration Guide](../fixtures/README.md)
- [Configuration Files](../config/league_config.json)

---

*Last Updated: 2025-10-06*
*Source: SportMonks API v3*
*Maintained by: SmartBet Development Team*

