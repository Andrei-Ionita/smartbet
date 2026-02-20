'use client';

import React, { useEffect, useState } from 'react';
import { RefreshCw, Trophy, TrendingUp, TrendingDown, Filter, CheckCircle, XCircle, Clock, Calendar, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

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
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterResult, setFilterResult] = useState('all');
  const [filterOutcome, setFilterOutcome] = useState('all');
  const [showFilters, setShowFilters] = useState(true);
  const [leagues, setLeagues] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, [filterStatus]);

  const loadData = async () => {
    try {
      setLoading(true);

      // Fetch predictions
      const showAll = filterStatus === 'all';
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const predictionsResponse = await fetch(
        `${apiUrl}/api/transparency/recent/?limit=100&show_all=${showAll}`
      );
      const predictionsData = await predictionsResponse.json();

      if (predictionsData.success) {
        setPredictions(predictionsData.predictions);

        // Extract unique leagues
        const uniqueLeagues = Array.from(new Set(predictionsData.predictions.map((p: PredictionWithResult) => p.league)));
        setLeagues(uniqueLeagues as string[]);
      }

      // Fetch accuracy stats
      const statsResponse = await fetch(`${apiUrl}/api/transparency/dashboard/`);
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
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/transparency/update-results/`, {
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

  // Helper for replacing placeholders
  const formatString = (str: string, ...args: (string | number)[]) => {
    return str.replace(/{(\d+)}/g, (match, number) => {
      return typeof args[number] !== 'undefined' ? String(args[number]) : match;
    });
  };

  const { t, language } = useLanguage()

  // ... (rest of imports and logic)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(language === 'ro' ? 'ro-RO' : 'en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const clearFilters = () => {
    setFilterLeague('all');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterResult('all');
    setFilterOutcome('all');
  };

  const activeFilterCount = [
    filterLeague !== 'all',
    filterDateFrom !== '',
    filterDateTo !== '',
    filterResult !== 'all',
    filterOutcome !== 'all',
  ].filter(Boolean).length;

  const filteredPredictions = predictions.filter((pred) => {
    if (filterLeague !== 'all' && pred.league !== filterLeague) return false;

    // Date range filter
    if (filterDateFrom) {
      const kickoff = new Date(pred.kickoff).toISOString().split('T')[0];
      if (kickoff < filterDateFrom) return false;
    }
    if (filterDateTo) {
      const kickoff = new Date(pred.kickoff).toISOString().split('T')[0];
      if (kickoff > filterDateTo) return false;
    }

    // Result filter (win/loss)
    if (filterResult === 'wins' && pred.was_correct !== true) return false;
    if (filterResult === 'losses' && pred.was_correct !== false) return false;

    // Predicted outcome filter
    if (filterOutcome !== 'all' && pred.predicted_outcome !== filterOutcome) return false;

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
                <span>{t('trackRecord.title')}</span>
              </h1>
              <p className="text-gray-600 mt-2">
                {t('trackRecord.subtitle')}
              </p>
              <p className="text-sm text-blue-600 mt-1">
                {t('trackRecord.disclaimer')}
              </p>
            </div>
            <button
              onClick={handleUpdateResults}
              disabled={updating}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            >
              <RefreshCw className={`h-4 w-4 ${updating ? 'animate-spin' : ''}`} />
              <span>{updating ? t('trackRecord.updating') : t('trackRecord.updateResults')}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Key Stats */}
        {accuracyStats && roiStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Overall Accuracy */}
            <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg p-6 text-white">
              <p className="text-sm opacity-90 mb-2">{t('trackRecord.stats.overallAccuracy')}</p>
              <p className="text-4xl font-bold mb-2">
                {accuracyStats.overall.accuracy_percent}%
              </p>
              <p className="text-sm opacity-90">
                {formatString('{0}/{1} correct', accuracyStats.overall.correct_predictions, accuracyStats.overall.total_predictions)}
                {/* Note: 'correct' word hardcoded in logic above, simplified for now as numbers are universal */}
              </p>
            </div>

            {/* Win Rate */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <p className="text-sm text-gray-600 mb-2">{t('trackRecord.stats.winRate')}</p>
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
              <p className="text-sm text-gray-700 mb-2">{t('trackRecord.stats.roi')}</p>
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
              <p className="text-sm text-gray-600 mb-2">{t('trackRecord.stats.totalTracked')}</p>
              <p className="text-4xl font-bold text-gray-900 mb-2">
                {roiStats.total_bets}
              </p>
              <p className="text-sm text-gray-600">
                {t('trackRecord.stats.predictionsLogged')}
              </p>
            </div>
          </div>
        )}

        {/* Outcome Breakdown */}
        {accuracyStats && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">{t('trackRecord.stats.accuracyByType')}</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-2">{t('trackRecord.stats.homeWins')}</p>
                <p className="text-3xl font-bold text-blue-600 mb-1">
                  {accuracyStats.by_outcome.home.accuracy}%
                </p>
                <p className="text-xs text-gray-600">
                  {accuracyStats.by_outcome.home.correct}/{accuracyStats.by_outcome.home.total}
                </p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-2">{t('trackRecord.stats.draws')}</p>
                <p className="text-3xl font-bold text-gray-600 mb-1">
                  {accuracyStats.by_outcome.draw.accuracy}%
                </p>
                <p className="text-xs text-gray-600">
                  {accuracyStats.by_outcome.draw.correct}/{accuracyStats.by_outcome.draw.total}
                </p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-sm text-gray-600 mb-2">{t('trackRecord.stats.awayWins')}</p>
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
        <div className="bg-white rounded-lg border border-gray-200 mb-6 overflow-hidden">
          {/* Filter header - always visible */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-semibold text-gray-800">{t('trackRecord.filters.label')}</span>
              {activeFilterCount > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  {formatString(t('trackRecord.filters.activeFilters'), activeFilterCount)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">
                {formatString(t('trackRecord.filters.showing'), filteredPredictions.length)}
              </span>
              {showFilters ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
            </div>
          </button>

          {/* Collapsible filter body */}
          {showFilters && (
            <div className="px-4 pb-4 border-t border-gray-100 pt-3">
              {/* Row 1: Date range + League + Status */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
                {/* Date From */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.filters.dateFrom')}</label>
                  <div className="relative">
                    <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 pointer-events-none" />
                    <input
                      type="date"
                      value={filterDateFrom}
                      onChange={(e) => setFilterDateFrom(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* Date To */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.filters.dateTo')}</label>
                  <div className="relative">
                    <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 pointer-events-none" />
                    <input
                      type="date"
                      value={filterDateTo}
                      onChange={(e) => setFilterDateTo(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* League */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.filters.allLeagues')}</label>
                  <select
                    value={filterLeague}
                    onChange={(e) => setFilterLeague(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="all">{t('trackRecord.filters.allLeagues')}</option>
                    {leagues.map((league) => (
                      <option key={league} value={league}>{league}</option>
                    ))}
                  </select>
                </div>

                {/* Status */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.filters.completedOnly')}</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="completed">{t('trackRecord.filters.completedOnly')}</option>
                    <option value="all">{t('trackRecord.filters.all')}</option>
                  </select>
                </div>
              </div>

              {/* Row 2: Result + Outcome + Clear */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Result (Win/Loss) */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.table.result')}</label>
                  <select
                    value={filterResult}
                    onChange={(e) => setFilterResult(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="all">{t('trackRecord.filters.allResults')}</option>
                    <option value="wins">{t('trackRecord.filters.winsOnly')}</option>
                    <option value="losses">{t('trackRecord.filters.lossesOnly')}</option>
                  </select>
                </div>

                {/* Predicted Outcome */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.table.predicted')}</label>
                  <select
                    value={filterOutcome}
                    onChange={(e) => setFilterOutcome(e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="all">{t('trackRecord.filters.allOutcomes')}</option>
                    <option value="Home">{t('card.outcomes.home')}</option>
                    <option value="Draw">{t('card.outcomes.draw')}</option>
                    <option value="Away">{t('card.outcomes.away')}</option>
                  </select>
                </div>

                {/* Clear Filters */}
                <div className="flex items-end">
                  <button
                    onClick={clearFilters}
                    disabled={activeFilterCount === 0}
                    className="w-full flex items-center justify-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    {t('trackRecord.filters.clearFilters')}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Predictions Table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.match')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.predicted')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.actual')}</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.result')}</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.confidence')}</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.ev')}</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.pl')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.date')}</th>
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
                            {t('trackRecord.table.score')} {pred.actual_score}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${pred.predicted_outcome === 'Home' ? 'bg-blue-100 text-blue-800' :
                        pred.predicted_outcome === 'Draw' ? 'bg-gray-100 text-gray-800' :
                          'bg-purple-100 text-purple-800'
                        }`}>
                        {pred.predicted_outcome === 'Home' ? t('card.outcomes.home') :
                          pred.predicted_outcome === 'Draw' ? t('card.outcomes.draw') :
                            pred.predicted_outcome === 'Away' ? t('card.outcomes.away') : pred.predicted_outcome}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {pred.actual_outcome ? (
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${pred.actual_outcome === 'Home' ? 'bg-blue-100 text-blue-800' :
                          pred.actual_outcome === 'Draw' ? 'bg-gray-100 text-gray-800' :
                            'bg-purple-100 text-purple-800'
                          }`}>
                          {pred.actual_outcome === 'Home' ? t('card.outcomes.home') :
                            pred.actual_outcome === 'Draw' ? t('card.outcomes.draw') :
                              pred.actual_outcome === 'Away' ? t('card.outcomes.away') : pred.actual_outcome}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          <Clock className="h-3 w-3" />
                          {t('trackRecord.table.pending')}
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
                {t('trackRecord.table.noPredictions')}
              </div>
            )}
          </div>
        </div>

        {/* Transparency Notice */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-blue-100 border-2 border-blue-300 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 mb-3 text-lg">{t('trackRecord.transparency.title')}</h3>

          <div className="mb-4 p-4 bg-white rounded-lg border border-blue-200">
            <h4 className="font-semibold text-blue-900 mb-2">{t('trackRecord.transparency.whatWeTrack')}</h4>
            <p className="text-sm text-blue-800">
              {t('trackRecord.transparency.whatWeTrackDesc')}
            </p>
            <p className="text-sm text-blue-800 mt-2">
              <strong>{t('trackRecord.transparency.why')}</strong> {t('trackRecord.transparency.whyDesc')}
            </p>
          </div>

          <ul className="space-y-2 text-sm text-blue-800">
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>{t('trackRecord.transparency.points.timestamped')}:</strong> {t('trackRecord.transparency.points.timestampedDesc')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>{t('trackRecord.transparency.points.verified')}:</strong> {t('trackRecord.transparency.points.verifiedDesc')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>{t('trackRecord.transparency.points.permanent')}:</strong> {t('trackRecord.transparency.points.permanentDesc')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>{t('trackRecord.transparency.points.history')}:</strong> {t('trackRecord.transparency.points.historyDesc')}</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span><strong>{t('trackRecord.transparency.points.updates')}:</strong> {t('trackRecord.transparency.points.updatesDesc')}</span>
            </li>
          </ul>

          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-900">
              <strong>{t('trackRecord.transparency.note')}</strong> {t('trackRecord.transparency.noteDesc')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
