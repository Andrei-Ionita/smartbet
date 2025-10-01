"use client";

import { useState, useEffect } from 'react';

interface Prediction {
  id: number;
  match: {
    home_team: { name: string };
    away_team: { name: string };
    league: string;
    kickoff_time: string;
  };
  score: {
    predicted_outcome: string;
    expected_value: number;
    confidence_level: string;
    odds_snapshot: {
      odds_home: number;
      odds_draw: number;
      odds_away: number;
      bookmaker: string;
    };
  };
}

export default function TestPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPredictions() {
      try {
        const response = await fetch('http://localhost:8000/api/predictions/');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setPredictions(data.results || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch predictions');
      } finally {
        setLoading(false);
      }
    }

    fetchPredictions();
  }, []);

  if (loading) return <div className="p-8">Loading predictions...</div>;
  if (error) return <div className="p-8 text-red-600">Error: {error}</div>;

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">SmartBet API Test</h1>
        <p className="mb-6 text-gray-600">
          Successfully connected to Django backend at http://localhost:8000/api/predictions/
        </p>
        
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {predictions.map((prediction) => (
            <div key={prediction.id} className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold text-lg mb-2">
                {prediction.match.home_team.name} vs {prediction.match.away_team.name}
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                {prediction.match.league} • {new Date(prediction.match.kickoff_time).toLocaleDateString()}
              </p>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Prediction:</span>
                  <span className="font-medium capitalize">{prediction.score.predicted_outcome}</span>
                </div>
                <div className="flex justify-between">
                  <span>Confidence:</span>
                  <span className="font-medium capitalize">{prediction.score.confidence_level}</span>
                </div>
                <div className="flex justify-between">
                  <span>Expected Value:</span>
                  <span className="font-medium">{prediction.score.expected_value}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Odds (H/D/A):</span>
                  <span className="font-medium">
                    {prediction.score.odds_snapshot.odds_home}/
                    {prediction.score.odds_snapshot.odds_draw}/
                    {prediction.score.odds_snapshot.odds_away}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {predictions.length === 0 && (
          <p className="text-gray-500 text-center py-12">No predictions available.</p>
        )}
      </div>
    </main>
  );
} 