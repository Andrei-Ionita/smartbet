import pandas as pd
import numpy as np
import lightgbm as lgb

# Load dataset
df = pd.read_csv('LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv')
print(f"Loaded {len(df)} matches")

# Create holdout split
df = df.sort_values('season').reset_index(drop=True)
split_idx = int(len(df) * 0.8)
holdout_data = df.iloc[split_idx:].copy()
print(f"Holdout: {len(holdout_data)} matches")

# Load model
model = lgb.Booster(model_file='LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt')
print("Model loaded")

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

print(f"Raw accuracy: {(pred_class == y).mean()*100:.2f}%")

# Get predicted odds
predicted_odds = []
for i, pred in enumerate(pred_class):
    if pred == 0:
        predicted_odds.append(holdout_data.iloc[i]['home_win_odds'])
    elif pred == 1:
        predicted_odds.append(holdout_data.iloc[i]['draw_odds'])
    else:
        predicted_odds.append(holdout_data.iloc[i]['away_win_odds'])

# Apply betting filters
confidence_threshold = 0.60
odds_threshold = 1.5

mask = (max_conf >= confidence_threshold) & (np.array(predicted_odds) >= odds_threshold)
betting_indices = np.where(mask)[0]

print(f"Qualifying bets: {len(betting_indices)}/{len(pred_class)}")

if len(betting_indices) == 0:
    print("No qualifying bets!")
else:
    # Calculate performance on qualifying bets
    correct_bets = sum((pred_class[i] == y.iloc[i]) for i in betting_indices)
    hit_rate = (correct_bets / len(betting_indices)) * 100
    
    # Calculate profits
    profits = []
    stake = 10.0
    for i in betting_indices:
        if pred_class[i] == y.iloc[i]:
            profit = stake * predicted_odds[i] - stake
        else:
            profit = -stake
        profits.append(profit)
    
    total_profit = sum(profits)
    total_stake = len(betting_indices) * stake
    roi = (total_profit / total_stake) * 100
    
    print(f"Hit Rate: {hit_rate:.2f}%")
    print(f"ROI: {roi:.2f}%")
    print(f"Profit: €{total_profit:.2f}")
    
    # Validation criteria
    roi_pass = roi > 0
    hit_rate_pass = hit_rate > 55
    volume_pass = len(betting_indices) >= 5
    
    overall_pass = roi_pass and hit_rate_pass and volume_pass
    
    print(f"ROI > 0%: {'PASS' if roi_pass else 'FAIL'}")
    print(f"Hit Rate > 55%: {'PASS' if hit_rate_pass else 'FAIL'}")
    print(f"Min 5 bets: {'PASS' if volume_pass else 'FAIL'}")
    print(f"FINAL: {'VALIDATED' if overall_pass else 'FAILED'}")
    
    # Save validation status
    with open('la_liga_model_validation_status.txt', 'w') as f:
        f.write(f"MODEL_VALIDATED={overall_pass}\n")
        f.write(f"FINAL_ROI={roi:.2f}%\n")
        f.write(f"FINAL_HIT_RATE={hit_rate:.2f}%\n")
        f.write(f"TOTAL_BETS={len(betting_indices)}\n") 