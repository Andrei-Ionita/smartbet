import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime

def main():
    print("LA LIGA MODEL - HOLDOUT VALIDATION")
    print("=" * 50)
    
    # Load dataset
    df = pd.read_csv('LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv')
    print(f"Loaded {len(df)} matches")
    
    # Create holdout split (last 20%)
    df = df.sort_values('season').reset_index(drop=True)
    split_idx = int(len(df) * 0.8)
    holdout_data = df.iloc[split_idx:].copy()
    print(f"Holdout: {len(holdout_data)} matches")
    
    # Load model
    model = lgb.Booster(model_file='LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt')
    print("Loaded frozen model")
    
    # Features
    features = ['home_win_odds', 'away_win_odds', 'draw_odds', 'home_recent_form', 
               'away_recent_form', 'recent_form_diff', 'home_goals_for', 
               'home_goals_against', 'away_goals_for', 'away_goals_against', 
               'home_win_rate', 'away_win_rate']
    
    X = holdout_data[features]
    y = holdout_data['result']
    
    # Predict
    pred_proba = model.predict(X)
    pred_class = np.argmax(pred_proba, axis=1)
    max_conf = np.max(pred_proba, axis=1)
    
    # Apply filters
    confidence_threshold = 0.60
    odds_threshold = 1.5
    
    # Get odds for predictions
    predicted_odds = []
    for i, pred in enumerate(pred_class):
        if pred == 0:
            predicted_odds.append(holdout_data.iloc[i]['home_win_odds'])
        elif pred == 1:
            predicted_odds.append(holdout_data.iloc[i]['draw_odds'])
        else:
            predicted_odds.append(holdout_data.iloc[i]['away_win_odds'])
    
    # Create betting dataframe
    betting_data = pd.DataFrame({
        'confidence': max_conf,
        'predicted_odds': predicted_odds,
        'correct': (pred_class == y).astype(int)
    })
    
    # Apply filters
    mask = (betting_data['confidence'] >= confidence_threshold) & (betting_data['predicted_odds'] >= odds_threshold)
    bets = betting_data[mask].copy()
    
    print(f"Qualifying bets: {len(bets)}/{len(betting_data)}")
    
    if len(bets) == 0:
        print("No qualifying bets!")
        return False
    
    # Calculate performance
    stake = 10.0
    bets['profit'] = np.where(bets['correct'], 
                             stake * bets['predicted_odds'] - stake,
                             -stake)
    
    hit_rate = bets['correct'].mean() * 100
    roi = (bets['profit'].sum() / (len(bets) * stake)) * 100
    
    print(f"Hit Rate: {hit_rate:.2f}%")
    print(f"ROI: {roi:.2f}%")
    print(f"Profit: €{bets['profit'].sum():.2f}")
    
    # Validation
    roi_pass = roi > 0
    hit_rate_pass = hit_rate > 55
    volume_pass = len(bets) >= 5
    
    overall_pass = roi_pass and hit_rate_pass and volume_pass
    
    print(f"ROI > 0%: {'PASS' if roi_pass else 'FAIL'}")
    print(f"Hit Rate > 55%: {'PASS' if hit_rate_pass else 'FAIL'}")
    print(f"Min 5 bets: {'PASS' if volume_pass else 'FAIL'}")
    print(f"FINAL: {'VALIDATED' if overall_pass else 'FAILED'}")
    
    # Save status
    with open('la_liga_model_validation_status.txt', 'w') as f:
        f.write(f"MODEL_VALIDATED={overall_pass}\n")
        f.write(f"FINAL_ROI={roi:.2f}%\n")
        f.write(f"FINAL_HIT_RATE={hit_rate:.2f}%\n")
        f.write(f"TOTAL_BETS={len(bets)}\n")
    
    return overall_pass

if __name__ == "__main__":
    main() 