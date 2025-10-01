"""
Tests for the Pinnacle odds fetcher module.
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from core.models import Match, Team, League, OddsSnapshot
from odds.fetch_pinnacle import (
    process_pinnacle_odds,
    american_to_decimal,
    store_odds,
    fetch_pinnacle_odds
)


class AmericanToDecimalTestCase(unittest.TestCase):
    """Test the American to decimal odds conversion function."""
    
    def test_positive_american_odds(self):
        """Test conversion of positive American odds."""
        self.assertEqual(american_to_decimal(100), 2.00)
        self.assertEqual(american_to_decimal(200), 3.00)
        self.assertEqual(american_to_decimal(150), 2.50)
    
    def test_negative_american_odds(self):
        """Test conversion of negative American odds."""
        self.assertEqual(american_to_decimal(-100), 2.00)
        self.assertEqual(american_to_decimal(-200), 1.50)
        self.assertEqual(american_to_decimal(-150), 1.67)


class ProcessPinnacleOddsTestCase(unittest.TestCase):
    """Test the process_pinnacle_odds function."""
    
    def test_process_valid_data(self):
        """Test processing of valid Pinnacle API response."""
        # Sample API response
        sample_data = {
            "leagues": [
                {
                    "id": 123,
                    "events": [
                        {
                            "id": "fixture1",
                            "periods": [
                                {
                                    "number": 0,
                                    "moneyline": {
                                        "home": 150,
                                        "draw": 250,
                                        "away": -120
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = process_pinnacle_odds(sample_data)
        
        self.assertEqual(len(result), 1)
        odds = result[0]
        self.assertEqual(odds["fixture_id"], "fixture1")
        self.assertEqual(odds["league_id"], 123)
        self.assertEqual(odds["odds_home"], 2.50)
        self.assertEqual(odds["odds_draw"], 3.50)
        self.assertEqual(odds["odds_away"], 1.83)
        self.assertEqual(odds["bookmaker"], "Pinnacle")
        self.assertEqual(odds["market_type"], "Match Winner")
    
    def test_process_missing_moneyline(self):
        """Test processing when moneyline market is missing."""
        # Sample API response with missing moneyline
        sample_data = {
            "leagues": [
                {
                    "id": 123,
                    "events": [
                        {
                            "id": "fixture1",
                            "periods": [
                                {
                                    "number": 0,
                                    # No moneyline here
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = process_pinnacle_odds(sample_data)
        self.assertEqual(len(result), 0)  # Should skip this fixture
    
    def test_process_incomplete_odds(self):
        """Test processing when some odds are missing."""
        # Sample API response with incomplete odds
        sample_data = {
            "leagues": [
                {
                    "id": 123,
                    "events": [
                        {
                            "id": "fixture1",
                            "periods": [
                                {
                                    "number": 0,
                                    "moneyline": {
                                        "home": 150,
                                        # Missing "draw"
                                        "away": -120
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        result = process_pinnacle_odds(sample_data)
        self.assertEqual(len(result), 0)  # Should skip this fixture


class StoreOddsTestCase(TestCase):
    """Test the store_odds function."""
    
    def setUp(self):
        """Set up test data."""
        # Create test leagues
        self.league = League.objects.create(
            name_ro="Liga 1",
            name_en="League 1",
            country="Romania",
            api_id=123
        )
        
        # Create test teams
        self.home_team = Team.objects.create(
            name_ro="Echipa Acasa",
            name_en="Home Team",
            slug="home-team"
        )
        
        self.away_team = Team.objects.create(
            name_ro="Echipa Deplasare",
            name_en="Away Team",
            slug="away-team"
        )
        
        # Create test match
        self.match = Match.objects.create(
            league=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            kickoff=timezone.now() + timezone.timedelta(days=1),
            status="NS",
            api_ref="fixture1"
        )
    
    def test_store_odds(self):
        """Test storing odds data."""
        odds_data = [
            {
                "fixture_id": "fixture1",
                "league_id": 123,
                "odds_home": 2.50,
                "odds_draw": 3.50,
                "odds_away": 1.83,
                "bookmaker": "Pinnacle",
                "market_type": "Match Winner",
                "fetched_at": timezone.now()
            }
        ]
        
        # Initial count
        initial_count = OddsSnapshot.objects.count()
        
        # Store odds
        stored = store_odds(odds_data)
        
        # Check that one record was stored
        self.assertEqual(stored, 1)
        self.assertEqual(OddsSnapshot.objects.count(), initial_count + 1)
        
        # Check the stored data
        snapshot = OddsSnapshot.objects.latest('fetched_at')
        self.assertEqual(snapshot.match, self.match)
        self.assertEqual(snapshot.bookmaker, "Pinnacle")
        self.assertEqual(snapshot.odds_home, 2.50)
        self.assertEqual(snapshot.odds_draw, 3.50)
        self.assertEqual(snapshot.odds_away, 1.83)


class FetchPinnacleOddsTestCase(TestCase):
    """Test the fetch_pinnacle_odds function."""
    
    @patch('odds.fetch_pinnacle.requests.Session')
    def test_fetch_pinnacle_odds(self, mock_session):
        """Test fetching odds from Pinnacle API."""
        # Mock environment variables
        with patch.dict('os.environ', {
            'PINNACLE_USERNAME': 'testuser',
            'PINNACLE_PASSWORD': 'testpass'
        }):
            # Mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "leagues": [
                    {
                        "id": 123,
                        "events": [
                            {
                                "id": "fixture1",
                                "periods": [
                                    {
                                        "number": 0,
                                        "moneyline": {
                                            "home": 150,
                                            "draw": 250,
                                            "away": -120
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            
            # Mock session get method
            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = mock_response
            mock_session.return_value = mock_session_instance
            
            # Mock store_odds function
            with patch('odds.fetch_pinnacle.store_odds') as mock_store_odds:
                mock_store_odds.return_value = 1
                
                # Execute function under test
                result = fetch_pinnacle_odds()
                
                # Assertions
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["fixture_id"], "fixture1")
                self.assertEqual(result[0]["odds_home"], 2.50)
                
                # Check that the correct API URL was called
                mock_session_instance.get.assert_called_once()
                call_args = mock_session_instance.get.call_args[0][0]
                self.assertIn("odds", call_args)


if __name__ == '__main__':
    unittest.main() 