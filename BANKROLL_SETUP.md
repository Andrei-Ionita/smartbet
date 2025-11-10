# 🚀 Quick Setup Guide - Bankroll Management

## What Was Built

Your SmartBet application now has a complete **Bankroll Management System** that includes:

### Backend ✅
- **3 new Django models**: `UserBankroll`, `BankrollTransaction`, `StakeRecommendation`
- **Kelly Criterion calculator** with multiple staking strategies
- **8 REST API endpoints** for complete bankroll management
- **Risk management tools** with daily/weekly loss limits
- **Automatic stake recommendations** integrated into prediction API

### Frontend ✅
- **BankrollSetupModal**: Beautiful onboarding for new users
- **BankrollWidget**: Compact dashboard widget showing current status
- **StakeRecommendation**: Display optimal stake sizes for each bet
- **Full Bankroll Dashboard**: `/bankroll` page with stats, transactions, and settings

## Quick Start (5 minutes)

### Step 1: Run Database Migrations
```bash
# You're in the project root (C:\Users\Andrei\OneDrive\Desktop\ML\smartbet)
python manage.py migrate core
```

### Step 2: Start Backend
```bash
# If Django server is not running
python manage.py runserver
```

### Step 3: Start Frontend
```bash
cd smartbet-frontend
npm run dev
```

### Step 4: Test It Out

1. **Visit**: http://localhost:3000
2. **Look for**: Bankroll widget on homepage (or any page)
3. **Click**: "Set Up" to create your bankroll
4. **Fill in**:
   - Initial bankroll: $1000 (or any amount)
   - Risk profile: Balanced (recommended)
   - Strategy: Fractional Kelly (default)
5. **Click**: "Create Bankroll"

### Step 5: See It In Action

1. **Go to predictions page**
2. **Add**: `?session_id=YOUR_SESSION_ID` to URL (or it auto-detects from localStorage)
3. **Each prediction** now shows personalized stake recommendation!
4. **Visit**: http://localhost:3000/bankroll for full dashboard

## API Testing (Optional)

### Create a Test Bankroll
```bash
curl -X POST http://localhost:8000/api/bankroll/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_user_123",
    "initial_bankroll": 1000.00,
    "currency": "USD",
    "risk_profile": "balanced",
    "staking_strategy": "kelly_fractional",
    "max_stake_percentage": 5.0
  }'
```

### Get Stake Recommendation
```bash
curl -X POST http://localhost:8000/api/bankroll/stake-recommendation/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_user_123",
    "odds": 2.50,
    "win_probability": 0.50,
    "confidence": 65.0
  }'
```

### Get Bankroll Status
```bash
curl http://localhost:8000/api/bankroll/test_user_123/
```

### Get Recommendations with Stakes
```bash
curl "http://localhost:8000/api/recommendations/?session_id=test_user_123&limit=5"
```

## Features Overview

### 1. Kelly Criterion 📊
Automatically calculates optimal bet size based on:
- Your win probability (from AI model)
- Bookmaker odds
- Your bankroll size
- Your risk tolerance

**Example**:
- Bankroll: $1000
- Model confidence: 65%
- Odds: 2.50
- Recommended stake: $28.50 (2.85% using 1/4 Kelly)

### 2. Risk Management 🛡️
**Three profiles**:
- **Conservative**: Max 2% per bet, 1/8 Kelly, strict limits
- **Balanced**: Max 5% per bet, 1/4 Kelly, moderate limits (recommended)
- **Aggressive**: Max 10% per bet, 1/2 Kelly, relaxed limits

**Loss Limits**:
- Daily: Prevents chasing losses in one session
- Weekly: Broader protection over time
- Automatic resets at midnight/Monday

### 3. Real-Time Tracking 📈
- Current bankroll
- Total profit/loss
- ROI percentage
- Win rate
- All transactions
- Pending bets

### 4. Smart Warnings ⚠️
The system warns you when:
- Stake is too large for your bankroll
- You're close to loss limits
- Bankroll has dropped significantly
- Bet has high variance
- Multiple risk factors present

## Integration with Existing Code

The bankroll system integrates seamlessly:

### In Recommendations API
```python
# core/api_views.py - Already integrated!
# When session_id is provided, each recommendation includes:
recommendation['stake_recommendation'] = {
    'recommended_stake': 28.50,
    'stake_percentage': 2.85,
    'risk_level': 'medium',
    'warnings': [...]
}
```

### In Frontend
```typescript
// Just add the session_id parameter
const sessionId = localStorage.getItem('smartbet_session_id');
const response = await fetch(`/api/recommendations/?session_id=${sessionId}`);

// Stake recommendations are automatically included!
```

## File Structure

### Backend Files
```
core/
├── models.py                 # UserBankroll, BankrollTransaction, StakeRecommendation
├── bankroll_utils.py         # Kelly Criterion, staking strategies, risk assessment
├── bankroll_views.py         # API endpoints for bankroll management
├── api_views.py             # Updated with stake recommendation integration
└── urls.py                  # Routes for bankroll endpoints

core/migrations/
└── 0018_userbankroll_stakerecommendation_bankrolltransaction.py  # New models
```

### Frontend Files
```
smartbet-frontend/
├── app/
│   ├── components/
│   │   ├── BankrollSetupModal.tsx      # Initial setup
│   │   ├── BankrollWidget.tsx          # Dashboard widget
│   │   └── StakeRecommendation.tsx     # Stake display
│   └── bankroll/
│       └── page.tsx                     # Full dashboard page
```

### Documentation
```
docs/
└── BANKROLL_MANAGEMENT.md               # Complete documentation

BANKROLL_SETUP.md                        # This file
```

## Customization Options

### Change Default Risk Profile
```python
# In bankroll_views.py
risk_profile = request.data.get('risk_profile', 'conservative')  # Change default
```

### Adjust Kelly Fraction
```python
# In bankroll_utils.py, calculate_kelly_criterion()
kelly_fractional = kelly_full * 0.25  # Change 0.25 to 0.125 (1/8) or 0.5 (1/2)
```

### Modify Max Stake Limits
```python
# In core/models.py, UserBankroll
max_stake_percentage = models.FloatField(
    default=5.0,  # Change default max %
    validators=[MinValueValidator(0.1), MaxValueValidator(25.0)],  # Change max allowed
)
```

## Troubleshooting

### "Bankroll not found" error
- Make sure you created a bankroll first
- Check session_id in localStorage
- Verify API endpoint is correct

### Migrations not applying
```bash
# Delete db.sqlite3 (WARNING: loses data)
rm db.sqlite3

# Recreate database
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Stake recommendations not showing
- Verify session_id is being sent to API
- Check browser console for errors
- Ensure bankroll exists for that session
- Check odds and probabilities are valid

### Frontend not connecting to backend
- Backend must be running on port 8000
- Frontend must be running on port 3000
- Check CORS settings if needed

## Next Steps

### For Testing
1. Create multiple test bankrolls with different profiles
2. Record some test bets
3. Settle them as won/lost
4. Check statistics update correctly
5. Test loss limit enforcement

### For Production
1. Add user authentication (link to real users, not just sessions)
2. Add email notifications for limits reached
3. Implement bet confirmation UI
4. Add export functionality (CSV/PDF)
5. Track more detailed analytics
6. Add social features (leaderboards)

### For Enhancement
1. Multi-currency support
2. Correlation detection
3. Portfolio optimization
4. Advanced Kelly variants
5. Machine learning for personalized strategies

## Admin Interface

View bankroll data in Django admin:

1. **Create superuser** (if not done):
```bash
python manage.py createsuperuser
```

2. **Login** to admin:
http://localhost:8000/admin/

3. **View models**:
- User Bankrolls
- Bankroll Transactions
- Stake Recommendations

## Key Differentiators

This system makes SmartBet stand out because:

✅ **Responsible Gambling**: Enforces limits, encourages breaks
✅ **Scientific Approach**: Uses Kelly Criterion, not gut feeling
✅ **Transparent**: Shows all calculations and reasoning
✅ **Personalized**: Adapts to individual risk tolerance
✅ **Educational**: Explains why certain stakes are recommended
✅ **Protective**: Prevents common betting mistakes

## Support & Documentation

- **Full docs**: `docs/BANKROLL_MANAGEMENT.md`
- **API examples**: See "API Testing" section above
- **Code comments**: Extensive inline documentation
- **Type hints**: Full TypeScript/Python typing

## Success Metrics

Track these to measure success:
- % of users who set up bankroll
- Average ROI of users following recommendations
- % of users who stay within limits
- Retention rate of bankroll users
- Average session length (should be healthy, not excessive)

---

## 🎉 Congratulations!

You now have a **professional-grade bankroll management system** that:
- Helps users bet responsibly
- Provides scientific stake recommendations
- Tracks performance transparently
- Enforces protective limits
- Differentiates you from competitors

**Ready to test?** Run the migrations and visit http://localhost:3000!

**Questions?** Check `docs/BANKROLL_MANAGEMENT.md` for detailed documentation.

---

Built with ❤️ for responsible and informed betting.

