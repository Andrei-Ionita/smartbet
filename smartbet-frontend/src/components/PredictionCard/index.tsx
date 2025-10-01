"use client";

import React, { useState } from 'react';
import type { Prediction } from "@/types/prediction";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useFeedback } from "@/hooks/useFeedback";
import { 
  ThumbsUp, 
  ThumbsDown, 
  CheckCircle, 
  XCircle, 
  TrendingUp, 
  TrendingDown, 
  MinusCircle, 
  Loader2 
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PredictionCardProps {
  prediction: Prediction;
}

// Utility functions for betting intelligence
function getEVBadge(ev: number) {
  if (ev > 0.05) return '💰 Excellent';
  if (ev > 0.01) return '✅ Good';
  if (ev > -0.01) return '➖ Neutral';
  return '❌ Avoid';
}

function getConfidenceBadge(level: string) {
  // Normalize the confidence level to uppercase to handle case variations
  const normalizedLevel = level?.toUpperCase();
  return {
    HIGH: '🟢 HIGH',
    MEDIUM: '🟡 MEDIUM',
    LOW: '🟠 LOW',
  }[normalizedLevel] ?? '❓ Unknown';
}

function getEVColor(ev: number) {
  if (ev > 0.05) return 'text-green-600 bg-green-50 border-green-200';
  if (ev > 0.01) return 'text-lime-600 bg-lime-50 border-lime-200';
  if (ev > -0.01) return 'text-gray-600 bg-gray-50 border-gray-200';
  return 'text-red-600 bg-red-50 border-red-200';
}

function getConfidenceColor(level: string) {
  const normalizedLevel = level?.toUpperCase();
  const colors = {
    HIGH: 'text-emerald-600 bg-emerald-50 border-emerald-200',
    MEDIUM: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    LOW: 'text-orange-600 bg-orange-50 border-orange-200',
  };
  return colors[normalizedLevel as keyof typeof colors] ?? 'text-gray-600 bg-gray-50 border-gray-200';
}

function formatPredictedOutcome(outcome: string): string {
  const normalizedOutcome = outcome?.toUpperCase();
  const outcomes = {
    'HOME_WIN': 'Home Win',
    'HOME': 'Home Win',
    'AWAY_WIN': 'Away Win', 
    'AWAY': 'Away Win',
    'DRAW': 'Draw',
  };
  return outcomes[normalizedOutcome as keyof typeof outcomes] ?? outcome;
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
      return formatPredictedOutcome(outcome || 'Unknown');
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

const PredictionCard: React.FC<PredictionCardProps> = ({ prediction }) => {
  const [feedbackSent, setFeedbackSent] = useState<"yes" | "no" | null>(null);
  const { mutate: submitFeedback, isPending } = useFeedback();

  const handleFeedback = (didBet: boolean) => {
    setFeedbackSent(didBet ? "yes" : "no");
    submitFeedback({
      predictionId: prediction.id,
      didBet: didBet,
    });
  };

  const formatKickoffTime = (time: string) => {
    return new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  const evValue = prediction.score.expected_value;
  const confidenceLevel = prediction.score.confidence_level;
  const evBadge = getEVBadge(evValue);
  const confidenceBadge = getConfidenceBadge(confidenceLevel);
  const recommendedBet = getRecommendedBetDisplay(prediction);
  const { odds, bookmaker } = getBestOddsForOutcome(prediction);
  const teamsDisplay = `${prediction.match.home_team.name} vs ${prediction.match.away_team.name}`;

  return (
    <div className="rounded-xl border bg-card text-card-foreground shadow-lg transition-all hover:shadow-xl dark:shadow-primary/10">
      <div className="p-6">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              {teamsDisplay}
            </h3>
            <p className="text-sm text-muted-foreground">
              {prediction.match.league} - {formatKickoffTime(prediction.match.kickoff_time)}
            </p>
          </div>
          <Badge 
            className={cn("text-xs font-semibold border", getConfidenceColor(confidenceLevel))}
            title="Confidence level based on model certainty and historical performance"
          >
            {confidenceLevel === 'HIGH' ? '🔐' : confidenceLevel === 'MEDIUM' ? '🤔' : '❓'} {confidenceBadge}
          </Badge>
        </div>

        <div className="my-4 border-t border-border -mx-6"></div>

        <div className="space-y-3 mb-5">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Bet:</span>
            <span className="text-md font-semibold text-primary">
              {recommendedBet}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Odds:</span>
            <span className="text-md font-semibold">
              {odds.toFixed(2)} {bookmaker && `(${bookmaker})`}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Expected Value:</span>
            <Badge 
              variant="outline" 
              className={cn("font-semibold text-sm border", getEVColor(evValue))}
              title="Expected Value: positive means profitable long-term, negative means avoid"
            >
              {evValue >= 0 ? '+' : ''}{(evValue * 100).toFixed(1)}% {evBadge}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Confidence:</span>
            <Badge 
              variant="outline" 
              className={cn("font-semibold text-sm border", getConfidenceColor(confidenceLevel))}
              title="Model confidence based on data quality and historical accuracy"
            >
              {confidenceBadge}
            </Badge>
          </div>
        </div>
        
        <div className="mt-6 pt-4 border-t border-border">
          <p className="text-sm text-center text-muted-foreground mb-3">
            Did you place this bet?
          </p>
          {!feedbackSent ? (
            <div className="flex space-x-3">
              <Button 
                variant="outline" 
                className="w-full hover:bg-green-50 dark:hover:bg-green-900/50 border-green-500 text-green-600 dark:text-green-400 dark:border-green-700"
                onClick={() => handleFeedback(true)} 
                disabled={isPending}
              >
                {isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Loading...
                  </>
                ) : (
                  <>
                    <ThumbsUp className="h-4 w-4 mr-2" />
                    Yes, I did!
                  </>
                )}
              </Button>
              <Button 
                variant="outline" 
                className="w-full hover:bg-red-50 dark:hover:bg-red-900/50 border-red-500 text-red-600 dark:text-red-400 dark:border-red-700"
                onClick={() => handleFeedback(false)} 
                disabled={isPending}
              >
                {isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Loading...
                  </>
                ) : (
                  <>
                    <ThumbsDown className="h-4 w-4 mr-2" />
                    No, skipped.
                  </>
                )}
              </Button>
            </div>
          ) : (
            <div className={cn(
              "flex items-center justify-center p-3 rounded-md text-sm font-medium",
              feedbackSent === "yes" 
                ? "bg-green-100 dark:bg-green-800/30 text-green-700 dark:text-green-300" 
                : "bg-red-100 dark:bg-red-800/30 text-red-700 dark:text-red-300"
            )}>
              {feedbackSent === "yes" ? <CheckCircle className="h-5 w-5 mr-2" /> : <XCircle className="h-5 w-5 mr-2" />}
              Thanks for your feedback!
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PredictionCard; 