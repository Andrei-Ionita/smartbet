import pandas as pd
import numpy as np  
import lightgbm as lgb

df = pd.read_csv('LOCKED_PRODUCTION_la_liga_complete_training_dataset_20250630_152907.csv')
holdout = df.tail(200)
print(f"Testing on {len(holdout)} matches")

model = lgb.Booster(model_file='LOCKED_PRODUCTION_league_model_1x2_la_liga_20250630_152907.txt')

features = ['home_win_odds', 'away_win_odds', 'draw_odds', 'home_recent_form', 'away_recent_form', 'recent_form_diff', 'home_goals_for', 'home_goals_against', 'away_goals_for', 'away_goals_against', 'home_win_rate', 'away_win_rate']

X = holdout[features]
y = holdout['result']

pred_proba = model.predict(X)
pred_class = np.argmax(pred_proba, axis=1)
max_conf = np.max(pred_proba, axis=1)

print("Validation complete") 