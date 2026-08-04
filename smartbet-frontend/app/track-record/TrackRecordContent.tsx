'use client';

import React, { useEffect, useState } from 'react';
import { Trophy, Filter, CheckCircle, XCircle, Clock, Calendar, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { MODEL_SCORE_NOTE, getCopy } from '../lib/terminology';
import ProofCapturePanel from '../components/ProofCapturePanel';
import ShareProofButton from '../components/ShareProofButton';
import { StatusBadge, StatusLegend, statusFromClaim } from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';

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
  /** Read-only from the API. 'verified' rows are the only ones eligible for
   *  the public record; anything else is legacy or missing provenance. */
  pricing_integrity_status?: string | null;
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

/** Only 'verified' rows have a price provenance we can stand behind. Anything
 *  else — legacy_unverified, audit_excluded, missing — is outside the public
 *  record and may not display price-derived performance. */
const isVerified = (p: PredictionWithResult) =>
  (p.pricing_integrity_status || '') === 'verified';

/** Placeholder for a price-dependent figure we will not publish. */
function NotVerified() {
  return (
    <span
      className="text-sm font-medium text-gray-400"
      title="This prediction predates BetGlitch’s verified pricing standard. Its original price snapshot is not used in public performance reporting."
    >
      Not verified
    </span>
  );
}

export default function TrackRecordContent() {
  const [predictions, setPredictions] = useState<PredictionWithResult[]>([]);
  const [accuracyStats, setAccuracyStats] = useState<AccuracyStats | null>(null);
  const [roiStats, setROIStats] = useState<ROIStats | null>(null);
  const [loading, setLoading] = useState(true);
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
        `${apiUrl}/api/transparency/recent/?limit=1000&show_all=${showAll}`
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

  // Helper for replacing placeholders
  const formatString = (str: string, ...args: (string | number)[]) => {
    return str.replace(/{(\d+)}/g, (match, number) => {
      return typeof args[number] !== 'undefined' ? String(args[number]) : match;
    });
  };

  const { t, language } = useLanguage()
  const rec = getCopy(language).record

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

  // Rows recorded before the pricing-integrity cutoff. They are preserved and
  // shown, but they are NOT the verified record and must not read as it.
  const legacyCount = filteredPredictions.filter((p) => !isVerified(p)).length;

  // Published picks are the verified-provenance rows, listed whatever their
  // outcome — that is the point of publishing. Read off the full prediction
  // set rather than the filtered table, so a league or date filter chosen
  // further down the page cannot quietly shrink what claims to be the
  // complete published set.
  const publishedPicks = predictions.filter(isVerified);

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
          {/* An "Update Results" button used to sit here. It fired an
              unauthenticated settlement run against production from a public
              page and reported through a blocking browser dialog. Settlement is
              the scheduler's job, not a visitor's. Removing it also fixed the
              Romanian layout: the translated label would not wrap and forced
              the whole page to scroll sideways at 320px. */}
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Trophy className="h-8 w-8 flex-shrink-0 text-blue-600" />
              <span>{t('trackRecord.title')}</span>
            </h1>
            <p className="text-gray-600 mt-2">
              {t('trackRecord.subtitle')}
            </p>
            <p className="text-sm text-blue-600 mt-1">
              {t('trackRecord.disclaimer')}
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* What actually counts towards this page. Stated before any figure,
            because "track record" previously implied every prediction ever
            made — which is not what this measures. */}
        <section
          aria-labelledby="record-scope"
          className="mb-8 rounded-2xl border border-gray-200 bg-white p-6"
        >
          <h2 id="record-scope" className="text-lg font-bold text-gray-900">
            {rec.scopeHeading}
          </h2>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed text-gray-700">
            <li>{rec.scopeCutoff}</li>
            <li>{rec.scopeImmutable}</li>
            <li>{rec.scopePending}</li>
            <li>{rec.scopeLive}</li>
          </ul>
          <StatusLegend className="mt-5 border-t border-gray-200 pt-5" lang={language} />
        </section>

        {/* PUBLISHED PICKS — the objects. Anchored so the onboarding panel can
            send someone to the thing it just described, rather than to the top
            of a long page. Deliberately separate from the verified record
            below: a pending pick belongs here and belongs in no total. */}
        <section
          id="published-picks"
          aria-labelledby="published-picks-heading"
          className="mb-8 scroll-mt-24 rounded-2xl border border-gray-200 bg-white p-6"
        >
          <h2
            id="published-picks-heading"
            className="text-lg font-bold text-gray-900"
          >
            {rec.publishedHeading}
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-700">
            {rec.publishedBody}
          </p>
          <p className="mt-3 text-sm leading-relaxed text-gray-700">
            {rec.publishedStates}
          </p>

          {publishedPicks.length === 0 ? (
            <p className="mt-5 rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm leading-relaxed text-gray-600">
              {rec.publishedEmpty}
            </p>
          ) : (
            <>
              <p className="mt-5 text-xs font-semibold uppercase tracking-widest text-gray-500">
                {rec.publishedCount}: {publishedPicks.length}
              </p>
              <ul className="mt-3 divide-y divide-gray-200 border-t border-gray-200">
                {publishedPicks.map((pick) => (
                  <li
                    key={`${pick.fixture_id}-${pick.predicted_outcome}`}
                    className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3"
                  >
                    <StatusBadge
                      status={statusFromClaim(
                        pick.pricing_integrity_status,
                        pick.actual_outcome,
                      )}
                      size="sm"
                      lang={language}
                    />
                    <span className="text-sm font-semibold text-gray-900">
                      {pick.home_team} v {pick.away_team}
                    </span>
                    <span className="text-sm text-gray-600">
                      {pick.predicted_outcome}
                    </span>
                    <span className="ml-auto text-sm text-gray-600">
                      {formatDate(pick.kickoff)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        {/* VERIFIED RECORD — the aggregate. Anchored, and explicitly scoped so
            the figures below cannot be read as "every prediction ever made". */}
        <section
          id="verified-record"
          aria-labelledby="verified-record-heading"
          className="mb-8 scroll-mt-24 rounded-2xl border border-gray-200 bg-white p-6"
        >
          <h2
            id="verified-record-heading"
            className="text-lg font-bold text-gray-900"
          >
            {rec.verifiedHeading}
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-700">
            {rec.verifiedBody}
          </p>
        </section>

        {/* Key Stats */}
        {accuracyStats && roiStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {/* Overall Accuracy — an empty record is "no results yet", never
                "0% accurate". A zero denominator rendered as a big "0%" reads
                as measured failure, which is a different and false claim. */}
            {accuracyStats.overall.total_predictions === 0 ? (
              <div className="rounded-lg border-2 border-gray-200 bg-gray-50 p-6">
                <p className="text-sm text-gray-700 mb-2">{t('trackRecord.stats.overallAccuracy')}</p>
                <p className="text-2xl font-bold text-gray-500 mb-2">{rec.noAccuracy}</p>
                <p className="text-sm text-gray-600">{rec.accuracyAppears}</p>
              </div>
            ) : (
              <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg p-6 text-white">
                <p className="text-sm opacity-90 mb-2">{t('trackRecord.stats.overallAccuracy')}</p>
                <p className="text-4xl font-bold mb-2">
                  {accuracyStats.overall.accuracy_percent}%
                </p>
                <p className="text-sm opacity-90">
                  {formatString('{0}/{1} correct', accuracyStats.overall.correct_predictions, accuracyStats.overall.total_predictions)}
                </p>
              </div>
            )}

            {/* Win Rate — same rule: 0W-0L is not a 0% win rate. */}
            {roiStats.total_bets === 0 ? (
              <div className="rounded-lg border-2 border-gray-200 bg-gray-50 p-6">
                <p className="text-sm text-gray-700 mb-2">{t('trackRecord.stats.winRate')}</p>
                <p className="text-2xl font-bold text-gray-500 mb-2">{rec.noSettled}</p>
                <p className="text-sm text-gray-600">
                  {rec.winsLosses}
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <p className="text-sm text-gray-600 mb-2">{t('trackRecord.stats.winRate')}</p>
                <p className="text-4xl font-bold text-gray-900 mb-2">
                  {roiStats.win_rate}%
                </p>
                <p className="text-sm text-gray-600">
                  {roiStats.wins}W - {roiStats.losses}L
                </p>
              </div>
            )}

            {/* ROI — a zero-sample record must never render as profitable.
                The verified pricing record restarts at the integrity cutoff, so
                total_bets is legitimately 0 until new picks settle. Showing
                "+0%" in green would read as break-even performance rather than
                "no results yet". */}
            {roiStats.total_bets === 0 ? (
              <div className="rounded-lg border-2 border-gray-200 bg-gray-50 p-6">
                <p className="text-sm text-gray-700 mb-2">{t('trackRecord.stats.roi')}</p>
                <p className="text-2xl font-bold text-gray-500 mb-2">{rec.noAccuracy}</p>
                <p className="text-sm text-gray-600">{rec.roiRestarted}</p>
              </div>
            ) : (
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
            )}

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
        {/* Suppressed entirely at zero. Three side-by-side "0%" tiles read as
            "the model gets home, draw and away all wrong", not "nothing has
            settled yet". */}
        {accuracyStats && accuracyStats.overall.total_predictions === 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-2">{t('trackRecord.stats.accuracyByType')}</h2>
            <p className="text-sm text-gray-600">{rec.noBreakdown}</p>
          </div>
        )}

        {accuracyStats && accuracyStats.overall.total_predictions > 0 && (
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
                      aria-label={t('trackRecord.filters.dateFrom')}
                      value={filterDateFrom}
                      onChange={(e) => setFilterDateFrom(e.target.value)}
                      className="w-full min-h-[44px] pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                      aria-label={t('trackRecord.filters.dateTo')}
                      value={filterDateTo}
                      onChange={(e) => setFilterDateTo(e.target.value)}
                      className="w-full min-h-[44px] pl-8 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* League */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">{t('trackRecord.filters.allLeagues')}</label>
                  <select
                    aria-label={t('trackRecord.filters.allLeagues')}
                    value={filterLeague}
                    onChange={(e) => setFilterLeague(e.target.value)}
                    className="w-full min-h-[44px] px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                    aria-label={t('trackRecord.filters.completedOnly')}
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full min-h-[44px] px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                    aria-label={t('trackRecord.table.result')}
                    value={filterResult}
                    onChange={(e) => setFilterResult(e.target.value)}
                    className="w-full min-h-[44px] px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                    aria-label={t('trackRecord.table.predicted')}
                    value={filterOutcome}
                    onChange={(e) => setFilterOutcome(e.target.value)}
                    className="w-full min-h-[44px] px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                    className="w-full min-h-[44px] flex items-center justify-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
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
          {/* Without this, the log reads as the verified record: the stats above
              correctly say zero while the table below lists hundreds of rows
              with profit figures. Say plainly which is which. */}
          {legacyCount > 0 && (
            <div className="border-b border-amber-200 bg-amber-50 p-4 sm:p-5">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status="legacy" size="sm" />
                <h3 className="text-sm font-bold text-gray-900">
                  Prediction log — not the verified record
                </h3>
              </div>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-700">
                {legacyCount === filteredPredictions.length
                  ? `All ${legacyCount} rows below were`
                  : `${legacyCount} of the ${filteredPredictions.length} rows below were`}{' '}
                recorded before the pricing-integrity cutoff. They are kept
                public because BetGlitch does not delete history, but their
                prices could not be verified against the exact market and
                bookmaker, so they are excluded from the accuracy and ROI
                figures above and from every public performance claim.
              </p>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-700">
                These predictions predate BetGlitch’s verified pricing standard.
                Their original price snapshots are not used in public performance
                reporting, so every price-dependent figure — expected value and
                profit/loss — reads <strong>Not verified</strong> rather than a
                number. The match, the selection and the actual outcome are still
                shown, because those do not depend on the recorded price.
              </p>
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.match')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.predicted')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.actual')}</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.result')}</th>
                  {/* Was "Confidence", rendered as "60.8%" — which reads as a
                      calibrated probability. It is a relative ranking score. */}
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                    Model score
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.ev')}</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.pl')}</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('trackRecord.table.date')}</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredPredictions.map((pred) => (
                  <tr key={pred.fixture_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div>
                        {!isVerified(pred) && (
                          <div className="mb-1">
                            <StatusBadge status="legacy" size="sm" />
                          </div>
                        )}
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
                        {pred.confidence.toFixed(1)}
                      </span>
                    </td>
                    {/* Expected value and profit/loss are both computed FROM the
                        recorded price. On a legacy row that price could not be
                        verified against the exact market and bookmaker, so the
                        figures derived from it are not evidence of anything and
                        must not be shown as green/red money. */}
                    <td className="px-6 py-4 text-right">
                      {isVerified(pred) ? (
                        <span className="text-sm font-medium text-green-600">
                          +{pred.expected_value.toFixed(1)}%
                        </span>
                      ) : (
                        <NotVerified />
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {!isVerified(pred) ? (
                        <NotVerified />
                      ) : pred.profit_loss !== null ? (
                        <span className={`text-sm font-bold ${pred.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                          {pred.profit_loss >= 0 ? '+' : ''}${pred.profit_loss.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {formatDate(pred.kickoff)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <ShareProofButton fixtureId={pred.fixture_id} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* An empty table with no explanation reads as a broken page. Say
                why it is empty, that it is expected, and what to do instead. */}
            {filteredPredictions.length === 0 && (
              <div className="p-6">
                <EmptyState state="no_verified_results" lang={language} />
              </div>
            )}
          </div>

          <p className="border-t border-gray-200 bg-gray-50 px-4 py-3 text-xs leading-relaxed text-gray-600 sm:px-6">
            {MODEL_SCORE_NOTE} <strong>Not verified</strong> means the row’s
            recorded price predates the verified pricing standard, so no
            price-dependent figure is published for it.
          </p>
        </div>

        <div className="mt-8">
          <ProofCapturePanel
            source="track_record_page"
            title="Check the receipts, then follow along by email."
            description="Verify every result here, then join the free list for weekly picks and updates as the verified record develops."
          />
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
