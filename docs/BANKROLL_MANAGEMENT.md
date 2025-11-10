# Bankroll Management System

## Overview

SmartBet's Bankroll Management system helps users bet responsibly by tracking their betting budget, recommending optimal stake sizes, and enforcing loss limits. This feature differentiates SmartBet from competitors by promoting informed and responsible betting strategies.

## Features

### 1. **Personal Bankroll Tracking** 💰
- Set initial bankroll amount
- Real-time tracking of current bankroll
- Track profit/loss and ROI
- View complete transaction history

### 2. **Kelly Criterion Calculator** 📊
- **Full Kelly**: Mathematical optimal stake (aggressive)
- **Fractional Kelly (1/4)**: Safer version, recommended for most users
- **Fixed Percentage**: Bet same % of bankroll every time
- **Fixed Amount**: Bet same dollar amount every time
- **Confidence Scaled**: Scale stakes based on model confidence

### 3. **Risk Management** 🛡️
- **Daily Loss Limits**: Hard stops to prevent chasing losses
- **Weekly Loss Limits**: Broader protection over longer periods
- **Max Stake Percentage**: Cap on single bet size (% of bankroll)
- **Automatic Limit Resets**: Daily/weekly limits reset automatically

### 4. **Risk Profiles** ⚖️

#### Conservative 🛡️
- Max stake: 2% per bet
- Strategy: 1/8 Kelly
- Min confidence: 70%
- Daily limit: 5% of bankroll
- Weekly limit: 15% of bankroll

#### Balanced ⚖️ (Recommended)
- Max stake: 5% per bet
- Strategy: 1/4 Kelly
- Min confidence: 60%
- Daily limit: 10% of bankroll
- Weekly limit: 25% of bankroll

#### Aggressive 🚀
- Max stake: 10% per bet
- Strategy: 1/2 Kelly
- Min confidence: 55%
- Daily limit: 20% of bankroll
- Weekly limit: 40% of bankroll

### 5. **Stake Recommendations** 🎯
For each prediction, the system provides:
- **Recommended stake amount**: Calculated based on strategy
- **Stake percentage**: Percentage of current bankroll
- **Risk level**: Low, Medium, or High
- **Risk explanation**: Plain language explanation
- **Warnings**: Alerts for concerning bet characteristics

### 6. **Performance Analytics** 📈
- Total bets placed
- Win rate
- Average profit per bet
- ROI percentage
- Pending bets and exposure

## API Endpoints

### Create Bankroll
```bash
POST /api/bankroll/create/
```

**Request:**
```json
{
  "session_id": "user_12345",
  "initial_bankroll": 1000.00,
  "currency": "USD",
  "risk_profile": "balanced",
  "staking_strategy": "kelly_fractional",
  "daily_loss_limit": 100.00,
  "weekly_loss_limit": 250.00,
  "max_stake_percentage": 5.0
}
```

**Response:**
```json
{
  "success": true,
  "bankroll": {...},
  "profile_settings": {...},
  "message": "Bankroll created successfully with balanced profile"
}
```

### Get Bankroll
```bash
GET /api/bankroll/{session_id}/
```

**Response:**
```json
{
  "bankroll": {
    "session_id": "user_12345",
    "current_bankroll": 1150.00,
    "initial_bankroll": 1000.00,
    "total_profit_loss": 150.00,
    "roi_percent": 15.0,
    "is_daily_limit_reached": false,
    ...
  },
  "recent_transactions": [...],
  "pending_bets": 2,
  "pending_exposure": 50.00
}
```

### Get Stake Recommendation
```bash
POST /api/bankroll/stake-recommendation/
```

**Request:**
```json
{
  "session_id": "user_12345",
  "fixture_id": 12345,
  "odds": 2.50,
  "win_probability": 0.45,
  "confidence": 68.5
}
```

**Response:**
```json
{
  "success": true,
  "can_bet": true,
  "recommendation": {
    "stake_amount": 28.50,
    "stake_percentage": 2.85,
    "currency": "USD",
    "strategy": "kelly_fractional",
    "risk_level": "medium",
    "risk_explanation": "Medium risk bet: Moderate stake (2.85% of bankroll), Good confidence (68.5%), Good odds (2.50)",
    "kelly_info": {
      "kelly_percentage": 2.85,
      "full_kelly": 11.4,
      "fractional_kelly": 2.85,
      "is_valid": true
    }
  },
  "warnings": [],
  "bankroll_status": {...},
  "simulation": {
    "average_profit": 14.25,
    "win_rate": 45.2,
    "expected_value": 14.25
  }
}
```

### Record Bet
```bash
POST /api/bankroll/record-bet/
```

**Request:**
```json
{
  "session_id": "user_12345",
  "fixture_id": 12345,
  "selected_outcome": "Home",
  "odds": 2.50,
  "stake_amount": 28.50,
  "recommended_stake": 28.50
}
```

### Settle Bet
```bash
POST /api/bankroll/settle-bet/{transaction_id}/
```

**Request:**
```json
{
  "won": true,
  "void": false
}
```

### Get Statistics
```bash
GET /api/bankroll/{session_id}/stats/
```

### Get Transactions
```bash
GET /api/bankroll/{session_id}/transactions/?limit=50&status=settled_won
```

## Frontend Integration

### 1. Setup Modal Component
```typescript
import BankrollSetupModal from '@/app/components/BankrollSetupModal';

// In your component
const [showSetup, setShowSetup] = useState(false);

<BankrollSetupModal 
  isOpen={showSetup}
  onClose={() => setShowSetup(false)}
  onSuccess={(bankroll) => {
    console.log('Bankroll created:', bankroll);
  }}
/>
```

### 2. Bankroll Widget
```typescript
import BankrollWidget from '@/app/components/BankrollWidget';

// Shows current bankroll status, P/L, and limits
<BankrollWidget />
```

### 3. Stake Recommendation Display
```typescript
import StakeRecommendation from '@/app/components/StakeRecommendation';

<StakeRecommendation 
  stakeRecommendation={recommendation}
  compact={true} // or false for full display
/>
```

### 4. Using with Predictions
When fetching recommendations, include `session_id` to get personalized stake recommendations:

```typescript
const sessionId = localStorage.getItem('smartbet_session_id');
const response = await fetch(`/api/recommendations/?session_id=${sessionId}`);
const data = await response.json();

// Each recommendation will now include:
// recommendation.stake_recommendation
```

## Database Models

### UserBankroll
- Stores user's bankroll settings and current state
- Tracks limits, strategy, and risk profile
- Automatically resets daily/weekly limits

### BankrollTransaction
- Individual betting transactions
- Links to PredictionLog for tracking
- Stores stake, outcome, P/L

### StakeRecommendation
- Historical stake recommendations
- Links predictions to bankroll decisions
- Tracks Kelly calculations and risk assessments

## Kelly Criterion Explained

The Kelly Criterion is a mathematical formula for optimal bet sizing:

```
f = (bp - q) / b
```

Where:
- `f` = fraction of bankroll to bet
- `b` = odds - 1 (net odds)
- `p` = probability of winning
- `q` = probability of losing (1 - p)

**Example:**
- Model probability: 50%
- Odds: 2.50
- Full Kelly: 12.5% of bankroll
- 1/4 Kelly (recommended): 3.125% of bankroll

**Why Fractional Kelly?**
- Reduces variance
- More sustainable long-term
- Protects against model inaccuracies
- Recommended by professional bettors

## Usage Guide

### For Users

1. **Set Up Bankroll**
   - Visit /bankroll or click "Set Up" in bankroll widget
   - Choose initial amount (only bet what you can afford to lose)
   - Select risk profile (balanced recommended for beginners)
   - Set loss limits

2. **View Recommendations**
   - Browse predictions as usual
   - Each prediction now shows personalized stake recommendation
   - Follow the recommendation or adjust based on your judgment

3. **Track Performance**
   - Visit /bankroll to see full dashboard
   - Monitor ROI, win rate, and P/L
   - Check how close you are to loss limits
   - Review transaction history

4. **Adjust Settings**
   - Update risk profile as you gain experience
   - Modify loss limits based on results
   - Change staking strategy if needed

### For Developers

1. **Run Migrations**
```bash
python manage.py migrate core
```

2. **Test API Endpoints**
```bash
# Create test bankroll
curl -X POST http://localhost:8000/api/bankroll/create/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_user", "initial_bankroll": 1000, "currency": "USD", "risk_profile": "balanced"}'

# Get stake recommendation
curl -X POST http://localhost:8000/api/bankroll/stake-recommendation/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_user", "odds": 2.5, "win_probability": 0.5, "confidence": 65}'
```

3. **Frontend Development**
```bash
cd smartbet-frontend
npm run dev
# Visit http://localhost:3000/bankroll
```

## Best Practices

### For Users
1. **Start Conservative**: Begin with balanced or conservative profile
2. **Set Realistic Limits**: Daily limits should be 5-10% of total bankroll
3. **Follow Recommendations**: The system is designed by professionals
4. **Track Everything**: Record all bets for accurate performance tracking
5. **Take Breaks**: If you hit daily limit, stop betting for the day
6. **Adjust Gradually**: Don't switch from conservative to aggressive quickly

### For Operators
1. **Encourage Limits**: Default to having loss limits enabled
2. **Show Performance**: Display transparent win/loss statistics
3. **Educate Users**: Provide resources on bankroll management
4. **Monitor Patterns**: Flag concerning betting patterns
5. **Support Resources**: Link to gambling addiction support

## Risk Warnings

This system helps users bet **responsibly**, but:
- ❌ Does not guarantee profits
- ❌ Does not eliminate risk
- ❌ Should not encourage problem gambling
- ✅ Provides tools for informed decisions
- ✅ Enforces protective limits
- ✅ Promotes long-term sustainability

**Always**: Only bet what you can afford to lose.

## Future Enhancements

Potential additions:
- Multi-currency support
- Portfolio diversification analysis
- Correlation detection (avoiding correlated bets)
- Betting streaks detection
- Cool-down periods
- Export reports (CSV, PDF)
- Integration with bookmaker APIs
- Real-time odds comparison
- Social comparison (anonymized)

## Support

For issues or questions:
- Check logs in Django admin
- Review transaction history
- Test with small amounts first
- Contact development team

---

**SmartBet Bankroll Management** - Bet smarter, not harder. 🎯

