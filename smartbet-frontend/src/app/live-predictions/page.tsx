"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import LivePredictionCard from "@/components/LivePredictionCard";
import { 
  useLivePredictionWorkflow, 
  useModelStatus, 
  useSupportedLeagues,
  useLiveAPIHealth 
} from "@/hooks/useLivePredictions";
import { 
  Plus, 
  Trash2, 
  Zap, 
  TrendingUp, 
  AlertCircle, 
  RefreshCw,
  Brain,
  BarChart3,
  CheckCircle,
  XCircle,
  Loader2
} from "lucide-react";
import { cn } from "@/lib/utils";

// Example matches for quick testing
const exampleMatches = [
  {
    league: "La Liga",
    home_team: "Real Madrid",
    away_team: "Barcelona",
    home_win_odds: 2.10,
    draw_odds: 3.40,
    away_win_odds: 3.60,
    home_recent_form: 1.8,
    away_recent_form: 1.6
  },
  {
    league: "Serie A", 
    home_team: "Juventus",
    away_team: "AC Milan",
    home_win_odds: 2.25,
    draw_odds: 3.20,
    away_win_odds: 3.40
  },
  {
    league: "Bundesliga",
    home_team: "Bayern Munich", 
    away_team: "Borussia Dortmund",
    home_win_odds: 1.85,
    draw_odds: 3.80,
    away_win_odds: 4.20
  },
  {
    league: "Premier League",
    home_team: "Manchester City",
    away_team: "Liverpool",
    home_win_odds: 2.05,
    draw_odds: 3.50,
    away_win_odds: 3.75
  },
  {
    league: "Ligue 1",
    home_team: "Paris Saint-Germain",
    away_team: "Olympique Marseille", 
    home_win_odds: 1.65,
    draw_odds: 4.00,
    away_win_odds: 5.50
  }
];

interface MatchFormData {
  league: string;
  home_team: string;
  away_team: string;
  home_win_odds: string;
  draw_odds: string;
  away_win_odds: string;
}

const LivePredictionsPage: React.FC = () => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState<MatchFormData>({
    league: "",
    home_team: "",
    away_team: "",
    home_win_odds: "",
    draw_odds: "",
    away_win_odds: ""
  });

  const workflow = useLivePredictionWorkflow();
  const modelStatus = useModelStatus();
  const supportedLeagues = useSupportedLeagues();
  const apiHealth = useLiveAPIHealth();

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.league || !formData.home_team || !formData.away_team ||
        !formData.home_win_odds || !formData.draw_odds || !formData.away_win_odds) {
      alert("Please fill in all required fields");
      return;
    }

    const match = {
      league: formData.league,
      home_team: formData.home_team,
      away_team: formData.away_team,
      home_win_odds: parseFloat(formData.home_win_odds),
      draw_odds: parseFloat(formData.draw_odds),
      away_win_odds: parseFloat(formData.away_win_odds)
    };

    workflow.addMatch(match);
    setFormData({
      league: "",
      home_team: "",
      away_team: "",
      home_win_odds: "",
      draw_odds: "",
      away_win_odds: ""
    });
    setShowAddForm(false);
  };

  const addExampleMatch = (match: typeof exampleMatches[0]) => {
    workflow.addMatch(match);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      default: return 'text-red-600';
    }
  };

  const getModelStatusIcon = (status: string) => {
    switch (status) {
      case 'PRODUCTION': return '✅';
      case 'EXPERIMENTAL': return '🔬';
      default: return '📊';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                🚀 Live Predictions
              </h1>
              <p className="text-lg text-gray-600">
                Multi-league AI-powered betting predictions with real-time model selection
              </p>
            </div>
            
            {/* API Health Status */}
            <div className="text-right">
              <div className="flex items-center gap-2 mb-1">
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  apiHealth.data?.status === 'healthy' ? 'bg-green-500' :
                  apiHealth.data?.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                )} />
                <span className={cn(
                  "text-sm font-medium",
                  getStatusColor(apiHealth.data?.status || 'unknown')
                )}>
                  {apiHealth.isLoading ? 'Checking...' : 
                   apiHealth.data?.status === 'healthy' ? 'Live API Active' :
                   apiHealth.data?.status === 'degraded' ? 'Limited Service' : 'API Offline'}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                {modelStatus.data ? `${modelStatus.data.total_leagues} leagues available` : 'Loading...'}
              </div>
            </div>
          </div>

          {/* System Status Bar */}
          <div className="bg-white rounded-lg border p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Brain className="h-6 w-6 text-blue-600" />
                <div>
                  <div className="font-semibold text-gray-900">Prediction Engine Status</div>
                  <div className="text-sm text-gray-600">
                    {modelStatus.isLoading ? 'Loading model status...' :
                     modelStatus.data ? `${modelStatus.data.system_status} - ${modelStatus.data.total_leagues} leagues` :
                     'Model status unavailable'}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {workflow.hasMatches && (
                  <Badge variant="outline" className="text-blue-600 border-blue-600">
                    {workflow.matchCount} matches selected
                  </Badge>
                )}
                {workflow.predictionCount > 0 && (
                  <Badge variant="outline" className="text-green-600 border-green-600">
                    {workflow.recommendedBets}/{workflow.predictionCount} bets recommended
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Left Column - Match Selection */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Add Matches
              </h2>

              {/* Quick Add Examples */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-700 mb-3">Quick Add Examples</h3>
                <div className="space-y-2">
                  {exampleMatches.map((match, index) => (
                    <button
                      key={index}
                      onClick={() => addExampleMatch(match)}
                      className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="font-medium text-sm">{match.home_team} vs {match.away_team}</div>
                      <div className="text-xs text-gray-500">{match.league}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Match Form */}
              <div>
                <Button
                  onClick={() => setShowAddForm(!showAddForm)}
                  variant="outline"
                  className="w-full mb-4"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Custom Match
                </Button>

                {showAddForm && (
                  <form onSubmit={handleFormSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        League
                      </label>
                      <select
                        value={formData.league}
                        onChange={(e) => setFormData({...formData, league: e.target.value})}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                        required
                      >
                        <option value="">Select League</option>
                        <option value="La Liga">🇪🇸 La Liga</option>
                        <option value="Serie A">🇮🇹 Serie A</option>
                        <option value="Bundesliga">🇩🇪 Bundesliga</option>
                        <option value="Premier League">🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League</option>
                        <option value="Ligue 1">🇫🇷 Ligue 1</option>
                        <option value="Liga 1">🇷🇴 Liga 1</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Home Team
                        </label>
                        <input
                          type="text"
                          value={formData.home_team}
                          onChange={(e) => setFormData({...formData, home_team: e.target.value})}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Away Team
                        </label>
                        <input
                          type="text"
                          value={formData.away_team}
                          onChange={(e) => setFormData({...formData, away_team: e.target.value})}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Home Odds
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={formData.home_win_odds}
                          onChange={(e) => setFormData({...formData, home_win_odds: e.target.value})}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Draw Odds
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={formData.draw_odds}
                          onChange={(e) => setFormData({...formData, draw_odds: e.target.value})}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Away Odds
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          value={formData.away_win_odds}
                          onChange={(e) => setFormData({...formData, away_win_odds: e.target.value})}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                          required
                        />
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <Button type="submit" className="flex-1">
                        Add Match
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setShowAddForm(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </form>
                )}
              </div>

              {/* Selected Matches */}
              {workflow.hasMatches && (
                <div className="mt-6 pt-6 border-t">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-semibold text-gray-700">
                      Selected Matches ({workflow.matchCount})
                    </h3>
                    <Button
                      onClick={workflow.clearMatches}
                      variant="outline"
                      size="sm"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="space-y-2 mb-4">
                    {workflow.selectedMatches.map((match, index) => (
                      <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                        <div className="text-sm">
                          <div className="font-medium">{match.home_team} vs {match.away_team}</div>
                          <div className="text-gray-500">{match.league}</div>
                        </div>
                        <Button
                          onClick={() => workflow.removeMatch(index)}
                          variant="outline"
                          size="sm"
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>

                  <Button
                    onClick={workflow.predictSelectedMatches}
                    disabled={workflow.isLoading}
                    className="w-full"
                  >
                    {workflow.isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4 mr-2" />
                        Get Predictions
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>

            {/* Model Status Summary */}
            {modelStatus.data && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Model Status
                </h3>
                <div className="space-y-3">
                  {Object.entries(modelStatus.data.leagues).map(([key, league]) => (
                    <div key={key} className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{getModelStatusIcon(league.status)}</span>
                        <span className="text-sm font-medium">{league.name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        {league.is_loaded ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs text-gray-500">
                          {league.is_loaded ? 'Ready' : 'Error'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Predictions */}
          <div className="lg:col-span-2">
            {workflow.error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  <span className="font-medium text-red-700">Prediction Error</span>
                </div>
                <p className="text-red-600 text-sm mt-1">{workflow.error}</p>
              </div>
            )}

            {workflow.predictionCount > 0 ? (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">
                    Predictions ({workflow.predictionCount})
                  </h2>
                  <div className="flex items-center gap-4">
                    <Badge variant="outline" className="text-green-600 border-green-600">
                      {workflow.recommendedBets} recommended bets
                    </Badge>
                    <Badge variant="outline">
                      {Math.round((workflow.recommendedBets / workflow.predictionCount) * 100)}% success rate
                    </Badge>
                  </div>
                </div>

                <div className="grid gap-6">
                  {workflow.currentPredictions.map((prediction, index) => (
                    <LivePredictionCard
                      key={`${prediction.home_team}-${prediction.away_team}`}
                      prediction={prediction}
                      rank={prediction.recommend ? index + 1 : undefined}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-lg p-8 text-center">
                <TrendingUp className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-600 mb-2">
                  No Predictions Yet
                </h3>
                <p className="text-gray-500 mb-6">
                  Add some matches and click "Get Predictions" to see AI-powered betting recommendations.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>6 leagues supported</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>Real-time model selection</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>Confidence-based filtering</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>Value betting recommendations</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LivePredictionsPage; 