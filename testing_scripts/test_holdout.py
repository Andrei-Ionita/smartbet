import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime

def main():
    print("🎯 LA LIGA MODEL - HOLDOUT VALIDATION")
    print("=" * 50)
    
    # Load dataset
    df = pd.read_csv('LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv')
    print(f"📊 Loaded {len(df)} matches from {df['season'].nunique()} seasons")
    print(f"📅 Seasons: {df['season'].unique()}")
    
    # Create holdout split (last 20% - most recent season)
    df = df.sort_values('season').reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    
    training_data = df.iloc[:split_idx].copy()
    holdout_data = df.iloc[split_idx:].copy()
    
    print(f"✅ Training: {len(training_data)} matches")
    print(f"✅ Holdout: {len(holdout_data)} matches ({len(holdout_data)/len(df)*100:.1f}%)")
    print(f"📅 Training seasons: {training_data['season'].unique()}")
    print(f"📅 Holdout seasons: {holdout_data['season'].unique()}")
    
    # Save holdout set
    holdout_data.to_csv('la_liga_holdout_test_set.csv', index=False)
    print("📁 Saved: la_liga_holdout_test_set.csv")
    
    # Load frozen model
    model_file = 'LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt'
    try:
        model = lgb.Booster(model_file=model_file)
        print(f"🔒 Loaded frozen model ({model.num_feature()} features)")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False
    
    # Prepare features
    features = ['home_win_odds', 'away_win_odds', 'draw_odds', 'home_recent_form', 
               'away_recent_form', 'recent_form_diff', 'home_goals_for', 
               'home_goals_against', 'away_goals_for', 'away_goals_against', 
               'home_win_rate', 'away_win_rate']
    
    print(f"🎯 Using {len(features)} features")
    
    X_holdout = holdout_data[features]
    y_holdout = holdout_data['result']
    
    print(f"📊 Holdout target distribution: {y_holdout.value_counts().to_dict()}")
    
    # Run predictions on holdout
    print("\n🧠 Running inference on holdout data...")
    pred_proba = model.predict(X_holdout)
    pred_class = np.argmax(pred_proba, axis=1)
    max_conf = np.max(pred_proba, axis=1)
    
    # Calculate raw accuracy
    raw_accuracy = (pred_class == y_holdout).mean() * 100
    avg_confidence = max_conf.mean() * 100
    
    print(f"✅ Raw accuracy: {raw_accuracy:.2f}%")
    print(f"📊 Average confidence: {avg_confidence:.2f}%")
    
    # Create predictions with odds
    predictions = []
    for i, pred in enumerate(pred_class):
        row = holdout_data.iloc[i]
        if pred == 0:  # Home win
            pred_odds = row['home_win_odds']
        elif pred == 1:  # Draw  
            pred_odds = row['draw_odds']
        else:  # Away win
            pred_odds = row['away_win_odds']
        
        predictions.append({
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'season': row['season'],
            'actual': y_holdout.iloc[i],
            'predicted': pred,
            'confidence': max_conf[i],
            'predicted_odds': pred_odds,
            'correct': int(pred == y_holdout.iloc[i])
        })
    
    pred_df = pd.DataFrame(predictions)
    pred_df.to_csv('la_liga_holdout_predictions.csv', index=False)
    print("📁 Saved: la_liga_holdout_predictions.csv")
    
    # Paper trading simulation
    print("\n💹 PAPER TRADING SIMULATION")
    print("=" * 50)
    
    confidence_threshold = 0.60  # 60% confidence
    odds_threshold = 1.5         # 1.5 odds minimum
    stake_per_bet = 10.0         # €10 per bet
    
    print(f"🎯 Betting criteria:")
    print(f"   Confidence ≥ {confidence_threshold*100:.0f}%")
    print(f"   Odds ≥ {odds_threshold}")
    print(f"   Stake: €{stake_per_bet} per bet")
    
    # Apply betting filters
    betting_mask = (pred_df['confidence'] >= confidence_threshold) & (pred_df['predicted_odds'] >= odds_threshold)
    betting_predictions = pred_df[betting_mask].copy()
    
    print(f"\n📊 Betting stats:")
    print(f"   Total predictions: {len(pred_df)}")
    print(f"   Qualifying bets: {len(betting_predictions)}")
    print(f"   Bet ratio: {len(betting_predictions)/len(pred_df)*100:.1f}%")
    
    if len(betting_predictions) == 0:
        print("⚠️ No bets qualify for criteria!")
        return False
    
    # Calculate profits
    betting_predictions['stake'] = stake_per_bet
    betting_predictions['profit'] = np.where(
        betting_predictions['correct'] == 1,
        stake_per_bet * betting_predictions['predicted_odds'] - stake_per_bet,
        -stake_per_bet
    )
    
    # Performance metrics
    total_bets = len(betting_predictions)
    winning_bets = betting_predictions['correct'].sum()
    total_stake = betting_predictions['stake'].sum()
    total_profit = betting_predictions['profit'].sum()
    hit_rate = (winning_bets / total_bets) * 100
    roi = (total_profit / total_stake) * 100
    
    # Bankroll simulation
    starting_bankroll = 1000.0
    betting_predictions['cumulative_profit'] = betting_predictions['profit'].cumsum()
    betting_predictions['bankroll'] = starting_bankroll + betting_predictions['cumulative_profit']
    final_bankroll = betting_predictions['bankroll'].iloc[-1]
    
    print(f"\n💰 HOLDOUT RESULTS:")
    print(f"   Total bets: {total_bets}")
    print(f"   Winning bets: {winning_bets}")
    print(f"   Hit rate: {hit_rate:.2f}%")
    print(f"   Total profit: €{total_profit:.2f}")
    print(f"   ROI: {roi:.2f}%")
    print(f"   Final bankroll: €{final_bankroll:.2f}")
    
    # Save transaction log
    betting_predictions.to_csv('la_liga_holdout_transactions.csv', index=False)
    print("📁 Saved: la_liga_holdout_transactions.csv")
    
    # Save summary
    summary = pd.DataFrame([{
        'total_bets': total_bets,
        'winning_bets': winning_bets,
        'hit_rate': hit_rate,
        'roi': roi,
        'total_profit': total_profit,
        'total_stake': total_stake,
        'starting_bankroll': starting_bankroll,
        'final_bankroll': final_bankroll
    }])
    summary.to_csv('la_liga_holdout_summary.csv', index=False)
    print("📁 Saved: la_liga_holdout_summary.csv")
    
    # Final validation assessment
    print("\n✅ FINAL VALIDATION ASSESSMENT")
    print("=" * 50)
    
    # Validation criteria
    roi_pass = roi > 0.0
    hit_rate_pass = hit_rate > 55.0
    volume_pass = total_bets >= 5
    
    overall_pass = roi_pass and hit_rate_pass and volume_pass
    
    print(f"🎯 Validation criteria:")
    print(f"   ROI > 0%: {'✅ PASS' if roi_pass else '❌ FAIL'} ({roi:.2f}%)")
    print(f"   Hit Rate > 55%: {'✅ PASS' if hit_rate_pass else '❌ FAIL'} ({hit_rate:.2f}%)")
    print(f"   Min 5 bets: {'✅ PASS' if volume_pass else '❌ FAIL'} ({total_bets} bets)")
    
    print(f"\n🏆 FINAL RESULT: {'✅ MODEL VALIDATED' if overall_pass else '❌ MODEL FAILED VALIDATION'}")
    
    # Performance assessment
    if overall_pass:
        if roi > 50:
            quality = "🌟 EXCEPTIONAL"
        elif roi > 20:
            quality = "⭐ EXCELLENT"  
        elif roi > 10:
            quality = "✅ GOOD"
        else:
            quality = "📈 ACCEPTABLE"
        print(f"📊 Model quality: {quality}")
    
    # Save validation status
    status_file = 'la_liga_model_validation_status.txt'
    with open(status_file, 'w') as f:
        f.write("LA LIGA MODEL VALIDATION STATUS\n")
        f.write("=" * 32 + "\n\n")
        f.write(f"MODEL_VALIDATED={overall_pass}\n")
        f.write(f"VALIDATION_DATE={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"FINAL_ROI={roi:.2f}%\n")
        f.write(f"FINAL_HIT_RATE={hit_rate:.2f}%\n")
        f.write(f"TOTAL_BETS={total_bets}\n")
        f.write(f"ASSESSMENT={quality if overall_pass else 'FAILED VALIDATION'}\n")
    
    print(f"📁 Saved validation status: {status_file}")
    
    print(f"\n" + "=" * 60)
    print("🎯 HOLDOUT VALIDATION COMPLETE!")
    print(f"Status: {'✅ VALIDATED' if overall_pass else '❌ FAILED'}")
    print("=" * 60)
    
    return overall_pass

if __name__ == "__main__":
    result = main()
    if result:
        print("\n🔥 La Liga model successfully validated on holdout data!")
    else:
        print("\n⚠️ La Liga model failed holdout validation.") 