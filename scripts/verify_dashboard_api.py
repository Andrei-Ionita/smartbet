import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartbet.settings')
django.setup()

from core.models import UserBankroll, PredictionLog, BankrollTransaction
from django.test import RequestFactory
from core.bankroll_views import get_bankroll, get_transactions, get_stake_recommendation, record_bet
from rest_framework.test import APIRequestFactory

def verify_dashboard_apis():
    print("🚀 Starting Dashboard API Verification...")
    
    # 1. Setup Test Data
    session_id = "test_dashboard_session_v1"
    
    # Clean up old test data
    UserBankroll.objects.filter(session_id=session_id).delete()
    
    print(f"📝 Creating test bankroll for session: {session_id}")
    bankroll = UserBankroll.objects.create(
        session_id=session_id,
        initial_bankroll=Decimal('1000.00'),
        current_bankroll=Decimal('1000.00'),
        currency='USD',
        risk_profile='balanced',
        staking_strategy='kelly_criterion',
        daily_loss_limit=Decimal('100.00'),
        weekly_loss_limit=Decimal('300.00'),
        max_stake_percentage=5.0
    )
    
    factory = APIRequestFactory()
    
    # 2. Test Bankroll Summary API
    print("\n💰 Testing Bankroll Summary API...")
    request = factory.get(f'/api/bankroll/{session_id}/')
    response = get_bankroll(request, session_id=session_id)
    
    if response.status_code == 200:
        data = response.data
        print("✅ Bankroll API Success")
        print(f"   - Current Bankroll: ${data['bankroll']['current_bankroll']}")
        print(f"   - Risk Profile: {data['bankroll']['risk_profile']}")
    else:
        print(f"❌ Bankroll API Failed: {response.status_code}")
        
    # 3. Test Recommendations & Stake Calculation
    print("\n🧠 Testing Stake Recommendation API...")
    # Create a dummy prediction log if needed, or just mock the data
    # We'll mock the request data as if it came from the frontend
    rec_data = {
        'session_id': session_id,
        'fixture_id': 12345, # Dummy ID
        'odds': 2.0,
        'win_probability': 0.55,
        'confidence': 60.0
    }
    
    request = factory.post('/api/bankroll/stake-recommendation/', rec_data, format='json')
    response = get_stake_recommendation(request)
    
    if response.status_code == 200:
        data = response.data
        print("✅ Stake Recommendation API Success")
        print(f"   - Recommended Stake: ${data['recommendation']['stake_amount']}")
        print(f"   - Strategy: {data['recommendation']['strategy']}")
        recommended_stake = data['recommendation']['stake_amount']
    else:
        print(f"❌ Stake Recommendation API Failed: {response.status_code}")
        recommended_stake = 10.0 # Fallback
        
    # 4. Test Bet Placement
    print("\n🎲 Testing Bet Placement API...")
    bet_data = {
        'session_id': session_id,
        'fixture_id': 12345,
        'selected_outcome': 'Home',
        'odds': 2.0,
        'stake_amount': recommended_stake,
        'match_description': 'Test Team A vs Test Team B'
    }
    
    request = factory.post('/api/bankroll/record-bet/', bet_data, format='json')
    response = record_bet(request)
    
    if response.status_code == 201:
        print("✅ Bet Placement API Success")
        print(f"   - Transaction ID: {response.data['transaction']['id']}")
        print(f"   - New Bankroll: ${response.data['bankroll']['current_bankroll']}")
    else:
        print(f"❌ Bet Placement API Failed: {response.status_code} - {response.data}")

    # 5. Test Active Bets API (Transactions)
    print("\n📋 Testing Active Bets API...")
    request = factory.get(f'/api/bankroll/{session_id}/transactions/?status=pending')
    response = get_transactions(request, session_id=session_id)
    
    if response.status_code == 200:
        data = response.data
        print("✅ Active Bets API Success")
        print(f"   - Pending Bets Count: {data['count']}")
        if data['count'] > 0:
            print(f"   - Latest Bet: {data['transactions'][0]['match_description']}")
    else:
        print(f"❌ Active Bets API Failed: {response.status_code}")

    print("\n✨ Dashboard Verification Complete!")

if __name__ == '__main__':
    verify_dashboard_apis()
