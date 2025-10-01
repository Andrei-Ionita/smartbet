#!/usr/bin/env python3
"""
SportMonks Predictions - Get 5 upcoming matches from each target league with match winner predictions
"""

import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_sportmonks_predictions():
    """Get 5 upcoming matches from each target league with SportMonks match winner predictions"""
    
    # Get API token
    api_token = os.getenv('SPORTMONKS_API_TOKEN')
    if not api_token:
        print("ERROR: SPORTMONKS_API_TOKEN not found in environment")
        return
    
    print("Fetching 5 upcoming matches from EACH target league...")
    print(f"Current time: {datetime.now()}")
    
    # League IDs (top 5 only): La Liga=564, Premier League=8, Serie A=384, Bundesliga=82, Ligue 1=301
    league_ids = "564,8,384,82,301"
    
    # Fetch upcoming fixtures with correct parameters
    url = f"https://api.sportmonks.com/v3/football/fixtures/upcoming/markets/1"
    params = {
        'api_token': api_token,
        'include': 'participants;league;metadata;predictions',
        'filters': f'fixtureLeagues:{league_ids}',
        'per_page': 50
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"API Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get('data', [])
            pagination = data.get('pagination', {})
            has_more = pagination.get('has_more', False)
            
            print(f"Found {len(fixtures)} fixtures on first page")
            print(f"Has more pages: {has_more}")
            
            # Get additional pages if needed
            all_fixtures = fixtures.copy()
            page = 2
            
            while has_more and len(all_fixtures) < 100:
                print(f"Fetching page {page}...")
                params['page'] = page
                
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    page_data = response.json()
                    page_fixtures = page_data.get('data', [])
                    all_fixtures.extend(page_fixtures)
                    
                    pagination = page_data.get('pagination', {})
                    has_more = pagination.get('has_more', False)
                    
                    print(f"Page {page}: {len(page_fixtures)} fixtures, has_more: {has_more}")
                    page += 1
                else:
                    print(f"Error fetching page {page}: {response.status_code}")
                    break
            
            print(f"Total fixtures found: {len(all_fixtures)}")
            
            # Organize matches by league
            matches_by_league = {
                'Premier League': [],
                'La Liga': [],
                'Serie A': [],
                'Bundesliga': [],
                'Ligue 1': []
            }
            
            for fixture in all_fixtures:
                try:
                    fixture_id = fixture.get('id')
                    name = fixture.get('name', '')
                    starting_at = fixture.get('starting_at')
                    participants = fixture.get('participants', [])
                    predictions = fixture.get('predictions', [])
                    metadata = fixture.get('metadata', {})
                    league_id = fixture.get('league_id')
                    league_obj = fixture.get('league') or {}
                    
                    # Get team names
                    home_team = ''
                    away_team = ''
                    if participants and len(participants) >= 2:
                        home_team = participants[0].get('name', '')
                        away_team = participants[1].get('name', '')
                    
                    # Determine league from league_id (and validate using included league name if present)
                    league = get_league_name(league_id)
                    league_name_from_api = (league_obj.get('name') or '').lower() if isinstance(league_obj, dict) else ''
                    if league_name_from_api:
                        if 'premier' in league_name_from_api and league != 'Premier League':
                            league = 'Premier League'
                        elif 'laliga' in league_name_from_api or 'la liga' in league_name_from_api:
                            league = 'La Liga'
                        elif 'serie a' in league_name_from_api:
                            league = 'Serie A'
                        elif 'bundesliga' in league_name_from_api:
                            league = 'Bundesliga'
                        elif 'ligue 1' in league_name_from_api:
                            league = 'Ligue 1'
                    
                    # Only include target leagues, predictable fixtures, and if we need more for this league
                    predictable = True
                    if isinstance(metadata, dict):
                        predictable = metadata.get('predictable', True)
                    if (
                        league in matches_by_league
                        and len(matches_by_league[league]) < 5
                        and predictable is not False
                    ):
                        # Extract SportMonks predictions (match winner + score if available)
                        match_winner_prediction = None
                        score_prediction = None
                        if predictions and isinstance(predictions, list):
                            for pred in predictions:
                                if isinstance(pred, dict):
                                    pred_type = pred.get('type_id')
                                    pred_values = pred.get('predictions', {})
                                    
                                    # Look for match winner prediction (1X2)
                                    if 'home' in pred_values and 'away' in pred_values and 'draw' in pred_values:
                                        match_winner_prediction = pred_values
                                    
                                    # Look for score prediction (correct score)
                                    if 'scores' in pred_values:
                                        score_prediction = pred_values
                        
                        # Require match winner prediction to be present
                        if not match_winner_prediction:
                            continue

                        match_data = {
                            'fixture_id': fixture_id,
                            'match': f"{home_team} vs {away_team}",
                            'league': league,
                            'league_id': league_id,
                            'starting_at': starting_at,
                            'match_winner_prediction': match_winner_prediction,
                            'score_prediction': score_prediction
                        }
                        
                        matches_by_league[league].append(match_data)
                        print(f"Added {league}: {home_team} vs {away_team}")
                
                except Exception as e:
                    print(f"Error processing fixture: {e}")
                    continue
            
            # Display results
            print(f"\n" + "="*80)
            print(f"RESULTS: MATCHES BY LEAGUE")
            print("="*80)
            
            total_matches = 0
            for league in ['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1']:
                matches = matches_by_league[league]
                print(f"\n{league}: {len(matches)} matches")
                
                for i, match in enumerate(matches, 1):
                    print(f"  {i}. {match['match']}")
                    print(f"     Starting: {match['starting_at']}")
                    print(f"     League ID: {match['league_id']}")
                    if match['match_winner_prediction']:
                        pred = match['match_winner_prediction']
                        print(f"     Match Winner Prediction: Home {pred.get('home', 'N/A')}%, Draw {pred.get('draw', 'N/A')}%, Away {pred.get('away', 'N/A')}%")
                    else:
                        print(f"     Match Winner Prediction: Not available")
                    
                    if match['score_prediction']:
                        score_pred = match['score_prediction']
                        scores = score_pred.get('scores', {})
                        if scores:
                            # Show top 3 most likely scores
                            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
                            print(f"     Score Prediction: {', '.join([f'{score}: {prob}%' for score, prob in sorted_scores])}")
                        else:
                            print(f"     Score Prediction: Available but no scores data")
                    else:
                        print(f"     Score Prediction: Not available")
                
                total_matches += len(matches)
            
            print(f"\n" + "="*80)
            print(f"TOTAL: {total_matches} matches found")
            print("="*80)
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sportmonks_predictions_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(matches_by_league, f, indent=2, ensure_ascii=False)
            
            print(f"\nResults saved to: {filename}")
            
        else:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def get_league_name(league_id):
    """Get league name from league ID"""
    # Based on debug analysis:
    # League ID 8: Aston Villa vs Fulham (Premier League teams) - This is NOT La Liga!
    # League ID 82: TSG Hoffenheim vs SC Freiburg (Bundesliga teams)
    # League ID 384: Sassuolo vs Udinese (Serie A teams) 
    # League ID 301: Nice vs Paris (Ligue 1 teams)
    
    league_mapping = {
        564: 'La Liga',        # FOUND: 564 is La Liga (Real Madrid, Barcelona, etc.)
        8: 'Premier League',   # Confirmed: 8 is Premier League
        82: 'Bundesliga',      # Confirmed: 82 is Bundesliga
        384: 'Serie A',        # Confirmed: 384 is Serie A
        301: 'Ligue 1'         # Confirmed: 301 is Ligue 1
    }
    return league_mapping.get(league_id, 'Unknown')

if __name__ == "__main__":
    get_sportmonks_predictions()
