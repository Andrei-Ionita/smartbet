"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { 
  ThumbsUp, 
  ThumbsDown, 
  CheckCircle, 
  XCircle, 
  TrendingUp, 
  TrendingDown, 
  Clock,
  Target,
  BarChart3,
  Brain,
  Loader2 
} from "lucide-react";
import { cn } from "@/lib/utils";

// Interface for new prediction format from our multi-league system
interface LivePrediction {
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
  
  // New enhanced fields
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

interface LivePredictionCardProps {
  prediction: LivePrediction;
  rank?: number;
}

// Helper functions for styling and formatting
function getConfidenceLevel(confidence: number): 'HIGH' | 'MEDIUM' | 'LOW' {
  if (confidence >= 0.7) return 'HIGH';
  if (confidence >= 0.5) return 'MEDIUM';
  return 'LOW';
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'border-green-500 bg-green-50 text-green-700';
  if (confidence >= 0.5) return 'border-yellow-500 bg-yellow-50 text-yellow-700';
  return 'border-red-500 bg-red-50 text-red-700';
}

function getRecommendationColor(recommend: boolean): string {
  return recommend 
    ? 'border-green-500 bg-green-50 text-green-700' 
    : 'border-gray-300 bg-gray-50 text-gray-600';
}

function getModelStatusIcon(status: string): string {
  switch (status) {
    case 'PRODUCTION': return '✅';
    case 'EXPERIMENTAL': return '🔬';
    default: return '📊';
  }
}

function getLeagueFlag(league: string): string {
  const flags: Record<string, string> = {
    'La Liga': '🇪🇸',
    'Serie A': '🇮🇹',
    'Bundesliga': '🇩🇪',
    'Ligue 1': '🇫🇷',
    'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    'Liga 1': '🇷🇴'
  };
  return flags[league] || '⚽';
}

const LivePredictionCard: React.FC<LivePredictionCardProps> = ({ prediction, rank }) => {
  const [showModal, setShowModal] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState<"yes" | "no" | null>(null);

  const handleFeedback = (didBet: boolean) => {
    setFeedbackSent(didBet ? "yes" : "no");
    // In a real app, you'd send this feedback to the backend
    console.log(`Feedback for ${prediction.home_team} vs ${prediction.away_team}:`, didBet);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const confidenceLevel = getConfidenceLevel(prediction.confidence);
  const modelIcon = getModelStatusIcon(prediction.model_info.model_status);
  const leagueFlag = getLeagueFlag(prediction.league);
  const performance = prediction.model_info.model_performance;

  return (
    <>
      <div className={cn(
        "relative bg-gradient-to-br rounded-xl border shadow-lg transition-all hover:shadow-xl hover:scale-[1.02] duration-200",
        prediction.recommend 
          ? "from-green-50 to-emerald-50 border-green-200" 
          : "from-white to-gray-50 border-gray-200"
      )}>
        {/* Rank Badge */}
        {rank && (
          <div className="absolute -top-2 -left-2 bg-blue-600 text-white text-sm font-bold rounded-full w-8 h-8 flex items-center justify-center shadow-lg">
            {rank}
          </div>
        )}

        {/* Recommendation Badge */}
        <div className="absolute -top-2 -right-2">
          <Badge className={cn(
            "text-xs font-semibold px-2 py-1",
            prediction.recommend 
              ? "bg-green-500 text-white" 
              : "bg-gray-400 text-white"
          )}>
            {prediction.recommend ? "✔ BET" : "✖ SKIP"}
          </Badge>
        </div>
        
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h3 className="text-lg font-bold text-gray-900 mb-1">
                {prediction.home_team} vs {prediction.away_team}
              </h3>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <span className="flex items-center gap-1">
                  {leagueFlag} {prediction.league}
                </span>
                <span className="flex items-center gap-1">
                  {modelIcon} {prediction.model_info.model_status}
                </span>
              </div>
            </div>
            <Badge className={cn("text-xs font-semibold border", getConfidenceColor(prediction.confidence))}>
              🎯 {(prediction.confidence * 100).toFixed(0)}%
            </Badge>
          </div>

          {/* Prediction Details */}
          <div className="space-y-3 mb-5">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Prediction:</span>
              <span className="text-lg font-bold text-blue-600">
                {prediction.prediction}
              </span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Confidence:</span>
              <div className="flex items-center gap-2">
                <Badge className={cn("text-xs", getConfidenceColor(prediction.confidence))}>
                  {confidenceLevel}
                </Badge>
                <span className="text-sm font-semibold">
                  {(prediction.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Odds:</span>
              <span className="text-lg font-semibold text-gray-800">
                {prediction.predicted_odds.toFixed(2)}
              </span>
            </div>

            {/* Model Performance */}
            {(performance.hit_rate || performance.accuracy) && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Model Performance:</span>
                <span className="text-sm font-medium text-green-600">
                  {performance.hit_rate ? `${(performance.hit_rate * 100).toFixed(1)}% hit rate` :
                   performance.accuracy ? `${(performance.accuracy * 100).toFixed(1)}% accuracy` : 'N/A'}
                </span>
              </div>
            )}
          </div>

          {/* Recommendation Reason */}
          <div className="mb-5">
            <div className={cn(
              "rounded-lg p-3 text-sm border",
              getRecommendationColor(prediction.recommend)
            )}>
              <div className="flex items-start gap-2">
                {prediction.recommend ? 
                  <TrendingUp className="h-4 w-4 mt-0.5 flex-shrink-0" /> :
                  <TrendingDown className="h-4 w-4 mt-0.5 flex-shrink-0" />
                }
                <span>{prediction.recommendation_reason}</span>
              </div>
            </div>
          </div>

          {/* AI Reasoning */}
          {prediction.reasoning && (
            <div className="mb-5">
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide flex items-center gap-1">
                <Brain className="h-3 w-3" />
                AI Analysis
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                {prediction.reasoning}
              </div>
            </div>
          )}

          {/* Insights Alerts */}
          {prediction.insights?.alerts && prediction.insights.alerts.length > 0 && (
            <div className="mb-5">
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide flex items-center gap-1">
                <Target className="h-3 w-3" />
                Key Insights
              </div>
              <div className="space-y-1">
                {prediction.insights.alerts.map((alert, index) => (
                  <div 
                    key={index} 
                    className="text-xs p-2 rounded border-l-2 border-orange-400 bg-orange-50 text-orange-800"
                  >
                    {alert}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expected Value Highlight */}
          {prediction.insights?.expected_value && (
            <div className="mb-5">
              <div className="flex justify-between items-center p-3 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border">
                <span className="text-sm font-medium text-gray-700">Expected Value:</span>
                <span className={cn(
                  "text-lg font-bold",
                  parseFloat(prediction.insights.expected_value) > 0 ? "text-green-600" : "text-red-600"
                )}>
                  {prediction.insights.expected_value}
                </span>
              </div>
            </div>
          )}

          {/* All Probabilities */}
          <div className="mb-5">
            <div className="text-xs text-gray-500 mb-2 uppercase tracking-wide">All Outcomes</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-center">
                <div className="text-gray-600">Home</div>
                <div className="font-semibold">{(prediction.all_probabilities.home_win * 100).toFixed(1)}%</div>
                <div className="text-gray-500">{prediction.all_odds.home_win.toFixed(2)}</div>
              </div>
              <div className="text-center">
                <div className="text-gray-600">Draw</div>
                <div className="font-semibold">{(prediction.all_probabilities.draw * 100).toFixed(1)}%</div>
                <div className="text-gray-500">{prediction.all_odds.draw.toFixed(2)}</div>
              </div>
              <div className="text-center">
                <div className="text-gray-600">Away</div>
                <div className="font-semibold">{(prediction.all_probabilities.away_win * 100).toFixed(1)}%</div>
                <div className="text-gray-500">{prediction.all_odds.away_win.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <Button 
              variant="outline" 
              className="w-full border-blue-500 text-blue-600 hover:bg-blue-50"
              onClick={() => setShowModal(true)}
            >
              <Brain className="h-4 w-4 mr-2" />
              View Detailed Analysis
            </Button>

            {/* Feedback Section */}
            <div className="border-t pt-3">
              <p className="text-sm text-center text-gray-600 mb-3">
                Did you place this bet?
              </p>
              {!feedbackSent ? (
                <div className="flex space-x-3">
                  <Button 
                    variant="outline" 
                    className="w-full hover:bg-green-50 border-green-500 text-green-600"
                    onClick={() => handleFeedback(true)}
                  >
                    <ThumbsUp className="h-4 w-4 mr-2" />
                    Yes, I did!
                  </Button>
                  <Button 
                    variant="outline" 
                    className="w-full hover:bg-red-50 border-red-500 text-red-600"
                    onClick={() => handleFeedback(false)}
                  >
                    <ThumbsDown className="h-4 w-4 mr-2" />
                    No, skipped.
                  </Button>
                </div>
              ) : (
                <div className={cn(
                  "flex items-center justify-center p-3 rounded-md text-sm font-medium",
                  feedbackSent === "yes" 
                    ? "bg-green-100 text-green-700" 
                    : "bg-red-100 text-red-700"
                )}>
                  {feedbackSent === "yes" ? <CheckCircle className="h-4 w-4 mr-2" /> : <XCircle className="h-4 w-4 mr-2" />}
                  Thanks for your feedback!
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Analysis Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Detailed Match Analysis"
        className="max-w-4xl"
      >
        <div className="space-y-6">
          {/* Match Info */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Match Details</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="text-lg font-bold text-gray-900 mb-2">
                {leagueFlag} {prediction.home_team} vs {prediction.away_team}
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <div>League: {prediction.league}</div>
                <div>Model: {prediction.model_info.model_status}</div>
                <div>Prediction Time: {formatTimestamp(prediction.timestamp)}</div>
              </div>
            </div>
          </div>

          {/* AI Reasoning */}
          {prediction.reasoning && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">AI Reasoning</h4>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <Brain className="h-5 w-5 text-blue-600" />
                  <span className="font-semibold text-blue-900">Model Analysis</span>
                </div>
                <p className="text-sm text-blue-800 leading-relaxed">
                  {prediction.reasoning}
                </p>
              </div>
            </div>
          )}

          {/* Prediction Analysis */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Prediction Summary</h4>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-3 mb-3">
                <Target className="h-5 w-5 text-green-600" />
                <span className="font-semibold text-green-900">
                  Recommended: {prediction.prediction}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm text-green-800">
                <div>Confidence: {(prediction.confidence * 100).toFixed(1)}%</div>
                <div>Odds: {prediction.predicted_odds.toFixed(2)}</div>
                <div>Expected Value: {prediction.insights?.expected_value || 'N/A'}</div>
                <div>Recommendation: {prediction.recommend ? 'BET' : 'SKIP'}</div>
              </div>
            </div>
          </div>

          {/* Key Insights */}
          {prediction.insights?.alerts && prediction.insights.alerts.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Key Insights & Alerts</h4>
              <div className="space-y-2">
                {prediction.insights.alerts.map((alert, index) => (
                  <div 
                    key={index}
                    className="flex items-start gap-2 p-3 bg-orange-50 border border-orange-200 rounded-lg"
                  >
                    <div className="text-orange-600 mt-0.5">●</div>
                    <span className="text-sm text-orange-800">{alert}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Match Statistics */}
          {prediction.insights && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Match Statistics</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Team Stats */}
                {(prediction.insights.home_win_rate || prediction.insights.away_win_rate) && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h5 className="font-medium text-gray-800 mb-3">Team Performance</h5>
                    <div className="space-y-2 text-sm">
                      {prediction.insights.home_win_rate && (
                        <div className="flex justify-between">
                          <span>Home Win Rate:</span>
                          <span className="font-medium">{prediction.insights.home_win_rate}</span>
                        </div>
                      )}
                      {prediction.insights.away_win_rate && (
                        <div className="flex justify-between">
                          <span>Away Win Rate:</span>
                          <span className="font-medium">{prediction.insights.away_win_rate}</span>
                        </div>
                      )}
                      {prediction.insights.win_rate_diff && (
                        <div className="flex justify-between">
                          <span>Win Rate Difference:</span>
                          <span className="font-medium">{prediction.insights.win_rate_diff}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Form & Attack Stats */}
                {(prediction.insights.home_recent_form || prediction.insights.home_attack) && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h5 className="font-medium text-gray-800 mb-3">Form & Attack</h5>
                    <div className="space-y-2 text-sm">
                      {prediction.insights.home_recent_form && (
                        <div className="flex justify-between">
                          <span>Home Form:</span>
                          <span className="font-medium">{prediction.insights.home_recent_form}</span>
                        </div>
                      )}
                      {prediction.insights.away_recent_form && (
                        <div className="flex justify-between">
                          <span>Away Form:</span>
                          <span className="font-medium">{prediction.insights.away_recent_form}</span>
                        </div>
                      )}
                      {prediction.insights.home_attack && (
                        <div className="flex justify-between">
                          <span>Home Attack:</span>
                          <span className="font-medium">{prediction.insights.home_attack}</span>
                        </div>
                      )}
                      {prediction.insights.away_attack && (
                        <div className="flex justify-between">
                          <span>Away Attack:</span>
                          <span className="font-medium">{prediction.insights.away_attack}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Market Analysis (for Serie A) */}
                {(prediction.insights.market_efficiency || prediction.insights.bookmaker_margin) && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h5 className="font-medium text-gray-800 mb-3">Market Analysis</h5>
                    <div className="space-y-2 text-sm">
                      {prediction.insights.market_efficiency && (
                        <div className="flex justify-between">
                          <span>Market Efficiency:</span>
                          <span className="font-medium">{prediction.insights.market_efficiency}</span>
                        </div>
                      )}
                      {prediction.insights.bookmaker_margin && (
                        <div className="flex justify-between">
                          <span>Bookmaker Margin:</span>
                          <span className="font-medium">{prediction.insights.bookmaker_margin}</span>
                        </div>
                      )}
                      {prediction.insights.most_likely_outcome && (
                        <div className="flex justify-between">
                          <span>Market Favorite:</span>
                          <span className="font-medium">{prediction.insights.most_likely_outcome}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Implied Probabilities */}
                {(prediction.insights.home_implied_prob) && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h5 className="font-medium text-gray-800 mb-3">Market Probabilities</h5>
                    <div className="space-y-2 text-sm">
                      {prediction.insights.home_implied_prob && (
                        <div className="flex justify-between">
                          <span>Home Implied:</span>
                          <span className="font-medium">{prediction.insights.home_implied_prob}</span>
                        </div>
                      )}
                      {prediction.insights.draw_implied_prob && (
                        <div className="flex justify-between">
                          <span>Draw Implied:</span>
                          <span className="font-medium">{prediction.insights.draw_implied_prob}</span>
                        </div>
                      )}
                      {prediction.insights.away_implied_prob && (
                        <div className="flex justify-between">
                          <span>Away Implied:</span>
                          <span className="font-medium">{prediction.insights.away_implied_prob}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Probability Breakdown */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Probability Analysis</h4>
            <div className="space-y-3">
              {[
                { outcome: 'Home Win', prob: prediction.all_probabilities.home_win, odds: prediction.all_odds.home_win },
                { outcome: 'Draw', prob: prediction.all_probabilities.draw, odds: prediction.all_odds.draw },
                { outcome: 'Away Win', prob: prediction.all_probabilities.away_win, odds: prediction.all_odds.away_win }
              ].map(({ outcome, prob, odds }) => (
                <div key={outcome} className="flex items-center justify-between bg-gray-50 rounded p-3">
                  <span className="font-medium">{outcome}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm">
                      {(prob * 100).toFixed(1)}% probability
                    </span>
                    <span className="text-sm font-semibold">
                      {odds.toFixed(2)} odds
                    </span>
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `${prob * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Performance */}
          {performance && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Model Performance</h4>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {performance.hit_rate && (
                    <div>
                      <div className="text-gray-600">Hit Rate</div>
                      <div className="font-semibold text-green-700">
                        {(performance.hit_rate * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                  {performance.roi && (
                    <div>
                      <div className="text-gray-600">ROI</div>
                      <div className="font-semibold text-green-700">
                        {performance.roi > 0 ? '+' : ''}{performance.roi.toFixed(1)}%
                      </div>
                    </div>
                  )}
                  {performance.accuracy && (
                    <div>
                      <div className="text-gray-600">Accuracy</div>
                      <div className="font-semibold text-green-700">
                        {(performance.accuracy * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-gray-600">Confidence Threshold</div>
                    <div className="font-semibold text-gray-700">
                      {(prediction.model_info.confidence_threshold * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
};

export default LivePredictionCard; 