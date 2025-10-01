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

  const getConfidenceColor = (confidence: Prediction['confidence']) => {
    switch (confidence) {
      case "HIGH":
        return "bg-emerald-500 hover:bg-emerald-600";
      case "MEDIUM":
        return "bg-yellow-500 hover:bg-yellow-600";
      case "LOW":
        return "bg-orange-500 hover:bg-orange-600";
      default:
        return "bg-gray-500 hover:bg-gray-600";
    }
  };

  const getEVBadge = (ev: number) => {
    if (ev > 5) return { text: "EXCELLENT EV", color: "bg-green-500", icon: <TrendingUp className="h-4 w-4 mr-1.5" /> };
    if (ev > 0) return { text: "POSITIVE EV", color: "bg-lime-500", icon: <TrendingUp className="h-4 w-4 mr-1.5" /> };
    if (ev > -5) return { text: "NEUTRAL EV", color: "bg-gray-500", icon: <MinusCircle className="h-4 w-4 mr-1.5" /> };
    return { text: "NEGATIVE EV", color: "bg-red-500", icon: <TrendingDown className="h-4 w-4 mr-1.5" /> };
  };

  const evInfo = getEVBadge(prediction.expectedValue);

  return (
    <div className="rounded-xl border bg-card text-card-foreground shadow-lg transition-all hover:shadow-xl dark:shadow-primary/10">
      <div className="p-6">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              {prediction.matchDetails.teams}
            </h3>
            <p className="text-sm text-muted-foreground">
              {prediction.matchDetails.league} - {formatKickoffTime(prediction.matchDetails.kickoffTime)}
            </p>
          </div>
          <Badge className={cn("text-xs font-semibold text-white whitespace-nowrap", getConfidenceColor(prediction.confidence))}>
            {prediction.confidence}
          </Badge>
        </div>

        <div className="my-4 border-t border-border -mx-6"></div>

        <div className="space-y-3 mb-5">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Recommendation:</span>
            <span className="text-md font-semibold text-primary">
              {prediction.recommendation}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Odds:</span>
            <span className="text-md font-semibold">{prediction.odds.toFixed(2)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Expected Value:</span>
            <Badge variant="outline" className={cn("font-semibold text-sm", evInfo.color.replace('bg-', 'border-').replace('-500', '-600 dark:border-white/20'), evInfo.color.replace('bg-', 'text-'))}>
                {evInfo.icon}
                {prediction.expectedValue.toFixed(1)}%
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