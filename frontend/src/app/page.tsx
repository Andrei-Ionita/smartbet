'use client';

import React, { useState, useEffect } from 'react';
import MatchCard from '@/components/MatchCard';
import Filters from '@/components/Filters';
import { BettingSuggestion } from '@/types';

export default function Home() {
  const [suggestions, setSuggestions] = useState<BettingSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filter states
  const [confidenceLevel, setConfidenceLevel] = useState('All');
  const [league, setLeague] = useState('All');
  const [availableLeagues, setAvailableLeagues] = useState<string[]>([]);

  // Fetch suggestions based on filters
  useEffect(() => {
    const fetchSuggestions = async () => {
      setLoading(true);
      setError('');
      
      try {
        // Build URL with query parameters
        let url = '/api/suggestions';
        const params = new URLSearchParams();
        
        if (confidenceLevel !== 'All') {
          params.append('confidence', confidenceLevel);
        }
        
        if (league !== 'All') {
          params.append('league', league);
        }
        
        // Add params to URL if any exist
        if (params.toString()) {
          url += `?${params.toString()}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || 'Failed to fetch suggestions');
        }
        
        const data = await response.json();
        setSuggestions(data);
        
        // Extract unique leagues for the filter dropdown
        if (league === 'All' && data.length > 0) {
          const uniqueLeagues = [...new Set(data.map((s: BettingSuggestion) => s.league))];
          setAvailableLeagues(uniqueLeagues as string[]);
        }
      } catch (err) {
        setError('Failed to load betting suggestions. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchSuggestions();
  }, [confidenceLevel, league]);

  return (
    <main className="min-h-screen bg-gray-100">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">SmartBet Advisor</h1>
          <p className="text-gray-600">Your AI-powered betting suggestions for today's matches</p>
        </header>
        
        {/* Filters */}
        <Filters 
          confidenceLevel={confidenceLevel}
          league={league}
          onConfidenceChange={setConfidenceLevel}
          onLeagueChange={setLeague}
          availableLeagues={availableLeagues}
        />
        
        {/* Loading state */}
        {loading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <p className="mt-2 text-gray-600">Loading suggestions...</p>
          </div>
        )}
        
        {/* Error state */}
        {error && !loading && (
          <div className="bg-red-50 text-red-800 p-4 rounded-md mb-6">
            <p>{error}</p>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-2 text-sm underline hover:no-underline focus:outline-none"
            >
              Try again
            </button>
          </div>
        )}
        
        {/* No results */}
        {!loading && !error && suggestions.length === 0 && (
          <div className="bg-yellow-50 text-yellow-800 p-4 rounded-md mb-6">
            <p>No betting suggestions found with the current filters. Try adjusting your filters or check back later.</p>
          </div>
        )}
        
        {/* Suggestions list */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {!loading && suggestions.map((suggestion) => (
            <MatchCard key={suggestion.id} suggestion={suggestion} />
          ))}
        </div>
      </div>
    </main>
  );
} 