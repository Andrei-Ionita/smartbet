'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { BettingSuggestion } from '@/types';

export default function MatchDetails() {
  const params = useParams();
  const router = useRouter();
  const [match, setMatch] = useState<BettingSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchMatchDetails = async () => {
      if (!params.id) return;
      
      setLoading(true);
      try {
        const response = await fetch(`/api/suggestions/${params.id}`);
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Match not found');
          }
          throw new Error('Failed to fetch match details');
        }
        
        const data = await response.json();
        setMatch(data);
      } catch (err) {
        setError('Could not load match details');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchMatchDetails();
  }, [params.id]);

  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-GB', {
      weekday: 'long',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Determine confidence color
  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'LOW':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Handle back button
  const handleBack = () => {
    router.back();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-2 text-gray-600">Loading match details...</p>
        </div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6">
          <h1 className="text-xl font-semibold text-red-800 mb-4">Error</h1>
          <p className="text-gray-700 mb-4">{error || 'Match not found'}</p>
          <button
            onClick={handleBack}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition"
          >
            Back to Suggestions
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Back Button */}
        <button
          onClick={handleBack}
          className="flex items-center text-blue-600 mb-6 hover:text-blue-800 transition"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9.707 14.707a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 1.414L7.414 9H15a1 1 0 110 2H7.414l2.293 2.293a1 1 0 010 1.414z" clipRule="evenodd" />
          </svg>
          Back to Suggestions
        </button>
        
        {/* Match Card */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                {match.league}
              </span>
              <span className="text-sm text-gray-500">{formatDate(match.kickoff)}</span>
            </div>
            <h1 className="text-2xl font-bold">{match.homeTeam} vs {match.awayTeam}</h1>
          </div>
          
          {/* Details */}
          <div className="p-6">
            {/* Recommendation Info */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-3">Betting Recommendation</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-md">
                  <p className="text-sm text-gray-500 mb-1">Recommended Bet</p>
                  <p className="font-bold text-blue-700">{match.recommendedBet}</p>
                </div>
                <div className={`p-3 rounded-md border ${getConfidenceColor(match.confidenceLevel)}`}>
                  <p className="text-sm mb-1">Confidence Level</p>
                  <p className="font-bold">{match.confidenceLevel}</p>
                </div>
              </div>
            </div>
            
            {/* Odds Table */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-3">Latest Odds</h2>
              <div className="overflow-hidden rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Home ({match.homeTeam})
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Draw
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Away ({match.awayTeam})
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                      <td className={`px-6 py-4 whitespace-nowrap text-lg font-bold ${match.recommendedBet === 'Home Win' ? 'text-blue-600' : ''}`}>
                        {match.odds.home.toFixed(2)}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-lg font-bold ${match.recommendedBet === 'Draw' ? 'text-blue-600' : ''}`}>
                        {match.odds.draw.toFixed(2)}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-lg font-bold ${match.recommendedBet === 'Away Win' ? 'text-blue-600' : ''}`}>
                        {match.odds.away.toFixed(2)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            
            {/* Model Predictions */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-3">Model Predictions</h2>
              <div className="bg-gray-50 p-4 rounded-md">
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-gray-500">Home Team Score</span>
                  <span className="font-medium">{(match.homeTeamScore * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full" 
                    style={{ width: `${match.homeTeamScore * 100}%` }}
                  ></div>
                </div>
                
                <div className="flex justify-between mb-2 mt-4">
                  <span className="text-sm text-gray-500">Away Team Score</span>
                  <span className="font-medium">{(match.awayTeamScore * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div 
                    className="bg-green-600 h-2.5 rounded-full" 
                    style={{ width: `${match.awayTeamScore * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
            
            {/* Source Info */}
            <div>
              <p className="text-sm text-gray-500 italic">
                Prediction based on {match.source} scoring model. Generated at {new Date(match.kickoff).toLocaleDateString()}.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 