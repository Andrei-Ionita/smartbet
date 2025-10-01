import pandas as pd
import numpy as np  
import lightgbm as lgb

df = pd.read_csv('LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv')
holdout = df.tail(200)
print(f"Holdout size: {len(holdout)}")

model = lgb.Booster(model_file='LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt')

features = ['home_win_odds', 'away_win_odds', 'draw_odds', 'home_recent_form', 'away_recent_form', 'recent_form_diff', 'home_goals_for', 'home_goals_against', 'away_goals_for', 'away_goals_against', 'home_win_rate', 'away_win_rate']

X = holdout[features]
y = holdout['result']

pred_proba = model.predict(X)
pred_class = np.argmax(pred_proba, axis=1)
max_conf = np.max(pred_proba, axis=1)

predicted_odds = []
for i, pred in enumerate(pred_class):
    row = holdout.iloc[i]
    if pred == 0:
        predicted_odds.append(row['home_win_odds'])
    elif pred == 1:
        predicted_odds.append(row['draw_odds'])
    else:
        predicted_odds.append(row['away_win_odds'])

mask = (max_conf >= 0.6) & (np.array(predicted_odds) >= 1.5)
betting_indices = np.where(mask)[0]

print(f"Qualifying bets: {len(betting_indices)}")

if len(betting_indices) > 0:
    correct = sum((pred_class[i] == y.iloc[i]) for i in betting_indices)
    hit_rate = (correct / len(betting_indices)) * 100
    
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
    print(f"Profit: {total_profit:.2f}")
    
    overall_pass = roi > 0 and hit_rate > 55 and len(betting_indices) >= 5
    print(f"VALIDATION: {'PASS' if overall_pass else 'FAIL'}")
    
    with open('validation_result.txt', 'w') as f:
        f.write(f"VALIDATED={overall_pass}\n")
        f.write(f"ROI={roi:.2f}\n")
        f.write(f"HIT_RATE={hit_rate:.2f}\n")
        f.write(f"BETS={len(betting_indices)}\n")
else:
    print("No bets qualify") 