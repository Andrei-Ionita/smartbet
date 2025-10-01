"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

// Types for the new prediction system
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
}

interface MatchPredictionRequest {
  league: string;
  home_team: string;
  away_team: string;
  home_win_odds: number;
  draw_odds: number;
  away_win_odds: number;
  home_recent_form?: number;
  away_recent_form?: number;
  home_avg_goals_for?: number;
  away_avg_goals_for?: number;
  home_win_rate?: number;
  away_win_rate?: number;
}

interface BatchPredictionRequest {
  matches: MatchPredictionRequest[];
}

interface BatchPredictionResponse {
  predictions: LivePrediction[];
  summary: {
    total_matches: number;
    successful_predictions: number;
    recommended_bets: number;
    recommendation_rate: number;
    league_breakdown: Record<string, { total: number; recommended: number }>;
    processing_timestamp: string;
  };
}

interface ModelStatusResponse {
  leagues: Record<string, {
    name: string;
    status: string;
    performance: any;
    thresholds: { confidence: number; odds: number };
    model_file: string;
    is_loaded: boolean;
    error?: string;
  }>;
  system_status: string;
  total_leagues: number;
  timestamp: string;
}

// API Base URL for our FastAPI endpoints
const LIVE_API_BASE = process.env.NEXT_PUBLIC_LIVE_API_URL || 'http://localhost:8001';

// API Functions
async function fetchModelStatus(): Promise<ModelStatusResponse> {
  console.log("🔍 Fetching model status from live prediction API...");
  
  const response = await fetch(`${LIVE_API_BASE}/api/predict/status`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error("❌ Failed to fetch model status:", response.status, errorText);
    throw new Error(`Model status fetch failed: ${response.status}`);
  }

  const data = await response.json();
  console.log("✅ Model status received:", data);
  return data;
}

async function predictSingleMatch(request: MatchPredictionRequest): Promise<LivePrediction> {
  console.log("🔮 Making single match prediction:", request);
  
  const response = await fetch(`${LIVE_API_BASE}/api/predict`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    console.error("❌ Prediction failed:", response.status, errorData);
    throw new Error(errorData.detail || `Prediction failed: ${response.status}`);
  }

  const data = await response.json();
  console.log("✅ Prediction received:", data);
  return data;
}

async function predictBatchMatches(request: BatchPredictionRequest): Promise<BatchPredictionResponse> {
  console.log("📊 Making batch prediction:", request);
  
  const response = await fetch(`${LIVE_API_BASE}/api/predict/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    console.error("❌ Batch prediction failed:", response.status, errorData);
    throw new Error(errorData.detail || `Batch prediction failed: ${response.status}`);
  }

  const data = await response.json();
  console.log("✅ Batch prediction received:", data);
  return data;
}

async function fetchSupportedLeagues() {
  console.log("🌍 Fetching supported leagues...");
  
  const response = await fetch(`${LIVE_API_BASE}/api/predict/leagues`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error("❌ Failed to fetch leagues:", response.status, errorText);
    throw new Error(`Leagues fetch failed: ${response.status}`);
  }

  const data = await response.json();
  console.log("✅ Supported leagues:", data);
  return data;
}

// React Hooks

export const useModelStatus = () => {
  return useQuery({
    queryKey: ["liveModelStatus"],
    queryFn: fetchModelStatus,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 2,
    refetchOnWindowFocus: false,
  });
};

export const useSupportedLeagues = () => {
  return useQuery({
    queryKey: ["supportedLeagues"],
    queryFn: fetchSupportedLeagues,
    staleTime: 10 * 60 * 1000, // 10 minutes (leagues don't change often)
    retry: 2,
    refetchOnWindowFocus: false,
  });
};

export const useSinglePrediction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: predictSingleMatch,
    onSuccess: (data) => {
      console.log("🎯 Single prediction successful:", data);
      // Optionally cache the result
      queryClient.setQueryData(
        ["singlePrediction", data.home_team, data.away_team], 
        data
      );
    },
    onError: (error) => {
      console.error("❌ Single prediction error:", error);
    },
  });
};

export const useBatchPrediction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: predictBatchMatches,
    onSuccess: (data) => {
      console.log("📊 Batch prediction successful:", data);
      // Cache individual predictions
      data.predictions.forEach((prediction) => {
        queryClient.setQueryData(
          ["singlePrediction", prediction.home_team, prediction.away_team],
          prediction
        );
      });
    },
    onError: (error) => {
      console.error("❌ Batch prediction error:", error);
    },
  });
};

// Custom hook for managing live prediction workflow
export const useLivePredictionWorkflow = () => {
  const [selectedMatches, setSelectedMatches] = useState<MatchPredictionRequest[]>([]);
  const [currentPredictions, setCurrentPredictions] = useState<LivePrediction[]>([]);
  
  const singlePrediction = useSinglePrediction();
  const batchPrediction = useBatchPrediction();
  const modelStatus = useModelStatus();

  const addMatch = (match: MatchPredictionRequest) => {
    setSelectedMatches(prev => {
      const exists = prev.some(m => 
        m.home_team === match.home_team && 
        m.away_team === match.away_team && 
        m.league === match.league
      );
      
      if (exists) {
        console.log("⚠️ Match already added:", match);
        return prev;
      }
      
      console.log("➕ Adding match:", match);
      return [...prev, match];
    });
  };

  const removeMatch = (index: number) => {
    setSelectedMatches(prev => {
      const newMatches = [...prev];
      const removed = newMatches.splice(index, 1);
      console.log("➖ Removing match:", removed[0]);
      return newMatches;
    });
  };

  const clearMatches = () => {
    console.log("🗑️ Clearing all matches");
    setSelectedMatches([]);
    setCurrentPredictions([]);
  };

  const predictSelectedMatches = async () => {
    if (selectedMatches.length === 0) {
      console.log("⚠️ No matches selected for prediction");
      return;
    }

    if (selectedMatches.length === 1) {
      // Single prediction
      try {
        const result = await singlePrediction.mutateAsync(selectedMatches[0]);
        setCurrentPredictions([result]);
      } catch (error) {
        console.error("❌ Single prediction failed:", error);
      }
    } else {
      // Batch prediction
      try {
        const result = await batchPrediction.mutateAsync({ matches: selectedMatches });
        setCurrentPredictions(result.predictions);
      } catch (error) {
        console.error("❌ Batch prediction failed:", error);
      }
    }
  };

  const isLoading = singlePrediction.isPending || batchPrediction.isPending;
  const error = singlePrediction.error || batchPrediction.error;

  return {
    // State
    selectedMatches,
    currentPredictions,
    isLoading,
    error: error?.message,
    modelStatus: modelStatus.data,
    isModelStatusLoading: modelStatus.isLoading,
    
    // Actions
    addMatch,
    removeMatch,
    clearMatches,
    predictSelectedMatches,
    
    // Stats
    hasMatches: selectedMatches.length > 0,
    matchCount: selectedMatches.length,
    predictionCount: currentPredictions.length,
    recommendedBets: currentPredictions.filter(p => p.recommend).length,
  };
};

// Health check hook
export const useLiveAPIHealth = () => {
  return useQuery({
    queryKey: ["liveAPIHealth"],
    queryFn: async () => {
      const response = await fetch(`${LIVE_API_BASE}/api/predict/health`);
      if (!response.ok) throw new Error("API unhealthy");
      return await response.json();
    },
    staleTime: 30 * 1000, // 30 seconds
    retry: 1,
    refetchInterval: 60 * 1000, // Check every minute
    refetchOnWindowFocus: false,
  });
}; 