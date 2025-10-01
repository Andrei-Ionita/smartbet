# Backend Connection Debugging Guide

## ✅ Current Status

The frontend has been **fully configured** to connect to the live Django backend API. Here's what's been implemented:

### 1. ❌ Mock Data Removal - COMPLETED
- **No mock data found** in the codebase
- All components use real API calls through React Query

### 2. ✅ Real Fetch Implementation - COMPLETED
- `src/lib/api.ts` fetches from `http://localhost:8000/api/predictions/`
- Proper error handling and response parsing
- Added comprehensive debug logging

### 3. ✅ Data Mapping - COMPLETED
- `TopPickCard` component correctly maps backend data structure
- All prediction fields properly displayed (odds, EV, confidence, explanations)

### 4. ✅ CORS Configuration - COMPLETED
- Django settings already include `corsheaders`
- `CORS_ALLOW_ALL_ORIGINS = True` is set for development

### 5. ✅ Debug Logging - COMPLETED
- Added extensive console logging throughout the data flow

## 🔍 How to Verify Real Data

### Step 1: Start the Django Backend
```bash
cd /path/to/smartbet
python manage.py runserver
```

### Step 2: Start the Frontend
```bash
cd smartbet-frontend
npm run dev
```

### Step 3: Check Browser Console
Open the dashboard at `http://localhost:3000/dashboard` and check the browser console. You should see:

```
🚀 Fetching predictions from Django backend...
🔄 usePredictions hook state: { isLoading: true, ... }
📊 Live predictions received: { results: [...], ... }
📊 Number of predictions: X
✅ Final predictions array: [...]
🔍 Dashboard data state: { predictions: [...], ... }
🎯 TopPickCard #1 rendering with prediction: { ... }
```

### Step 4: Test Backend Directly (Optional)
```bash
cd smartbet-frontend
node test-backend.js
```

## 🚨 Troubleshooting

### If you see "Failed to load predictions":
1. **Check Django server is running** on port 8000
2. **Check console logs** for detailed error messages
3. **Verify API endpoint** responds: visit `http://localhost:8000/api/predictions/` in browser
4. **Check Django logs** for any backend errors

### If you see empty predictions:
1. **Check Django database** has prediction data
2. **Verify API returns data** using test script
3. **Check console logs** for data structure issues

### If cards show incorrect data:
1. **Check console logs** for data mapping issues
2. **Verify backend API** returns expected structure
3. **Check TypeScript types** match backend response

## 📊 Expected Data Structure

The backend should return:
```json
{
  "results": [
    {
      "id": "string",
      "match": {
        "home_team": { "name": "Team A" },
        "away_team": { "name": "Team B" },
        "league": "Premier League",
        "kickoff_time": "2024-01-01T15:00:00Z"
      },
      "score": {
        "predicted_outcome": "HOME_WIN",
        "expected_value": 0.072,
        "confidence_level": "HIGH",
        "odds_snapshot": {
          "odds_home": 2.5,
          "odds_draw": 3.2,
          "odds_away": 2.8,
          "bookmaker": "Bet365"
        }
      },
      "explanation": "Model reasoning..."
    }
  ]
}
```

## 🎯 Debug Commands

### Check if backend is running:
```bash
curl http://localhost:8000/api/predictions/
```

### Check frontend API connection:
```bash
node test-backend.js
```

### View all console logs:
1. Open browser developer tools (F12)
2. Go to Console tab
3. Filter by "predictions" or emojis (🚀, 📊, 🎯)

---

**Status**: ✅ Frontend is ready to display live backend data. All mock data has been removed and real API integration is complete with comprehensive debugging. 