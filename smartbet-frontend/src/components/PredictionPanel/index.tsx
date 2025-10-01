"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { 
  TrendingUp, 
  TrendingDown, 
  ChevronDown, 
  ChevronUp,
  Target,
  Brain,
  AlertCircle,
  Star,
  Trophy,
  Activity,
  BarChart3,
  Zap,
  CheckCircle,
  XCircle,
  Clock,
  Info
} from "lucide-react";
import { cn } from "@/lib/utils";

// Supported leagues with trained models
const SUPPORTED_LEAGUES = [
  'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1'
];

// Match data interface
interface MatchData {
  league: string;
  home_team: string;
  away_team: string;
  home_win_odds: number;
  draw_odds: number;
  away_win_odds: number;
  [key: string]: any; // For additional features
}

// Prediction interface (from our API)
interface Prediction {
  league: string;
  home_team: string;
  away_team: string;
  prediction: "Home Win" | "Away Win" | "Draw";
  confidence: number;
  predicted_odds: number;
  recommend: boolean;
  recommendation_reason: string;
  all_probabilities: {
    home_win: number;
    away_win: number;
    draw: number;
  };
  all_odds: {
    home_win: number;
    away_win: number;
    draw: number;
  };
  model_info: {
    model_performance: {
      hit_rate?: number;
      roi?: number;
      accuracy?: number;
    };
    confidence_threshold: number;
    odds_threshold: number;
    model_status: string;
  };
  timestamp: string;
  reasoning: string;
  insights: {
    home_win_rate?: string;
    away_win_rate?: string;
    home_recent_form?: string;
    away_recent_form?: string;
    home_attack?: string;
    home_defense?: string;
    away_attack?: string;
    away_defense?: string;
    recent_form_diff?: string;
    market_efficiency?: string;
    bookmaker_margin?: string;
    home_implied_prob?: string;
    draw_implied_prob?: string;
    away_implied_prob?: string;
    most_likely_outcome?: string;
    win_rate_diff?: string;
    expected_value: string;
    alerts: string[];
  };
}

interface PredictionPanelProps {
  matches: MatchData[];
  predictions?: Prediction[];
  isRecommended?: boolean;
  title: string;
  onPredictionRequest?: (match: MatchData) => void;
  loading?: boolean;
}

// Helper functions
function isLeagueSupported(league: string): boolean {
  return SUPPORTED_LEAGUES.some(supportedLeague => 
    league.toLowerCase().includes(supportedLeague.toLowerCase()) ||
    supportedLeague.toLowerCase().includes(league.toLowerCase())
  );
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-green-500 text-white";
  if (confidence >= 0.65) return "bg-yellow-500 text-white";
  return "bg-red-500 text-white";
}

function getConfidenceLevel(confidence: number): string {
  if (confidence >= 0.8) return "HIGH";
  if (confidence >= 0.65) return "MEDIUM";
  return "LOW";
}

function getEVColor(ev: string): string {
  const numericEV = parseFloat(ev.replace('%', ''));
  if (numericEV > 5) return "text-green-600 bg-green-50 border-green-200";
  if (numericEV > 0) return "text-green-600 bg-green-50 border-green-200";
  if (numericEV >= -5) return "text-yellow-600 bg-yellow-50 border-yellow-200";
  return "text-red-600 bg-red-50 border-red-200";
}

function getEVIcon(ev: string): string {
  const numericEV = parseFloat(ev.replace('%', ''));
  if (numericEV > 5) return "🔥";
  if (numericEV > 0) return "✅";
  if (numericEV >= -5) return "⚠️";
  return "❌";
}

function getLeagueFlag(league: string): string {
  const leagueMap: { [key: string]: string } = {
    'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    'La Liga': '🇪🇸',
    'Serie A': '🇮🇹',
    'Bundesliga': '🇩🇪',
    'Ligue 1': '🇫🇷'
  };
  
  for (const [leagueName, flag] of Object.entries(leagueMap)) {
    if (league.toLowerCase().includes(leagueName.toLowerCase()) ||
        leagueName.toLowerCase().includes(league.toLowerCase())) {
      return flag;
    }
  }
  return '⚽';
}

// Individual match prediction component
const MatchPredictionCard: React.FC<{
  match: MatchData;
  prediction?: Prediction;
  isRecommended?: boolean;
  onPredictionRequest?: (match: MatchData) => void;
  loading?: boolean;
}> = ({ match, prediction, isRecommended, onPredictionRequest, loading }) => {
  const [showInsights, setShowInsights] = useState(false);
  const [showDetailedModal, setShowDetailedModal] = useState(false);
  
  const isSupported = isLeagueSupported(match.league);
  const leagueFlag = getLeagueFlag(match.league);
  
  // If league is not supported, show placeholder
  if (!isSupported) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {match.home_team} vs {match.away_team}
            </h3>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>{leagueFlag} {match.league}</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              Prediction unavailable for this league
            </h4>
            <p className="text-sm text-gray-600">
              This league is not yet supported by our trained models.
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Supported leagues: {SUPPORTED_LEAGUES.join(', ')}
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  // If no prediction available, show loading or request button
  if (!prediction) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {match.home_team} vs {match.away_team}
            </h3>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>{leagueFlag} {match.league}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Odds:</span>
            <span className="text-sm font-medium">{match.home_win_odds}</span>
            <span className="text-sm font-medium">{match.draw_odds}</span>
            <span className="text-sm font-medium">{match.away_win_odds}</span>
          </div>
        </div>
        
        <div className="flex items-center justify-center py-6">
          <Button
            onClick={() => onPredictionRequest?.(match)}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                Generating Prediction...
              </>
            ) : (
              <>
                <Brain className="h-4 w-4 mr-2" />
                Get AI Prediction
              </>
            )}
          </Button>
        </div>
      </div>
    );
  }
  
  // Full prediction display
  return (
    <>
      <div className={cn(
        "bg-gradient-to-br rounded-xl border shadow-lg transition-all hover:shadow-xl duration-200",
        prediction.recommend && isRecommended
          ? "from-green-50 to-emerald-50 border-green-200"
          : "from-white to-gray-50 border-gray-200"
      )}>
        {/* Recommended badge */}
        {isRecommended && prediction.recommend && (
          <div className="absolute -top-2 -right-2">
            <Badge className="bg-green-500 text-white text-xs font-semibold px-2 py-1">
              <Star className="h-3 w-3 mr-1" />
              Recommended
            </Badge>
          </div>
        )}
        
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">
                {match.home_team} vs {match.away_team}
              </h3>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <span className="flex items-center gap-1">
                  {leagueFlag} {match.league}
                </span>
                <span className="flex items-center gap-1">
                  <Trophy className="h-3 w-3" />
                  {prediction.model_info.model_status}
                </span>
              </div>
            </div>
          </div>
          
          {/* 🎯 Outcome Prediction */}
          <div className="mb-5">
            <div className="flex items-center gap-2 mb-3">
              <Target className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-semibold text-gray-700">Outcome Prediction</span>
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-lg font-bold text-blue-900">
                  {prediction.prediction}
                </span>
                <div className="flex items-center gap-2">
                  <Badge className={cn("text-xs font-semibold", getConfidenceColor(prediction.confidence))}>
                    {getConfidenceLevel(prediction.confidence)}
                  </Badge>
                  <span className="text-sm font-semibold text-blue-800">
                    {(prediction.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-blue-700">Predicted Odds:</span>
                <span className="text-lg font-bold text-blue-900">
                  {prediction.predicted_odds.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
          
          {/* 💸 Expected Value */}
          <div className="mb-5">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-sm font-semibold text-gray-700">Expected Value</span>
            </div>
            
            <div className={cn(
              "border rounded-lg p-4 flex items-center justify-between",
              getEVColor(prediction.insights.expected_value)
            )}>
              <div className="flex items-center gap-2">
                <span className="text-lg">{getEVIcon(prediction.insights.expected_value)}</span>
                <span className="font-semibold">Expected Value</span>
              </div>
              <span className="text-xl font-bold">
                {prediction.insights.expected_value}
              </span>
            </div>
          </div>
          
          {/* 📊 Insights Section (Collapsible) */}
          <div className="mb-5">
            <button
              onClick={() => setShowInsights(!showInsights)}
              className="flex items-center justify-between w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-gray-600" />
                <span className="text-sm font-semibold text-gray-700">Match Insights</span>
              </div>
              {showInsights ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            
            {showInsights && (
              <div className="mt-3 space-y-3">
                {/* AI Reasoning */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Brain className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-semibold text-blue-800">AI Reasoning</span>
                  </div>
                  <p className="text-sm text-blue-700 leading-relaxed">
                    {prediction.reasoning}
                  </p>
                </div>
                
                {/* Key Statistics */}
                <div className="grid grid-cols-2 gap-3">
                  {prediction.insights.home_win_rate && (
                    <div className="bg-gray-50 rounded p-3">
                      <div className="text-xs text-gray-600 mb-1">Home Win Rate</div>
                      <div className="font-semibold">{prediction.insights.home_win_rate}</div>
                    </div>
                  )}
                  {prediction.insights.away_win_rate && (
                    <div className="bg-gray-50 rounded p-3">
                      <div className="text-xs text-gray-600 mb-1">Away Win Rate</div>
                      <div className="font-semibold">{prediction.insights.away_win_rate}</div>
                    </div>
                  )}
                  {prediction.insights.home_recent_form && (
                    <div className="bg-gray-50 rounded p-3">
                      <div className="text-xs text-gray-600 mb-1">Home Form</div>
                      <div className="font-semibold">{prediction.insights.home_recent_form}</div>
                    </div>
                  )}
                  {prediction.insights.away_recent_form && (
                    <div className="bg-gray-50 rounded p-3">
                      <div className="text-xs text-gray-600 mb-1">Away Form</div>
                      <div className="font-semibold">{prediction.insights.away_recent_form}</div>
                    </div>
                  )}
                </div>
                
                {/* Alerts */}
                {prediction.insights.alerts && prediction.insights.alerts.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs text-gray-600 uppercase tracking-wide">Alerts</div>
                    {prediction.insights.alerts.map((alert, index) => (
                      <div 
                        key={index}
                        className="flex items-start gap-2 p-2 bg-orange-50 border border-orange-200 rounded text-sm text-orange-800"
                      >
                        <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        <span>{alert}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Action Button */}
          <Button
            onClick={() => setShowDetailedModal(true)}
            variant="outline"
            className="w-full border-blue-500 text-blue-600 hover:bg-blue-50"
          >
            <Activity className="h-4 w-4 mr-2" />
            View Full Analysis
          </Button>
        </div>
      </div>
      
      {/* Detailed Analysis Modal */}
      <Modal
        isOpen={showDetailedModal}
        onClose={() => setShowDetailedModal(false)}
        title="Complete Match Analysis"
        className="max-w-4xl"
      >
        <div className="space-y-6">
          {/* Match Header */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4">
            <div className="text-xl font-bold text-gray-900 mb-2">
              {leagueFlag} {match.home_team} vs {match.away_team}
            </div>
            <div className="text-sm text-gray-600 space-y-1">
              <div>League: {match.league}</div>
              <div>Model: {prediction.model_info.model_status}</div>
              <div>Analysis Time: {new Date(prediction.timestamp).toLocaleString()}</div>
            </div>
          </div>
          
          {/* Prediction Summary */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <Target className="h-5 w-5 text-green-600" />
              <span className="font-semibold text-green-900">Prediction: {prediction.prediction}</span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Confidence: </span>
                <span className="font-semibold">{(prediction.confidence * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-gray-600">Odds: </span>
                <span className="font-semibold">{prediction.predicted_odds.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-600">Expected Value: </span>
                <span className="font-semibold">{prediction.insights.expected_value}</span>
              </div>
              <div>
                <span className="text-gray-600">Recommendation: </span>
                <span className="font-semibold">{prediction.recommend ? 'BET' : 'SKIP'}</span>
              </div>
            </div>
          </div>
          
          {/* AI Reasoning */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <Brain className="h-5 w-5 text-blue-600" />
              <span className="font-semibold text-blue-900">AI Analysis</span>
            </div>
            <p className="text-sm text-blue-800 leading-relaxed">
              {prediction.reasoning}
            </p>
          </div>
          
          {/* All Probabilities */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Probability Breakdown</h4>
            <div className="space-y-3">
              {[
                { outcome: 'Home Win', prob: prediction.all_probabilities.home_win, odds: prediction.all_odds.home_win },
                { outcome: 'Draw', prob: prediction.all_probabilities.draw, odds: prediction.all_odds.draw },
                { outcome: 'Away Win', prob: prediction.all_probabilities.away_win, odds: prediction.all_odds.away_win }
              ].map(({ outcome, prob, odds }) => (
                <div key={outcome} className="flex items-center justify-between bg-gray-50 rounded p-3">
                  <span className="font-medium">{outcome}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm">{(prob * 100).toFixed(1)}%</span>
                    <span className="text-sm font-semibold">{odds.toFixed(2)}</span>
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${prob * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Model Performance */}
          {prediction.model_info.model_performance && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h4 className="font-semibold text-gray-900 mb-3">Model Performance</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                {prediction.model_info.model_performance.hit_rate && (
                  <div>
                    <div className="text-gray-600">Hit Rate</div>
                    <div className="font-semibold text-green-700">
                      {(prediction.model_info.model_performance.hit_rate * 100).toFixed(1)}%
                    </div>
                  </div>
                )}
                {prediction.model_info.model_performance.roi && (
                  <div>
                    <div className="text-gray-600">ROI</div>
                    <div className="font-semibold text-green-700">
                      {prediction.model_info.model_performance.roi > 0 ? '+' : ''}{prediction.model_info.model_performance.roi.toFixed(1)}%
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
};

// Main PredictionPanel component
const PredictionPanel: React.FC<PredictionPanelProps> = ({
  matches,
  predictions = [],
  isRecommended = false,
  title,
  onPredictionRequest,
  loading = false
}) => {
  const [expandedSection, setExpandedSection] = useState(true);
  
  if (matches.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8">
        <div className="text-center">
          <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No matches available</h3>
          <p className="text-gray-600">
            {isRecommended ? 'No recommended matches found at this time.' : 'Add matches to get predictions.'}
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setExpandedSection(!expandedSection)}
          className="flex items-center gap-3 text-left"
        >
          <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
          {expandedSection ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {matches.length} match{matches.length !== 1 ? 'es' : ''}
          </Badge>
          {isRecommended && (
            <Badge className="bg-green-500 text-white text-xs">
              <Star className="h-3 w-3 mr-1" />
              Recommended
            </Badge>
          )}
        </div>
      </div>
      
      {/* Matches Grid */}
      {expandedSection && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {matches.map((match, index) => {
            const matchPrediction = predictions.find(p => 
              p.home_team === match.home_team && 
              p.away_team === match.away_team &&
              p.league === match.league
            );
            
            return (
              <div key={`${match.home_team}-${match.away_team}-${index}`} className="relative">
                <MatchPredictionCard
                  match={match}
                  prediction={matchPrediction}
                  isRecommended={isRecommended}
                  onPredictionRequest={onPredictionRequest}
                  loading={loading}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PredictionPanel; 