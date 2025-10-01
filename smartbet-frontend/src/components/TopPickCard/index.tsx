"use client";

import React, { useState } from 'react';
import type { Prediction } from "@/types/prediction";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { useFeedback } from "@/hooks/useFeedback";
import { 
  ThumbsUp, 
  ThumbsDown, 
  CheckCircle, 
  XCircle, 
  Info,
  Clock,
  Target,
  TrendingUp,
  Loader2 
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TopPickCardProps {
  prediction: Prediction;
  rank: number;
}

// Utility functions for betting intelligence
function getEVBadge(ev: number) {
  if (ev > 0.05) return { text: 'Great Value', emoji: '🟢', color: 'text-green-600 bg-green-50 border-green-200' };
  if (ev >= 0) return { text: 'Neutral', emoji: '🟡', color: 'text-yellow-600 bg-yellow-50 border-yellow-200' };
  return { text: 'Negative EV', emoji: '🔴', color: 'text-red-600 bg-red-50 border-red-200' };
}

function getConfidenceBadge(level: string) {
  // Normalize the confidence level to uppercase to handle case variations
  const normalizedLevel = level?.toUpperCase();
  const badges = {
    HIGH: { text: 'High', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
    MEDIUM: { text: 'Medium', color: 'text-yellow-600 bg-yellow-50 border-yellow-200' },
    LOW: { text: 'Low', color: 'text-orange-600 bg-orange-50 border-orange-200' },
  };
  return badges[normalizedLevel as keyof typeof badges] ?? { text: 'Unknown', color: 'text-gray-600 bg-gray-50 border-gray-200' };
}

function getRecommendedBetDisplay(prediction: Prediction): string {
  const outcome = prediction.score.predicted_outcome?.toUpperCase();
  const homeTeam = prediction.match.home_team.name;
  const awayTeam = prediction.match.away_team.name;
  
  switch(outcome) {
    case 'HOME_WIN':
    case 'HOME':
      return `${homeTeam} to Win`;
    case 'AWAY_WIN':
    case 'AWAY':
      return `${awayTeam} to Win`;
    case 'DRAW':
      return 'Draw';
    default:
      return outcome || 'Unknown';
  }
}

function getBestOddsForOutcome(prediction: Prediction) {
  const { odds_home, odds_draw, odds_away, bookmaker } = prediction.score.odds_snapshot;
  const outcome = prediction.score.predicted_outcome?.toUpperCase();
  
  let selectedOdds;
  switch(outcome) {
    case 'HOME_WIN':
    case 'HOME':
      selectedOdds = odds_home;
      break;
    case 'AWAY_WIN':
    case 'AWAY':
      selectedOdds = odds_away;
      break;
    case 'DRAW':
      selectedOdds = odds_draw;
      break;
    default:
      selectedOdds = Math.max(odds_home || 0, odds_draw || 0, odds_away || 0);
  }
  
  return { 
    odds: selectedOdds || 0, 
    bookmaker: bookmaker || 'Unknown' 
  };
}

const TopPickCard: React.FC<TopPickCardProps> = ({ prediction, rank }) => {
  const [feedbackSent, setFeedbackSent] = useState<"yes" | "no" | null>(null);
  const [showModal, setShowModal] = useState(false);
  const { mutate: submitFeedback, isPending } = useFeedback();

  // Debug logging for prediction data
  console.log(`🎯 TopPickCard #${rank} rendering with prediction:`, {
    id: prediction.id,
    homeTeam: prediction.match.home_team.name,
    awayTeam: prediction.match.away_team.name,
    league: prediction.match.league,
    predictedOutcome: prediction.score.predicted_outcome,
    expectedValue: prediction.score.expected_value,
    confidence: prediction.score.confidence_level,
    odds: prediction.score.odds_snapshot,
    explanation: prediction.explanation
  });

  const handleFeedback = (didBet: boolean) => {
    setFeedbackSent(didBet ? "yes" : "no");
    submitFeedback({
      predictionId: prediction.id,
      didBet: didBet,
    });
  };

  const formatKickoffTime = (time: string) => {
    const date = new Date(time);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  const formatKickoffDate = (time: string) => {
    const date = new Date(time);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  const evValue = prediction.score.expected_value;
  const confidenceLevel = prediction.score.confidence_level;
  const evInfo = getEVBadge(evValue);
  const confidenceInfo = getConfidenceBadge(confidenceLevel);
  const recommendedBet = getRecommendedBetDisplay(prediction);
  const { odds, bookmaker } = getBestOddsForOutcome(prediction);
  const teamsDisplay = `${prediction.match.home_team.name} vs ${prediction.match.away_team.name}`;

  return (
    <>
      <div className="relative bg-gradient-to-br from-white to-gray-50 rounded-xl border border-gray-200 shadow-lg transition-all hover:shadow-xl hover:scale-[1.02] duration-200">
        {/* Rank Badge */}
        <div className="absolute -top-2 -left-2 bg-blue-600 text-white text-sm font-bold rounded-full w-8 h-8 flex items-center justify-center shadow-lg">
          {rank}
        </div>
        
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h3 className="text-lg font-bold text-gray-900 mb-1">
                {teamsDisplay}
              </h3>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <span className="font-medium">{prediction.match.league}</span>
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatKickoffDate(prediction.match.kickoff_time)} {formatKickoffTime(prediction.match.kickoff_time)}</span>
                </div>
              </div>
            </div>
            <Badge className={cn("text-xs font-semibold border", confidenceInfo.color)}>
              {confidenceLevel === 'HIGH' ? '🔐' : confidenceLevel === 'MEDIUM' ? '🤔' : '❓'} {confidenceInfo.text}
            </Badge>
          </div>

          {/* Bet Details */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-800">Recommended Bet</span>
            </div>
            <div className="text-lg font-bold text-blue-900 mb-2">{recommendedBet}</div>
            <div className="flex justify-between items-center">
              <div>
                <span className="text-sm text-blue-700">Odds:</span>
                <span className="ml-2 font-semibold text-blue-900">
                  {odds.toFixed(2)} {bookmaker && `(${bookmaker})`}
                </span>
              </div>
              <Badge className={cn("font-semibold border", evInfo.color)}>
                {evInfo.emoji} {evInfo.text}
              </Badge>
            </div>
          </div>

          {/* Expected Value */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-gray-600" />
              <span className="text-sm text-gray-600">Expected Value:</span>
            </div>
            <span className={cn("font-bold", evValue >= 0 ? 'text-green-600' : 'text-red-600')}>
              {evValue >= 0 ? '+' : ''}{(evValue * 100).toFixed(1)}%
            </span>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            {/* Why This Bet Button */}
            <Button 
              variant="outline" 
              className="w-full border-blue-200 text-blue-700 hover:bg-blue-50"
              onClick={() => setShowModal(true)}
            >
              <Info className="h-4 w-4 mr-2" />
              Why this bet?
            </Button>

            {/* Feedback Buttons */}
            {!feedbackSent ? (
              <div className="flex space-x-2">
                <Button 
                  variant="outline" 
                  className="w-full hover:bg-green-50 border-green-500 text-green-600"
                  onClick={() => handleFeedback(true)} 
                  disabled={isPending}
                >
                  {isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <ThumbsUp className="h-4 w-4 mr-2" />
                  )}
                  ✅ Placed bet
                </Button>
                <Button 
                  variant="outline" 
                  className="w-full hover:bg-red-50 border-red-500 text-red-600"
                  onClick={() => handleFeedback(false)} 
                  disabled={isPending}
                >
                  {isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <ThumbsDown className="h-4 w-4 mr-2" />
                  )}
                  ❌ Skipped
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

      {/* Modal for bet reasoning */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Why This Bet?"
        className="max-w-lg"
      >
        <div className="space-y-4">
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Match Analysis</h4>
            <p className="text-gray-700 text-sm">
              {teamsDisplay} in {prediction.match.league}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {formatKickoffDate(prediction.match.kickoff_time)} at {formatKickoffTime(prediction.match.kickoff_time)}
            </p>
          </div>
          
          {prediction.explanation ? (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Model Explanation</h4>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-sm text-blue-900">{prediction.explanation}</p>
              </div>
            </div>
          ) : (
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Model Analysis</h4>
              <p className="text-sm text-gray-700">
                Our AI model has analyzed this match and recommends betting on{' '}
                <strong>{recommendedBet}</strong> based on statistical patterns and team performance.
              </p>
            </div>
          )}
          
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Prediction Confidence</h4>
            <div className="flex items-center gap-2">
              <Badge className={cn("text-xs border", confidenceInfo.color)}>
                {confidenceLevel === 'HIGH' ? '🔐' : confidenceLevel === 'MEDIUM' ? '🤔' : '❓'} {confidenceInfo.text} Confidence
              </Badge>
              <span className="text-sm text-gray-600">
                Model certainty: {confidenceLevel.toLowerCase()}
              </span>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Expected Value Analysis</h4>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <p className="text-sm text-gray-700">
                This bet has an expected value of{' '}
                <span className={cn("font-semibold", evValue >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {evValue >= 0 ? '+' : ''}{(evValue * 100).toFixed(1)}%
                </span>
                {evValue > 0.05 && " - which represents excellent value and strong profit potential."}
                {evValue > 0 && evValue <= 0.05 && " - which is close to fair value with modest profit potential."}
                {evValue < 0 && " - which suggests the odds are not favorable for long-term profit."}
              </p>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Betting Recommendation</h4>
            <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <Target className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-blue-900">
                <strong>Bet:</strong> {recommendedBet} at <strong>{odds.toFixed(2)}</strong>
                {bookmaker && ` (${bookmaker})`}
              </span>
            </div>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default TopPickCard; 