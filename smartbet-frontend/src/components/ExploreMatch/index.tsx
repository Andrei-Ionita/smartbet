"use client";

import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  fetchCustomPrediction, 
  fetchLeagues, 
  fetchMatches,
  type CustomPredictionRequest,
  type CustomPredictionResponse 
} from "@/lib/api";
import { 
  Loader2, 
  Search, 
  Target, 
  TrendingUp, 
  AlertTriangle,
  BookOpen,
  Activity
} from "lucide-react";
import { cn } from "@/lib/utils";

function getEVBadge(ev: number | null) {
  if (ev === null) return { text: 'N/A', emoji: '⚪', color: 'text-gray-600 bg-gray-50 border-gray-200' };
  if (ev > 0) return { text: 'Positive EV', emoji: '🟢', color: 'text-green-600 bg-green-50 border-green-200' };
  if (ev >= -0.02) return { text: 'Neutral', emoji: '🟡', color: 'text-yellow-600 bg-yellow-50 border-yellow-200' };
  return { text: 'Negative EV', emoji: '🔴', color: 'text-red-600 bg-red-50 border-red-200' };
}

const outcomeLabels = {
  home: 'Home Win',
  draw: 'Draw', 
  away: 'Away Win'
};

const ExploreMatch: React.FC = () => {
  const [leagues, setLeagues] = useState<string[]>([]);
  const [matches, setMatches] = useState<string[]>([]);
  const [formData, setFormData] = useState<CustomPredictionRequest>({
    league: '',
    match: ''
  });
  const [prediction, setPrediction] = useState<CustomPredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingLeagues, setIsLoadingLeagues] = useState(true);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [error, setError] = useState<string>('');

  // Load leagues on component mount
  useEffect(() => {
    const loadLeagues = async () => {
      try {
        const leagueData = await fetchLeagues();
        setLeagues(leagueData);
      } catch (err) {
        setError('Failed to load leagues');
      } finally {
        setIsLoadingLeagues(false);
      }
    };
    
    loadLeagues();
  }, []);

  // Load matches when league changes
  useEffect(() => {
    if (formData.league) {
      const loadMatches = async () => {
        setIsLoadingMatches(true);
        try {
          const matchData = await fetchMatches(formData.league);
          setMatches(matchData);
          setFormData(prev => ({ ...prev, match: '' })); // Reset match selection
        } catch (err) {
          setError('Failed to load matches for this league');
          setMatches([]);
        } finally {
          setIsLoadingMatches(false);
        }
      };
      
      loadMatches();
    } else {
      setMatches([]);
      setFormData(prev => ({ ...prev, match: '' }));
    }
  }, [formData.league]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.league || !formData.match) {
      setError('Please select a league and match');
      return;
    }

    setIsLoading(true);
    setError('');
    setPrediction(null);
    
    try {
      const result = await fetchCustomPrediction(formData);
      setPrediction(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get prediction');
      setPrediction(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* League Dropdown */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            League
          </label>
          {isLoadingLeagues ? (
            <div className="h-10 bg-gray-100 rounded-md flex items-center px-3">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-sm text-gray-500">Loading leagues...</span>
            </div>
          ) : (
            <select
              value={formData.league}
              onChange={(e) => setFormData(prev => ({ ...prev, league: e.target.value }))}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option value="">Select a league</option>
              {leagues.map((league) => (
                <option key={league} value={league}>
                  {league}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Match Dropdown */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Match
          </label>
          {isLoadingMatches ? (
            <div className="h-10 bg-gray-100 rounded-md flex items-center px-3">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              <span className="text-sm text-gray-500">Loading matches...</span>
            </div>
          ) : (
            <select
              value={formData.match}
              onChange={(e) => setFormData(prev => ({ ...prev, match: e.target.value }))}
              className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={!formData.league || matches.length === 0}
              required
            >
              <option value="">
                {!formData.league 
                  ? "Select a league first" 
                  : matches.length === 0 
                    ? "No matches available" 
                    : "Select a match"
                }
              </option>
              {matches.map((match) => (
                <option key={match} value={match}>
                  {match}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Submit Button */}
        <Button 
          type="submit" 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3"
          disabled={isLoading}
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Analyzing Match...
            </>
          ) : (
            <>
              <Search className="h-4 w-4 mr-2" />
              Analyze All Outcomes
            </>
          )}
        </Button>
      </form>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Prediction Results */}
      {prediction && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-6 space-y-6">
          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 mb-2">Match Analysis</h3>
            <p className="text-sm text-gray-600">
              {prediction.match_info.home_team} vs {prediction.match_info.away_team}
            </p>
            <p className="text-xs text-gray-500">
              {new Date(prediction.match_info.kickoff).toLocaleDateString()} • {prediction.bookmaker}
            </p>
            {/* Show note if odds are not available */}
            {!prediction.odds_available && prediction.note && (
              <div className="mt-2 text-xs text-orange-600 bg-orange-50 border border-orange-200 rounded px-2 py-1">
                ℹ️ {prediction.note}
              </div>
            )}
          </div>

          {/* Outcomes Comparison Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(["home", "draw", "away"] as const).map((outcome) => {
              const isRecommended = outcome === prediction.predicted_outcome;
              const evValue = prediction.expected_values[outcome];
              const evInfo = getEVBadge(evValue);
              
              return (
                <div 
                  key={outcome} 
                  className={cn(
                    "border rounded-lg p-4 relative",
                    isRecommended 
                      ? "border-green-500 bg-green-50 shadow-md" 
                      : "border-gray-200 bg-white"
                  )}
                >
                  {isRecommended && (
                    <div className="absolute -top-2 -right-2">
                      <Badge className="bg-green-500 text-white text-xs px-2 py-1">
                        🏆 Best Bet
                      </Badge>
                    </div>
                  )}
                  
                  <div className="text-center">
                    <h4 className={cn(
                      "font-semibold text-lg mb-3",
                      isRecommended ? "text-green-800" : "text-gray-800"
                    )}>
                      {outcomeLabels[outcome]}
                    </h4>
                    
                    <div className="space-y-2">
                      {/* Probability */}
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Probability</p>
                        <p className="text-lg font-bold text-blue-600">
                          {(prediction.probabilities[outcome] * 100).toFixed(1)}%
                        </p>
                      </div>
                      
                      {/* Odds - only show if available */}
                      {prediction.odds_available && prediction.odds ? (
                        <div>
                          <p className="text-xs text-gray-500 uppercase tracking-wide">Odds</p>
                          <p className="text-lg font-semibold text-gray-800">
                            {prediction.odds[outcome].toFixed(2)}
                          </p>
                        </div>
                      ) : (
                        <div>
                          <p className="text-xs text-gray-500 uppercase tracking-wide">Odds</p>
                          <p className="text-lg font-semibold text-gray-400">
                            N/A
                          </p>
                        </div>
                      )}
                      
                      {/* Expected Value - handle null values */}
                      <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Expected Value</p>
                        <div className="flex items-center justify-center gap-2">
                          {evValue !== null ? (
                            <p className={cn(
                              "text-lg font-bold",
                              evValue > 0 ? "text-green-600" : evValue < -0.02 ? "text-red-600" : "text-yellow-600"
                            )}>
                              {evValue > 0 ? '+' : ''}{(evValue * 100).toFixed(2)}%
                            </p>
                          ) : (
                            <p className="text-lg font-bold text-gray-400">
                              N/A
                            </p>
                          )}
                          <Badge 
                            className={cn("text-xs", evInfo.color)}
                            title={evValue === null ? "No odds available — EV cannot be calculated" : undefined}
                          >
                            {evInfo.emoji}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Model Recommendation */}
          <div className="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-5 w-5 text-blue-600" />
              <span className="font-semibold text-blue-900">Model Recommendation</span>
            </div>
            <div className="text-lg font-bold text-green-700 mb-2">
              📈 Best Bet: {outcomeLabels[prediction.predicted_outcome as keyof typeof outcomeLabels]}
            </div>
            <div className="text-sm text-gray-700 mb-2">
              <strong>Confidence:</strong> {prediction.confidence} ({(prediction.confidence_score * 100).toFixed(1)}%)
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">
              {prediction.explanation}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExploreMatch; 