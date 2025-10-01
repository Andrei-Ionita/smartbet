"use client";

import { useMutation } from "@tanstack/react-query";
import { submitFeedback } from "@/lib/api";
import type { Feedback } from "@/types/feedback";

export const useFeedback = () => {
  return useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      console.log("Feedback submitted successfully");
    },
    onError: (error) => {
      console.error("Failed to submit feedback:", error);
    },
  });
}; 