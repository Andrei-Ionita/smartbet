# SmartBet AI - Quick Reference Card

## 🎯 System Overview
**Phase 1 + Phase 2 Complete** - Consensus ensemble of 3 AI models for 1X2 predictions across 27 leagues

---

## 📊 Key Numbers

| Metric | Value |
|--------|-------|
| **Leagues Supported** | 27 |
| **Active Leagues** | 22 |
| **Fixtures Analyzed** | 189 |
| **Models per Fixture** | 3 (1X2 predictions) |
| **Avg Confidence** | 54.3% |
| **Max Confidence** | 77.1% |
| **Confidence Threshold** | 55% |
| **Top Recommendations** | 10 |
| **Time Window** | 14 days |

---

## 🔧 Technical Stack

### **Backend**
- Python 3.10+
- SportMonks API
- Consensus Ensemble Method

### **Frontend**
- Next.js
- TypeScript
- TailwindCSS
- SWR (data fetching)

---

## 📁 Key Files

### **Phase 1**
```bash
phase1_1x2_ensemble_system.py    # Ensemble analysis system
```

### **Phase 2**
```bash
smartbet-frontend/app/api/recommendations/route.ts    # API with ensemble
smartbet-frontend/app/page.tsx                        # Homepage
```

### **Documentation**
```bash
docs/PHASE2_COMPLETE.md              # Phase 2 docs
docs/PHASE1_AND_PHASE2_SUMMARY.md    # Complete summary
docs/QUICK_REFERENCE.md              # This file
```

---

## 🎨 Ensemble Method

### **Input**
3 SportMonks AI models (type_ids: 233, 237, 238)

### **Process**
1. Majority vote → Find predicted outcome
2. Max probability → For majority outcome
3. Average probability → For other outcomes

### **Output**
Consensus probabilities (home%, draw%, away%)

### **Example**
```
Models: [HOME 72%, HOME 69%, HOME 57%]
Result: HOME 72% (consensus)
```

---

## 🚀 Running the System

### **Phase 1 Analysis**
```bash
cd /path/to/smartbet
python phase1_1x2_ensemble_system.py
```

### **Frontend Development**
```bash
cd smartbet-frontend
npm run dev
```

### **API Testing**
```bash
curl http://localhost:3000/api/recommendations
```

---

## 📊 API Response Structure

```json
{
  "recommendations": [
    {
      "fixture_id": 12345,
      "home_team": "Team A",
      "away_team": "Team B",
      "league": "Premier League",
      "predicted_outcome": "Home",
      "confidence": 72,
      "explanation": "SmartBet AI predicts a Home win with 72% confidence using consensus of 3 AI models."
    }
  ],
  "total": 10,
  "confidence_threshold": 55,
  "ensemble_method": "consensus_3_models",
  "ensemble_description": "Phase 1: Consensus ensemble of 3 SportMonks AI models"
}
```

---

## 🎯 Supported Leagues (27 Total)

### **Major 5**
- Premier League (England)
- La Liga (Spain)
- Bundesliga (Germany)
- Serie A (Italy)
- Ligue 1 (France)

### **Other 22**
Championship, FA Cup, Carabao Cup, Eredivisie, Admiral Bundesliga, Pro League, 1. HNL, Superliga, Serie B, Coppa Italia, Eliteserien, Ekstraklasa, Liga Portugal, Premier League (Romania), Premiership (Scotland), La Liga 2, Copa Del Rey, Allsvenskan, Super League (Switzerland), Super Lig (Turkey), and more.

---

## 🔍 Environment Variables

```bash
SPORTMONKS_API_TOKEN=your_token_here
```

**Location:** `.env` file in project root

---

## 📈 Performance Benchmarks

| Method | Avg Confidence | Use Case |
|--------|---------------|----------|
| Single Model | ~46% | Baseline |
| Simple Average | 45.9% | Basic ensemble |
| **Consensus** | **54.3%** | **Production** ✅ |
| Variance Weighted | 55.0% | High confidence picks |

---

## 🎨 Frontend Stats Display

```
55%+ Confidence | 27 Leagues | 14 Days | 3 AI Ensemble
```

---

## 🔗 Quick Links

- **SportMonks API Docs**: https://docs.sportmonks.com/
- **Next.js Docs**: https://nextjs.org/docs
- **Project Root**: `/path/to/smartbet`

---

## 🛠️ Common Tasks

### **Update Confidence Threshold**
```typescript
// File: smartbet-frontend/app/api/recommendations/route.ts
const MINIMUM_CONFIDENCE = 55  // Change this value
```

### **Change Top N Recommendations**
```typescript
// File: smartbet-frontend/app/api/recommendations/route.ts
.slice(0, 10)  // Change 10 to desired number
```

### **Modify Ensemble Method**
```typescript
// File: smartbet-frontend/app/api/recommendations/route.ts
// function consensusEnsemble(models: any[])
// Modify the logic here
```

---

## 🐛 Troubleshooting

### **No predictions returned**
- Check API token in `.env`
- Verify SportMonks subscription includes predictions addon
- Check if there are fixtures in next 14 days

### **Low confidence predictions**
- Lower `MINIMUM_CONFIDENCE` threshold
- Check if 3 models available for ensemble
- Verify prediction type_ids (233, 237, 238)

### **Frontend not updating**
- Check SWR refresh interval (60s default)
- Verify API route is responding
- Check browser console for errors

---

## ✅ Quality Checklist

- [ ] SportMonks API token configured
- [ ] Phase 1 analysis runs successfully
- [ ] Frontend displays recommendations
- [ ] Confidence threshold appropriate (55%)
- [ ] Top 10 recommendations shown
- [ ] Ensemble method working (3 models)
- [ ] Documentation up to date

---

## 📞 Support

For issues or questions:
1. Check documentation in `docs/`
2. Review code comments in key files
3. Test with Phase 1 analysis script
4. Verify API responses

---

*Quick Reference - SmartBet AI v1.0*
*Phases 1 & 2 Complete - Production Ready*
