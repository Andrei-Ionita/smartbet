"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchPredictions } from "@/lib/api";
import type { Prediction } from "@/types/prediction";

export const usePredictions = () => {
  const queryClient = useQueryClient();
  
  const queryResult = useQuery({
    queryKey: ["predictions"],
    queryFn: fetchPredictions,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2, // Retry failed requests twice
    refetchOnWindowFocus: false, // Prevent automatic refetch on window focus
    refetchOnMount: true, // Always refetch when component mounts
  });

  // Debug logging for query state
  console.log("🔄 usePredictions hook state:", {
    isLoading: queryResult.isLoading,
    isFetching: queryResult.isFetching,
    isError: queryResult.isError,
    error: queryResult.error?.message,
    dataLength: queryResult.data?.length || 0,
    status: queryResult.status
  });

  // Enhanced refetch function that properly invalidates cache
  const enhancedRefetch = async () => {
    console.log("🔄 Manual refresh triggered - invalidating cache...");
    
    // First, invalidate the query cache
    await queryClient.invalidateQueries({ queryKey: ["predictions"] });
    
    // Then refetch with fresh data
    const result = await queryResult.refetch();
    
    console.log("✅ Refresh completed:", {
      success: result.isSuccess,
      dataLength: result.data?.length || 0,
      error: result.error?.message
    });
    
    return result;
  };

  return {
    ...queryResult,
    refetch: enhancedRefetch
  };
}; 