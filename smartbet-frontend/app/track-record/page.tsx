'use client';

import React, { useEffect, useState } from 'react';
import { RefreshCw, Trophy, TrendingUp, TrendingDown, Filter, CheckCircle, XCircle, Clock } from 'lucide-react';

interface PredictionWithResult {
  fixture_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff: string;
  predicted_outcome: string;
  confidence: number;
  expected_value: number;
  odds: {
    home: number;
    draw: number;
    away: number;
  };
  actual_outcome: string | null;
  actual_score: string | null;
  was_correct: boolean | null;
  profit_loss: number | null;
  prediction_logged_at: string;
  status: string;
}

interface AccuracyStats {
  overall: {
    total_predictions: number;
    correct_predictions: number;
    incorrect_predictions: number;
    accuracy_percent: number;
  };
  by_outcome: {
    home: { total: number; correct: number; accuracy: number };
    draw: { total: number; correct: number; accuracy: number };
    away: { total: number; correct: number; accuracy: number };
  };
}

interface ROIStats {
  total_bets: number;
  total_staked: number;
  total_profit_loss: number;
  roi_percent: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export default function TrackRecordPage() {
  const [predictions, setPredictions] = useState<PredictionWithResult[]>([]);
  const [accuracyStats, setAccuracyStats] = useState<AccuracyStats | null>(null);
  const [roiStats, setROIStats] = useState<ROIStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [filterLeague, setFilterLeague] = useState('all');
  const [filterStatus, setFilterStatus] = useState('completed');
  const [leagues, setLeagues] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, [filterStatus]);

  const loadData = async () => {
    try {
      setLoading(true);

      // Fetch predictions
      const showAll = filterStatus === 'all';
      const predictionsResponse = await fetch(
        `http://localhost:8000/api/transparency/recent/?limit=100&show_all=${showAll}`
      );
      const predictionsData = await predictionsResponse.json();

      if (predictionsData.success) {
        setPredictions(predictionsData.predictions);

        // Extract unique leagues
        const uniqueLeagues = Array.from(new Set(predictionsData.predictions.map((p: PredictionWithResult) => p.league)));
        setLeagues(uniqueLeagues as string[]);
      }

      // Fetch accuracy stats
      const statsResponse = await fetch('http://localhost:8000/api/transparency/dashboard/');
      const statsData = await statsResponse.json();

      if (statsData.success) {
        setAccuracyStats(statsData.stats.overall_accuracy);
        setROIStats(statsData.stats.roi_simulation);
      }
    } catch (error) {
      console.error('Failed to load track record:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateResults = async () => {
    setUpdating(true);
    try {
      const response = await fetch('http://localhost:8000/api/transparency/update-results/', {
        method: 'POST',
      });
      const data = await response.json();

      if (data.success) {
        alert(`✅ Updated ${data.stats.updated} predictions!\nAccuracy: ${data.stats.accuracy || 'N/A'}%`);
        loadData(); // Reload data
      } else {
        alert(`❌ ${data.error}`);
      }
    } catch (error) {
      alert('Failed to update results');
    } finally {
      setUpdating(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const filteredPredictions = predictions.filter((pred) => {
    if (filterLeague !== 'all' && pred.league !== filterLeague) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-12 bg-gray-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-32 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <Trophy className="h-8 w-8 text-blue-600" />
                <span>Our Track Record</span>
              </h1>
              <p className="text-gray-600 mt-2">
                Performance of our <strong>recommended bets</strong> - the fixtures we told you to bet on
              </p>
              <p className="text-sm text-blue-600 mt-1">
                💎 Only our top picks are shown here (55%+ confidence, positive EV)
              </p>
            </div>
            <button
              onClick={handleUpdateResults}
              disabled={updating}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            >
              <RefreshCw className={`h-4 w-4 ${updating ? 'animate-spin' : ''}`} />
              <span>{updating ? 'Updating...' : 'Update Results'}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Key Stats */}
        {accuracyStats && roiStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Overall Accuracy */}
            <div className="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg p-6 text-white">
              <p className="text-sm opacity-90 mb-2">Overall Accuracy</p>
              <p className="text-4xl font-bold mb-2">
                {accuracyStats.overall.accuracy_percent}%
              </p>
              <p className="text-sm opacity-90">
                {accuracyStats.overall.correct_predictions}/{accuracyStats.overall.total_predictions} correct
              </p>
            </div>

            {/* Win Rate */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <p className="text-sm text-gray-600 mb-2">Win Rate</p>
              <p className="text-4xl font-bold text-gray-900 mb-2">
                {roiStats.win_rate}%
              </p>
              <p className="text-sm text-gray-600">
                {roiStats.wins}W - {roiStats.losses}L
              </p>
            </div>

            {/* ROI */}
            <div className={`rounded-lg border-2 p-6 ${roiStats.roi_percent >= 0
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
              }`}>
              <p className="text-sm text-gray-700 mb-2">ROI ($10/bet)</p>
              <p className={`text-4xl font-bold mb-2 ${roiStats.roi_percent >= 0 ? 'text-green-700' : 'text-red-700'
                }`}>
                {roiStats.roi_percent >= 0 ? '+' : ''}{roiStats.roi_percent}%
              </p>
              <p className="text-sm text-gray-700">
                {roiStats.roi_percent >= 0 ? '+' : ''}${roiStats.total_profit_loss.toFixed(2)} total
              </p>
            </div>

            {/* Total Predictions */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <p className="text-sm text-gray-600 mb-2">Total Tracked</p>
              <p className="text-4xl font-bold text-gray-900 mb-2">
                {roiStats.total_bets}
              </p>
              <p className="text-sm text-gray-600">
                Predictions logged
              </p>
            </div>
          </div>
        )}

        {/* Outcome Breakdown */}
        {accuracyStats && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Accuracy by Prediction Type</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-2">Home Wins</p>
                <p className="text-3xl font-bold text-blue-600 mb-1">
                  {accuracyStats.by_outcome.home.accuracy}%
                </p>
                <p className="text-xs text-gray-600">
                  {accuracyStats.by_outcome.home.correct}/{accuracyStats.by_outcome.home.total}
                </p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-2">Draws</p>
                <p className="text-3xl font-bold text-gray-600 mb-1">
                  {accuracyStats.by_outcome.draw.accuracy}%
                </p>
                <p className="text-xs text-gray-600">
                  {accuracyStats.by_outcome.draw.correct}/{accuracyStats.by_outcome.draw.total}
                </p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-2">Away Wins</p>
                <p className="text-3xl font-bold text-purple-600 mb-1">
                  {accuracyStats.by_outcome.away.accuracy}%
                </p>
                <p className="text-xs text-gray-600">
                  {accuracyStats.by_outcome.away.correct}/{accuracyStats.by_outcome.away.total}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Filters:</span>
            </div>

            <select
              value={filterLeague}
              onChange={(e) => setFilterLeague(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="all">All Leagues</option>
              {leagues.map((league) => (
                <option key={league} value={league}>{league}</option>
              ))}
            </select>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="completed">Completed Only</option>
              <option value="all">All (Including Pending)</option>
            </select>

            <span className="text-sm text-gray-600 ml-auto">
              Showing {filteredPredictions.length} predictions
            </span>
          </div>
        </div>

        {/* Predictions Table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Predicted</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actual</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Result</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Confidence</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">EV</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">P/L ($10)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredPredictions.map((pred) => (
                  <tr key={pred.fixture_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {pred.home_team} vs {pred.away_team}
                        </p>
                        <p className="text-xs text-gray-500">{pred.league}</p>
                        {pred.actual_score && (
                          <p className="text-xs text-gray-600 font-mono mt-1">
                            Score: {pred.actual_score}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${pred.predicted_outcome === 'Home' ? 'bg-blue-100 text-blue-800' :
                          pred.predicted_outcome === 'Draw' ? 'bg-gray-100 text-gray-800' :
                            'bg-purple-100 text-purple-800'
                        }`}>
                        {pred.predicted_outcome}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {pred.actual_outcome ? (
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${pred.actual_outcome === 'Home' ? 'bg-blue-100 text-blue-800' :
                            pred.actual_outcome === 'Draw' ? 'bg-gray-100 text-gray-800' :
                              'bg-purple-100 text-purple-800'
                          }`}>
                          {pred.actual_outcome}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          <Clock className="h-3 w-3" />
                          Pending
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {pred.was_correct === true && (
                        <CheckCircle className="h-5 w-5 text-green-600 inline" />
                      )}
                      {pred.was_correct === false && (
                        <XCircle className="h-5 w-5 text-red-600 inline" />
                      )}
                      {pred.was_correct === null && (
                        <Clock className="h-5 w-5 text-yellow-600 inline" />
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-sm font-medium text-gray-900">
                        {pred.confidence.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-sm font-medium text-green-600">
                        +{pred.expected_value.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {pred.profit_loss !== null ? (
                        <span className={`text-sm font-bold ${pred.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                          {pred.profit_loss >= 0 ? '+' : ''}${pred.profit_loss.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {formatDate(pred.kickoff)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredPredictions.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                No predictions found
              </div>
            )}
          </div>
        </div>

        {/* Transparency Notice */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 mb-3 text-lg">🔒 Our Transparency Commitment</h3>

          <div className="mb-4 p-4 bg-white rounded-lg border border-blue-200">
            <h4 className="font-semibold text-blue-900 mb-2">📋 What We Track</h4>
            <p className="text-sm text-blue-800">
              We track <strong>only the predictions we recommend to you</strong> - the "best bets"
              shown on our homepage (top 10 daily picks with 55%+ confidence and positive EV).
            </p>
            <p className="text-sm text-blue-800 mt-2">
              <strong>Why?</strong> Because we believe in accountability. We don't track thousands
              of predictions we never told you about - we track what we actually recommend.
            </p>
          </div>

          <ul className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>Timestamped BEFORE kickoff:</strong> All predictions logged before matches start - impossible to fake</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>Third-party verified:</strong> Results fetched from SportMonks API - we cannot manipulate them</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>Never deleted:</strong> Historical data is permanent - we show both wins and losses</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>Complete history:</strong> Every recommendation we made is here - you can audit everything</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>Real-time updates:</strong> Click "Update Results" to fetch the latest match outcomes</span>
            </li>
          </ul>

          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-900">
              <strong>Note:</strong> We only track our <strong>recommended bets</strong> (the ones we show on the homepage).
              This is honest accountability - we're measured by what we actually tell you to bet on, not by cherry-picking
              from thousands of unpublished predictions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
