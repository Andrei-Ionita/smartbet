'use client'

import { useEffect, useState } from 'react'
import type { EvidenceStatus } from './useStrategyEvidence'

export interface StrategyFitProbability {
  kind: 'point_estimate' | 'bounded_score_distribution'
  model_probability_percent: number | null
  model_probability_low_percent: number | null
  model_probability_high_percent: number | null
  model_fair_odds: number | null
  market_no_vig_probability_percent: number | null
  score_distribution_coverage_percent: number | null
}

export interface StrategyFit {
  rank: number
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market: string
  selection: string
  side: string
  line: number | null
  odds: number
  bookmaker: string
  bookmaker_count: number
  price_captured_at: string
  observed_at: string
  break_even_probability_percent: number
  probability: StrategyFitProbability
  qualification: 'registered_rules_passed'
  fit_reasons: string[]
  caveats: string[]
}

export interface StrategyFitsReport {
  strategy_key: string
  version: string
  market: string
  evidence_status: EvidenceStatus
  generated_at: string
  eligible_fixture_count: number
  fits: StrategyFit[]
  policy: {
    maximum_fits: number
    empty_is_valid: boolean
    fit_is_public_pick: boolean
  }
}

export function useStrategyFits(strategyKey: string) {
  const [report, setReport] = useState<StrategyFitsReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setUnavailable(false)

    fetch(`/api/strategy-fits/${encodeURIComponent(strategyKey)}`, {
      cache: 'no-store',
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(String(response.status))
        return response.json()
      })
      .then((body) => {
        setReport(body?.data ?? null)
        setLoading(false)
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setUnavailable(true)
        setLoading(false)
      })

    return () => controller.abort()
  }, [strategyKey])

  return { report, loading, unavailable }
}
