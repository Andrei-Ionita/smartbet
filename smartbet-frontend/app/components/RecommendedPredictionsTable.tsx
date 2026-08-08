'use client'

import { useState, useEffect, useMemo } from 'react'
import { RefreshCw, CheckCircle2, XCircle, Clock, TrendingUp, TrendingDown, Award, Lock, ExternalLink, Filter, Calendar, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'
import { computeDiscrimination, describeAuc } from '../lib/discrimination'

interface RecommendedPrediction {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: string
  predicted_outcome_raw: string
  confidence: number
  actual_outcome: string | null
  actual_outcome_raw: string | null
  actual_score_home: number | null
  actual_score_away: number | null
  match_status: string | null
  was_correct: boolean | null
  prediction_logged_at: string
  result_logged_at: string | null
  is_completed: boolean
}

/**
 * Operational counts ONLY.
 *
 * accuracy / total_profit_loss / average_roi / edge_vs_market are gone. This
 * page covers the FULL internal universe including legacy rows whose prices
 * could not be verified — the same rows /track-record explicitly excludes
 * from every public figure. Publishing an accuracy percentage and a dollar
 * P/L here while the verified record said "no settled results yet" put two
 * contradicting performance universes on one screen (public review,
 * 2026-08-08). Public performance has exactly one home: the verified record.
 */
interface Summary {
  total_recommended: number
  completed: number
  pending: number
  audit_excluded: number
  graded: number
}

export default function RecommendedPredictionsTable() {
  const [predictions, setPredictions] = useState<RecommendedPrediction[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includePending, setIncludePending] = useState(true)
  const [filterLeague, setFilterLeague] = useState('all')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')
  const [filterResult, setFilterResult] = useState('all')
  const [filterOutcome, setFilterOutcome] = useState('all')
  const [showFilters, setShowFilters] = useState(false)

  const fetchPredictions = async () => {
    try {
      setIsRefreshing(true)
      setError(null)

      // This used to POST to a proxy route first, which forwarded to an
      // unauthenticated Django endpoint that fetched up to 50 fixtures from
      // SportMonks and wrote outcomes. /monitoring is public, so every anonymous
      // visitor triggered a production write on mount. Recording outcomes is the
      // scheduler's job; this component only reads.
      // Call Django API through Next.js API route
      const response = await fetch(`/api/django/recommended-predictions?include_pending=${includePending}`)
      const data = await response.json()

      if (data.success) {
        setPredictions(data.data || [])
        setSummary(data.summary || null)
      } else {
        setError(data.error || 'Failed to fetch predictions')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      console.error('Error fetching recommended predictions:', err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchPredictions()

    // Auto-refresh every 2 minutes to catch new results
    const refreshInterval = setInterval(() => {
      console.log('🔄 Auto-refreshing predictions...')
      fetchPredictions()
    }, 120000) // 2 minutes

    return () => clearInterval(refreshInterval)
  }, [includePending])

  // Refresh when tab becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('👁️ Tab became visible, refreshing predictions...')
        fetchPredictions()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [includePending])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Calculate time before kickoff when prediction was logged
  const getLoggedBeforeKickoff = (loggedAt: string, kickoff: string) => {
    const loggedDate = new Date(loggedAt)
    const kickoffDate = new Date(kickoff)
    const diffMs = kickoffDate.getTime() - loggedDate.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

    if (diffHours >= 24) {
      const days = Math.floor(diffHours / 24)
      return `${days}d ${diffHours % 24}h before`
    } else if (diffHours >= 1) {
      return `${diffHours}h ${diffMins}m before`
    } else if (diffMins >= 0) {
      return `${diffMins}m before`
    } else {
      return 'After kickoff'
    }
  }

  // Check if prediction is locked (after kickoff)
  const isLocked = (kickoff: string) => {
    return new Date(kickoff) < new Date()
  }

  // Generate FlashScore search URL for match
  const getExternalMatchUrl = (homeTeam: string, awayTeam: string) => {
    const searchTerm = encodeURIComponent(`${homeTeam} ${awayTeam}`)
    return `https://www.flashscore.com/search/?q=${searchTerm}`
  }

  const getOutcomeColor = (outcome: string) => {
    switch (outcome?.toLowerCase()) {
      case 'home':
        return 'bg-blue-100 text-blue-800'
      case 'draw':
        return 'bg-gray-100 text-gray-800'
      case 'away':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getCorrectnessBadge = (wasCorrect: boolean | null, isCompleted: boolean) => {
    if (!isCompleted) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <Clock className="h-3 w-3" />
          Pending
        </span>
      )
    }

    if (wasCorrect === true) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle2 className="h-3 w-3" />
          Correct
        </span>
      )
    } else if (wasCorrect === false) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <XCircle className="h-3 w-3" />
          Incorrect
        </span>
      )
    }

    return null
  }

  // --- Filter logic ---
  const uniqueLeagues = useMemo(() => {
    const leagues = Array.from(new Set(predictions.map(p => p.league))).sort()
    return leagues
  }, [predictions])

  const clearFilters = () => {
    setFilterLeague('all')
    setFilterDateFrom('')
    setFilterDateTo('')
    setFilterResult('all')
    setFilterOutcome('all')
  }

  const activeFilterCount = [
    filterLeague !== 'all',
    filterDateFrom !== '',
    filterDateTo !== '',
    filterResult !== 'all',
    filterOutcome !== 'all',
  ].filter(Boolean).length

  // Measured separation between right and wrong calls, over EVERY graded row
  // on this page — not the filtered view, so a visitor cannot narrow the
  // filters until the number flatters us.
  const discrimination = useMemo(
    () => computeDiscrimination(predictions),
    [predictions],
  )

  const filteredPredictions = useMemo(() => {
    return predictions.filter((pred) => {
      // League filter
      if (filterLeague !== 'all' && pred.league !== filterLeague) return false

      // Date range
      if (filterDateFrom) {
        const kickoff = new Date(pred.kickoff).toISOString().split('T')[0]
        if (kickoff < filterDateFrom) return false
      }
      if (filterDateTo) {
        const kickoff = new Date(pred.kickoff).toISOString().split('T')[0]
        if (kickoff > filterDateTo) return false
      }

      // Result (win/loss)
      if (filterResult === 'wins' && pred.was_correct !== true) return false
      if (filterResult === 'losses' && pred.was_correct !== false) return false

      // Predicted outcome
      if (filterOutcome !== 'all' && pred.predicted_outcome?.toLowerCase() !== filterOutcome) return false

      return true
    })
  }, [predictions, filterLeague, filterDateFrom, filterDateTo, filterResult, filterOutcome])

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 text-primary-600 animate-spin" />
          <span className="ml-3 text-gray-600">Loading recommended predictions...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-red-200">
        <div className="text-center py-12">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Predictions</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => fetchPredictions()}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Coverage counters — operational facts, never performance.
          This block used to carry an Accuracy percentage and a "Total P/L
          ($10 stakes)" figure computed across legacy rows with unverified
          prices, directly contradicting the verified record. The counts now
          reconcile too: total = completed + pending + no usable result. */}
      {summary && (
        <>
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm font-semibold text-blue-900">
              Pipeline coverage — not a performance record
            </p>
            <p className="mt-1 text-sm leading-relaxed text-blue-900">
              This page shows what the signal pipeline produced and whether each
              call matched the final score. Most rows below predate BetGlitch
              verifying its recorded prices, so no profit, ROI or accuracy
              figure is published here — those belong to the{' '}
              <a href="/track-record" className="font-semibold underline underline-offset-2">
                verified record
              </a>
              , which counts settled public commitments only.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
              <p className="text-sm text-gray-600">Signals tracked</p>
              <p className="text-2xl font-bold text-gray-900">{summary.total_recommended}</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
              {/* Matches the table: every row showing Correct or Incorrect. */}
              <p className="text-sm text-gray-600">Graded against a final score</p>
              <p className="text-2xl font-bold text-gray-900">{summary.graded}</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
              <p className="text-sm text-gray-600">Awaiting kickoff</p>
              <p className="text-2xl font-bold text-gray-900">{summary.pending}</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
              <p className="text-sm text-gray-600">Of those, audit-excluded</p>
              <p className="text-2xl font-bold text-gray-900">{summary.audit_excluded}</p>
              <p className="mt-1 text-xs text-gray-500">
                Graded, but quarantined from the audit universe
              </p>
            </div>
          </div>
        </>
      )}

      {/* Does the score actually separate right from wrong?
          A reviewer computed this from these very rows and used it against
          us. Publishing it ourselves is the only defensible answer: a
          prominent 0-100 number implies discriminating power, so the measured
          power belongs on the same page. It recomputes from live data, so it
          cannot drift away from reality. */}
      {discrimination && discrimination.auc !== null && (
        <div className="rounded-xl border border-gray-300 bg-white p-5 shadow-lg">
          <h3 className="text-base font-bold text-gray-900">
            Does the signal score separate right calls from wrong ones?
          </h3>
          <p className="mt-1 text-sm leading-relaxed text-gray-700">
            Measured on the {discrimination.sample} graded calls below. This is
            the question a 0–100 number invites, so here is the answer from our
            own data rather than a claim about it.
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Mean score when correct
              </p>
              <p className="text-2xl font-bold text-gray-900">
                {discrimination.meanCorrect.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">n = {discrimination.correct}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Mean score when incorrect
              </p>
              <p className="text-2xl font-bold text-gray-900">
                {discrimination.meanIncorrect.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">n = {discrimination.incorrect}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Separation
              </p>
              <p className="text-2xl font-bold text-gray-900">
                {discrimination.separation >= 0 ? '+' : ''}
                {discrimination.separation.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">points, out of 100</p>
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="flex flex-wrap items-baseline gap-x-3">
              <span className="text-xs uppercase tracking-wide text-gray-500">
                Ranking power (AUC)
              </span>
              <span className="text-2xl font-bold text-gray-900">
                {discrimination.auc.toFixed(3)}
              </span>
            </div>
            <p className="mt-1 text-sm font-medium text-gray-900">
              {describeAuc(discrimination.auc)}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-gray-600">
              Pick one correct call and one incorrect call at random: the
              correct one carries the higher score{' '}
              {(discrimination.auc * 100).toFixed(1)}% of the time. A score
              carrying no information at all would read 0.500.
            </p>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="py-2 pr-4 font-medium">Score band</th>
                  <th className="py-2 pr-4 font-medium">Correct</th>
                  <th className="py-2 pr-4 font-medium">Incorrect</th>
                  <th className="py-2 font-medium">Hit rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {discrimination.buckets.map((b) => (
                  <tr key={b.label}>
                    <td className="py-2 pr-4 text-gray-700">{b.label}</td>
                    <td className="py-2 pr-4 text-gray-900">{b.correct}</td>
                    <td className="py-2 pr-4 text-gray-900">{b.incorrect}</td>
                    <td className="py-2 font-medium text-gray-900">
                      {b.hitRate === null ? '—' : `${b.hitRate.toFixed(1)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 text-xs leading-relaxed text-gray-600">
            Read this carefully before reading anything into a score. These are
            legacy pipeline rows across mixed markets, graded on correctness
            only — they are not the verified record and say nothing about
            profitability. If the bands are not in ascending order, the score is
            not ordering outcomes reliably in this sample.
          </p>
        </div>
      )}

      {/* Filters & Controls */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        {/* Filter header - always visible */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors border border-gray-200"
            >
              <Filter className="h-4 w-4 text-blue-600" />
              Filters
              {activeFilterCount > 0 && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  {activeFilterCount}
                </span>
              )}
              {showFilters ? <ChevronUp className="h-3.5 w-3.5 text-gray-400" /> : <ChevronDown className="h-3.5 w-3.5 text-gray-400" />}
            </button>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includePending}
                onChange={(e) => setIncludePending(e.target.checked)}
                className="rounded text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-gray-700">Include Pending</span>
            </label>

            <span className="text-sm text-gray-500">
              Showing {filteredPredictions.length} of {predictions.length}
            </span>
          </div>

          <button
            onClick={() => fetchPredictions()}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {/* Collapsible filter body */}
        {showFilters && (
          <div className="px-4 pb-4 border-t border-gray-100 pt-3">
            {/* Row 1: Date range + League */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">From Date</label>
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

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">To Date</label>
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

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">League</label>
                <select
                  value={filterLeague}
                  onChange={(e) => setFilterLeague(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Leagues</option>
                  {uniqueLeagues.map((league) => (
                    <option key={league} value={league}>{league}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Result</label>
                <select
                  value={filterResult}
                  onChange={(e) => setFilterResult(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Results</option>
                  <option value="wins">Wins Only</option>
                  <option value="losses">Losses Only</option>
                </select>
              </div>
            </div>

            {/* Row 2: Predicted Outcome + Clear */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Predicted Outcome</label>
                <select
                  value={filterOutcome}
                  onChange={(e) => setFilterOutcome(e.target.value)}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Outcomes</option>
                  <option value="home">Home</option>
                  <option value="draw">Draw</option>
                  <option value="away">Away</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={clearFilters}
                  disabled={activeFilterCount === 0}
                  className="w-full flex items-center justify-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Clear Filters
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Desktop table.
          Hidden below `md` — a seven-column dataset in a horizontally
          scrolling container reads one column at a time on a phone, which a
          public reviewer (2026-08-08) correctly called unusable. The card
          list below carries the identical fields for small screens. */}
      <div className="hidden overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-lg md:block">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">League</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal score</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actual Outcome</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Result</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kickoff</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredPredictions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    {activeFilterCount > 0
                      ? 'No predictions match the current filters.'
                      : 'No recommended predictions found. Make sure predictions are marked as recommended.'
                    }
                  </td>
                </tr>
              ) : (
                filteredPredictions.map((pred) => (
                  <tr key={pred.fixture_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-start gap-2">
                        {isLocked(pred.kickoff) && (
                          <Lock className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                        )}
                        <div>
                          <a
                            href={getExternalMatchUrl(pred.home_team, pred.away_team)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-gray-900 hover:text-primary-600 hover:underline flex items-center gap-1"
                          >
                            {pred.home_team}
                            <ExternalLink className="h-3 w-3 opacity-50" />
                          </a>
                          <div className="text-sm text-gray-500">vs {pred.away_team}</div>
                          <div className="text-xs text-gray-400 mt-1" title={`Logged: ${new Date(pred.prediction_logged_at).toLocaleString()}`}>
                            🕐 {getLoggedBeforeKickoff(pred.prediction_logged_at, pred.kickoff)} kickoff
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{pred.league}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getOutcomeColor(pred.predicted_outcome)}`}>
                        {pred.predicted_outcome}
                      </span>
                      {/* No price here.
                          This cell rendered "@ 11.00 (bet365)" chosen by
                          string-matching the outcome against the 1X2 board, so
                          an Over 2.5 or BTTS row quoted a home/draw/away price
                          — the wrong-market defect that produced Cardiff BTTS
                          at 1.80 in the commitment and 8.70 here. The prices on
                          these legacy rows were never verified against the
                          exact market and bookmaker, so none is published.
                          Verified prices live on the public commitments. */}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2" style={{ width: '60px' }}>
                          <div
                            className="bg-primary-600 h-2 rounded-full"
                            style={{ width: `${pred.confidence}%` }}
                          ></div>
                        </div>
                        {/* "61.0%" read as a calibrated probability; the score
                            is a ranking and renders as N / 100 like everywhere
                            else. Null-guarded like the summary above. */}
                        <span className="text-sm text-gray-900">
                          {typeof pred.confidence === 'number' ? `${Math.round(pred.confidence)} / 100` : '—'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {pred.actual_outcome ? (
                        <>
                          <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getOutcomeColor(pred.actual_outcome)}`}>
                            {pred.actual_outcome}
                          </span>
                          {pred.actual_score_home !== null && pred.actual_score_away !== null && (
                            <div className="text-xs text-gray-500 mt-1">
                              {pred.actual_score_home} - {pred.actual_score_away}
                            </div>
                          )}
                        </>
                      ) : (
                        <span className="text-sm text-gray-400">Pending</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getCorrectnessBadge(pred.was_correct, pred.is_completed)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{formatDate(pred.kickoff)}</div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile cards — same fields, one fixture per block. */}
      <div className="space-y-3 md:hidden">
        {filteredPredictions.length === 0 ? (
          <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-gray-500 shadow-lg">
            {activeFilterCount > 0
              ? 'No predictions match the current filters.'
              : 'No signals found.'}
          </div>
        ) : (
          filteredPredictions.map((pred) => (
            <div
              key={pred.fixture_id}
              className="rounded-2xl border border-gray-200 bg-white p-4 shadow-lg"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {pred.home_team}
                  </p>
                  <p className="truncate text-sm text-gray-500">vs {pred.away_team}</p>
                  <p className="mt-1 truncate text-xs text-gray-400">{pred.league}</p>
                </div>
                {getCorrectnessBadge(pred.was_correct, pred.is_completed)}
              </div>

              <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-gray-100 pt-3 text-sm">
                <div>
                  <dt className="text-xs text-gray-500">Signal</dt>
                  <dd>
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${getOutcomeColor(pred.predicted_outcome)}`}>
                      {pred.predicted_outcome}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Signal score</dt>
                  <dd className="text-gray-900">
                    {typeof pred.confidence === 'number'
                      ? `${Math.round(pred.confidence)} / 100`
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Actual outcome</dt>
                  <dd className="text-gray-900">
                    {pred.actual_outcome ? (
                      <>
                        {pred.actual_outcome}
                        {pred.actual_score_home !== null && pred.actual_score_away !== null && (
                          <span className="text-gray-500">
                            {' '}({pred.actual_score_home}-{pred.actual_score_away})
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-gray-400">Pending</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500">Kickoff</dt>
                  <dd className="text-gray-900">{formatDate(pred.kickoff)}</dd>
                </div>
              </dl>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

