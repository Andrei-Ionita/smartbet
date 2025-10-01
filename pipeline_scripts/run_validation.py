import pandas as pd
import numpy as np
import lightgbm as lgb

# Load and split data
print("Loading dataset...")
df = pd.read_csv('LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv')
df = df.sort_values('season').reset_index(drop=True)
split_idx = int(len(df) * 0.8)
holdout_data = df.iloc[split_idx:].copy()
print(f"Holdout: {len(holdout_data)} matches")

# Load model
print("Loading model...")
model = lgb.Booster(model_file='LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt')

# Prepare features
features = ['home_win_odds', 'away_win_odds', 'draw_odds', 'home_recent_form', 
           'away_recent_form', 'recent_form_diff', 'home_goals_for', 
           'home_goals_against', 'away_goals_for', 'away_goals_against', 
           'home_win_rate', 'away_win_rate']

X = holdout_data[features]
y = holdout_data['result']

# Make predictions
print("Making predictions...")
pred_proba = model.predict(X)
pred_class = np.argmax(pred_proba, axis=1)
max_conf = np.max(pred_proba, axis=1)

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
mask = (max_conf >= 0.6) & (np.array(predicted_odds) >= 1.5)
betting_indices = np.where(mask)[0]

print(f"Qualifying bets: {len(betting_indices)}")

if len(betting_indices) > 0:
    # Calculate performance
    correct_bets = sum((pred_class[i] == y.iloc[i]) for i in betting_indices)
    hit_rate = (correct_bets / len(betting_indices)) * 100
    
    # Calculate profits
    profits = []
    for i in betting_indices:
        if pred_class[i] == y.iloc[i]:
            profits.append(10 * predicted_odds[i] - 10)
        else:
            profits.append(-10)
    
    total_profit = sum(profits)
    roi = (total_profit / (len(betting_indices) * 10)) * 100
    
    print(f"Hit Rate: {hit_rate:.2f}%")
    print(f"ROI: {roi:.2f}%")
    print(f"Total Profit: €{total_profit:.2f}")
    
    # Validation criteria
    roi_pass = roi > 0
    hit_rate_pass = hit_rate > 55
    volume_pass = len(betting_indices) >= 5
    overall_pass = roi_pass and hit_rate_pass and volume_pass
    
    print(f"ROI > 0%: {'PASS' if roi_pass else 'FAIL'}")
    print(f"Hit Rate > 55%: {'PASS' if hit_rate_pass else 'FAIL'}")
    print(f"Min 5 bets: {'PASS' if volume_pass else 'FAIL'}")
    print(f"VALIDATION: {'PASSED' if overall_pass else 'FAILED'}")
    
    # Save validation status
    with open('la_liga_model_validation_status.txt', 'w') as f:
        f.write(f"MODEL_VALIDATED={overall_pass}\n")
        f.write(f"FINAL_ROI={roi:.2f}%\n")
        f.write(f"FINAL_HIT_RATE={hit_rate:.2f}%\n")
        f.write(f"TOTAL_BETS={len(betting_indices)}\n")
    
    print("Validation status saved!")
else:
    print("No qualifying bets - validation failed")
    with open('la_liga_model_validation_status.txt', 'w') as f:
        f.write("MODEL_VALIDATED=False\n")
        f.write("REASON=No qualifying bets\n") 