import React from 'react';
import Link from 'next/link';
import { BettingSuggestion } from '@/types';

interface MatchCardProps {
  suggestion: BettingSuggestion;
}

export default function MatchCard({ suggestion }: MatchCardProps) {
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Determine the confidence level color
  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-green-100 text-green-800';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800';
      case 'LOW':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Link href={`/match/${suggestion.id}`} className="block">
      <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition duration-300 mb-4">
        <div className="p-4">
          {/* League and time */}
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-gray-500">{suggestion.league}</span>
            <span className="text-xs text-gray-500">{formatDate(suggestion.kickoff)}</span>
          </div>

          {/* Teams */}
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              {suggestion.homeTeam} vs {suggestion.awayTeam}
            </h3>
          </div>

          {/* Recommendation and confidence */}
          <div className="flex justify-between items-center mb-3">
            <div className="flex items-center">
              <span className="font-medium mr-2">Recommendation:</span>
              <span className="font-bold text-blue-600">{suggestion.recommendedBet}</span>
            </div>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(
                suggestion.confidenceLevel
              )}`}
            >
              {suggestion.confidenceLevel}
            </span>
          </div>

          {/* Odds */}
          <div className="grid grid-cols-3 gap-2 text-center bg-gray-50 p-2 rounded-md">
            <div className="flex flex-col">
              <span className="text-xs text-gray-500">Home</span>
              <span className="font-bold">{suggestion.odds.home.toFixed(2)}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-500">Draw</span>
              <span className="font-bold">{suggestion.odds.draw.toFixed(2)}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs text-gray-500">Away</span>
              <span className="font-bold">{suggestion.odds.away.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
} 