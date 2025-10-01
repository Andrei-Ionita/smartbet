"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import PredictionPanel from "@/components/PredictionPanel";
import { Plus, RefreshCw, Star, Search, Zap } from "lucide-react";

// Sample match data for demonstration
const recommendedMatches = [
  {
    league: "La Liga",
    home_team: "Real Madrid",
    away_team: "Barcelona",
    home_win_odds: 2.10,
    draw_odds: 3.40,
    away_win_odds: 3.60,
    home_recent_form: 1.8,
    away_recent_form: 1.6,
    home_win_rate: 0.85,
    away_win_rate: 0.75
  },
  {
    league: "Serie A",
    home_team: "Juventus",
    away_team: "AC Milan",
    home_win_odds: 2.25,
    draw_odds: 3.20,
    away_win_odds: 3.40,
    recent_form_home: 1.7,
    recent_form_away: 1.4
  },
  {
    league: "Premier League",
    home_team: "Manchester City",
    away_team: "Liverpool",
    home_win_odds: 2.05,
    draw_odds: 3.50,
    away_win_odds: 3.75,
    home_avg_goals_for: 2.3,
    away_avg_goals_for: 2.1
  }
];

const userSelectedMatches = [
  {
    league: "Bundesliga",
    home_team: "Bayern Munich",
    away_team: "Borussia Dortmund",
    home_win_odds: 1.85,
    draw_odds: 3.80,
    away_win_odds: 4.20,
    home_win_rate: 0.78,
    away_win_rate: 0.65
  },
  {
    league: "Ligue 1",
    home_team: "Paris Saint-Germain",
    away_team: "Olympique Marseille",
    home_win_odds: 1.65,
    draw_odds: 4.00,
    away_win_odds: 5.50,
    home_win_rate: 0.82,
    away_win_rate: 0.45
  },
  // Unsupported league example
  {
    league: "Eredivisie",
    home_team: "Ajax",
    away_team: "PSV Eindhoven",
    home_win_odds: 2.20,
    draw_odds: 3.30,
    away_win_odds: 3.50
  }
];

// Sample predictions (simulating API responses)
const samplePredictions = [
  {
    league: "La Liga",
    home_team: "Real Madrid",
    away_team: "Barcelona",
    prediction: "Home Win" as const,
    confidence: 0.78,
    predicted_odds: 2.10,
    recommend: true,
    recommendation_reason: "Strong home advantage and superior recent form",
    all_probabilities: {
      home_win: 0.52,
      away_win: 0.28,
      draw: 0.20
    },
    all_odds: {
      home_win: 2.10,
      away_win: 3.60,
      draw: 3.40
    },
    model_info: {
      model_performance: {
        hit_rate: 0.744,
        roi: 138.92,
        accuracy: 0.744
      },
      confidence_threshold: 0.6,
      odds_threshold: 1.5,
      model_status: "PRODUCTION"
    },
    timestamp: new Date().toISOString(),
    reasoning: "The model predicts a Real Madrid victory due to their strong home record (85% win rate) and excellent recent form against Barcelona's good away form (75% win rate). The model shows high confidence (78%) with excellent betting value (model sees 52% vs market's 48%).",
    insights: {
      home_win_rate: "85.0%",
      away_win_rate: "75.0%",
      home_recent_form: "Excellent (W-W-W)",
      away_recent_form: "Good (W-W-D)",
      home_attack: "2.8 goals/game",
      home_defense: "0.9 conceded/game",
      away_attack: "2.4 goals/game",
      away_defense: "1.1 conceded/game",
      recent_form_diff: "+0.2",
      expected_value: "+34.2%",
      alerts: ["🔥 Excellent value bet opportunity!", "🏠 Strong home team advantage", "⚽ High-scoring match expected"]
    }
  },
  {
    league: "Serie A",
    home_team: "Juventus",
    away_team: "AC Milan",
    prediction: "Away Win" as const,
    confidence: 0.67,
    predicted_odds: 3.40,
    recommend: false,
    recommendation_reason: "Confidence below threshold despite favorable odds",
    all_probabilities: {
      home_win: 0.35,
      away_win: 0.42,
      draw: 0.23
    },
    all_odds: {
      home_win: 2.25,
      away_win: 3.40,
      draw: 3.20
    },
    model_info: {
      model_performance: {
        hit_rate: 0.615,
        roi: -9.10,
        accuracy: 0.615
      },
      confidence_threshold: 0.7,
      odds_threshold: 1.8,
      model_status: "PRODUCTION"
    },
    timestamp: new Date().toISOString(),
    reasoning: "The model predicts an AC Milan victory based on market efficiency analysis and recent form indicators. However, confidence is relatively low (67%) due to Juventus' strong home defensive record.",
    insights: {
      market_efficiency: "94.2%",
      bookmaker_margin: "6.2%",
      home_implied_prob: "44.4%",
      draw_implied_prob: "31.3%",
      away_implied_prob: "29.4%",
      most_likely_outcome: "Home",
      expected_value: "-8.5%",
      alerts: ["⚠️ Poor value - odds too low", "📉 Low confidence prediction", "⚖️ Balanced market odds"]
    }
  },
  {
    league: "Bundesliga",
    home_team: "Bayern Munich",
    away_team: "Borussia Dortmund",
    prediction: "Home Win" as const,
    confidence: 0.82,
    predicted_odds: 1.85,
    recommend: true,
    recommendation_reason: "High confidence prediction with strong home advantage",
    all_probabilities: {
      home_win: 0.65,
      away_win: 0.22,
      draw: 0.13
    },
    all_odds: {
      home_win: 1.85,
      away_win: 4.20,
      draw: 3.80
    },
    model_info: {
      model_performance: {
        hit_rate: 0.687,
        roi: 45.3,
        accuracy: 0.687
      },
      confidence_threshold: 0.6,
      odds_threshold: 1.5,
      model_status: "PRODUCTION"
    },
    timestamp: new Date().toISOString(),
    reasoning: "The model predicts a Bayern Munich victory due to their exceptional home record (78% win rate) and superior attacking prowess. Very high confidence (82%) with decent betting value despite low odds.",
    insights: {
      home_win_rate: "78.0%",
      away_win_rate: "65.0%",
      home_attack: "2.8 goals/game",
      away_attack: "2.2 goals/game",
      win_rate_diff: "+13.0%",
      expected_value: "+20.3%",
      alerts: ["🎯 Very high model confidence", "🏠 Strong home team advantage", "✅ Good betting value detected"]
    }
  }
];

export default function PredictionsPage() {
  const [loadingPredictions, setLoadingPredictions] = useState(false);
  const [predictions, setPredictions] = useState(samplePredictions);
  const [customMatches, setCustomMatches] = useState(userSelectedMatches);

  const handlePredictionRequest = async (match: any) => {
    setLoadingPredictions(true);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Add a new prediction (simulate API response)
    const newPrediction = {
      league: match.league,
      home_team: match.home_team,
      away_team: match.away_team,
      prediction: "Draw" as const,
      confidence: 0.61,
      predicted_odds: match.draw_odds,
      recommend: false,
      recommendation_reason: "Moderate confidence with neutral expected value",
      all_probabilities: {
        home_win: 0.35,
        away_win: 0.32,
        draw: 0.33
      },
      all_odds: {
        home_win: match.home_win_odds,
        away_win: match.away_win_odds,
        draw: match.draw_odds
      },
      model_info: {
        model_performance: {
          hit_rate: 0.60,
          roi: 15.3,
          accuracy: 0.60
        },
        confidence_threshold: 0.65,
        odds_threshold: 1.8,
        model_status: "PRODUCTION"
      },
      timestamp: new Date().toISOString(),
      reasoning: "The model predicts a draw due to evenly matched teams and similar recent form. Confidence is moderate (61%) suggesting a tight contest.",
      insights: {
        home_win_rate: "65.0%",
        away_win_rate: "70.0%",
        win_rate_diff: "-5.0%",
        expected_value: "+2.1%",
        alerts: ["⚠️ Evenly matched teams", "📊 Moderate confidence prediction"]
      }
    };
    
    setPredictions(prev => [...prev, newPrediction]);
    setLoadingPredictions(false);
  };

  const handleRefresh = () => {
    // Simulate refresh
    console.log("Refreshing predictions...");
  };

  const addCustomMatch = () => {
    // For demo purposes, add a new custom match
    const newMatch = {
      league: "Premier League",
      home_team: "Arsenal",
      away_team: "Chelsea",
      home_win_odds: 2.30,
      draw_odds: 3.20,
      away_win_odds: 3.10,
      home_avg_goals_for: 2.1,
      away_avg_goals_for: 1.9
    };
    setCustomMatches(prev => [...prev, newMatch]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-6 gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-2 rounded-lg">
                  <Zap className="h-6 w-6" />
                </div>
                Prediction Dashboard
              </h1>
              <p className="text-gray-600 mt-1">
                AI-powered betting predictions with enhanced insights and analysis
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <Button
                onClick={handleRefresh}
                variant="outline"
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
              <Button
                onClick={addCustomMatch}
                className="bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Add Match
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Recommended Matches Section */}
          <PredictionPanel
            matches={recommendedMatches}
            predictions={predictions.filter(p => 
              recommendedMatches.some(m => 
                m.home_team === p.home_team && 
                m.away_team === p.away_team &&
                m.league === p.league
              )
            )}
            isRecommended={true}
            title="🌟 Recommended Matches"
            onPredictionRequest={handlePredictionRequest}
            loading={loadingPredictions}
          />

          {/* User Selected Matches Section */}
          <PredictionPanel
            matches={customMatches}
            predictions={predictions.filter(p => 
              customMatches.some(m => 
                m.home_team === p.home_team && 
                m.away_team === p.away_team &&
                m.league === p.league
              )
            )}
            isRecommended={false}
            title="🎯 Your Custom Matches"
            onPredictionRequest={handlePredictionRequest}
            loading={loadingPredictions}
          />

          {/* Features Overview */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              🚀 Enhanced Prediction Features
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="font-semibold text-blue-900 mb-2">🎯 Outcome Prediction</div>
                <div className="text-blue-700">
                  Clear prediction with confidence scores and color-coded badges
                </div>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="font-semibold text-green-900 mb-2">💸 Expected Value</div>
                <div className="text-green-700">
                  Real-time EV calculation with visual indicators
                </div>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <div className="font-semibold text-purple-900 mb-2">🧠 AI Reasoning</div>
                <div className="text-purple-700">
                  Natural language explanations for every prediction
                </div>
              </div>
              <div className="bg-orange-50 rounded-lg p-4">
                <div className="font-semibold text-orange-900 mb-2">📊 Smart Insights</div>
                <div className="text-orange-700">
                  Collapsible match statistics and automated alerts
                </div>
              </div>
            </div>
          </div>

          {/* Supported Leagues Info */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              🏆 Supported Leagues
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-lg">🏴󠁧󠁢󠁥󠁮󠁧󠁿</span>
                <span>Premier League</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🇪🇸</span>
                <span>La Liga</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🇮🇹</span>
                <span>Serie A</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🇩🇪</span>
                <span>Bundesliga</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🇫🇷</span>
                <span>Ligue 1</span>
              </div>
            </div>
            <p className="text-gray-600 mt-3 text-sm">
              Each league uses specialized models trained on historical data with league-specific features and performance metrics.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
} 