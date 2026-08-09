/**
 * INTERNAL evidence feed — server-to-server only, never called from a browser.
 *
 * WHY THIS EXISTS SEPARATELY FROM /api/recommendations
 * ----------------------------------------------------
 * The public recommendations route answers "what should we show?", so it ranks,
 * picks one best market per fixture and discards the rest. The 2026-08-04
 * calibration audit found that this leaves no usable evidence: only the
 * selected side of a market was persisted, the raw provider probability was
 * thrown away in favour of a heuristic blend, and markets that never won the
 * ranking (BTTS, double chance) accumulated almost no rows at all.
 *
 * This route answers a different question — "what did the provider actually
 * say?" — and answers it for EVERY supported fixture-market-outcome before any
 * ranking happens. It performs no selection and expresses no opinion.
 *
 * SECURITY
 * --------
 * Fail-closed on a server-only shared secret, mirroring the pattern already
 * used by the backend's upgrade-tier endpoint (core/auth_views.py:300). The
 * secret is read from INTERNAL_API_SECRET — deliberately NOT prefixed
 * NEXT_PUBLIC_, so Next cannot inline it into a browser bundle. With the
 * variable unset the route returns 503 and serves nothing; it never falls open.
 */
import { NextRequest, NextResponse } from 'next/server'

import { MARKET_SPECS, type ProductMarket } from '@/app/lib/oddsSelection'
import { expectedValue as canonicalEV, priceMarket } from '@/app/lib/marketPricing'
import { calculateFormMomentum, calculateMarketScore } from '@/app/lib/heuristics'
import { buildFormMap, formFor, type ParsedForm } from '@/app/lib/providerForm'
import {
  formHeuristicActivationState,
  pipelineVersion,
} from '@/app/lib/modelActivation'
import {
  evaluateValueStrategy,
  fixturePredictability,
  leagueMarketPerformance,
  nativeValueBet,
} from '@/app/lib/providerStrategy'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/** Provider prediction type ids, mirroring the live pipeline exactly.
 *  237 = Fulltime Result, 231 = BTTS, 235 = Over/Under 2.5, 239 = Double chance. */
const PROVIDER_MARKETS: Record<ProductMarket, {
  typeId: number
  /** provider vector key -> our canonical outcome name */
  outcomeMap: Record<string, string>
}> = {
  '1x2': { typeId: 237, outcomeMap: { home: 'home', draw: 'draw', away: 'away' } },
  btts: { typeId: 231, outcomeMap: { yes: 'yes', no: 'no' } },
  'over_under_2.5': { typeId: 235, outcomeMap: { yes: 'over', no: 'under' } },
  double_chance: {
    typeId: 239,
    outcomeMap: { draw_home: '1x', draw_away: 'x2', home_away: '12' },
  },
}


/** Provider values arrive as percentages or fractions depending on the type. */
function normalize(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n) || n <= 0) return null
  return n > 1 ? n / 100 : n
}

const api = async (url: string) => {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30000)
  try {
    const res = await fetch(url, { signal: controller.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } finally {
    clearTimeout(timer)
  }
}

export async function GET(request: NextRequest) {
  const expected = process.env.INTERNAL_API_SECRET || ''
  if (!expected) {
    // Fail CLOSED. An unset secret must never mean "allow everyone".
    return NextResponse.json(
      { success: false, error: 'evidence feed is not configured' },
      { status: 503 },
    )
  }
  if (request.headers.get('x-internal-auth') !== expected) {
    return NextResponse.json({ success: false, error: 'unauthorized' }, { status: 401 })
  }

  const token = process.env.SPORTMONKS_API_TOKEN
  if (!token) {
    return NextResponse.json(
      { success: false, error: 'provider is not configured' },
      { status: 503 },
    )
  }

  const observedAt = new Date().toISOString()
  const days = Math.min(Math.max(Number(request.nextUrl.searchParams.get('days') ?? 5), 1), 14)
  const start = new Date()
  const end = new Date(Date.now() + days * 86400000)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)

  try {
    const leaguesData = await api(
      `https://api.sportmonks.com/v3/football/leagues?api_token=${token}&per_page=50`,
    )
    const leagueIds: number[] = (leaguesData.data || []).map((l: any) => l.id).slice(0, 30)

    const candidates: any[] = []
    let fixturesSeen = 0

    // Team form drives the Variant-B multiplier. It comes from STANDINGS, keyed
    // by participant_id — teams/multi returns 403 on this subscription. One
    // request per unique SEASON, deduplicated, so a 30-league sweep costs ~30
    // calls rather than one per fixture or per team.
    const formBySeason = new Map<number, Map<number, ParsedForm>>()
    let formRequests = 0
    let formMs = 0
    const loadSeasonForm = async (seasonId: number) => {
      if (!seasonId || formBySeason.has(seasonId)) return
      const began = Date.now()
      formRequests++
      try {
        const res = await api(
          `https://api.sportmonks.com/v3/football/standings/seasons/${seasonId}` +
            `?api_token=${token}&include=form`,
        )
        formBySeason.set(seasonId, buildFormMap([res]))
      } catch {
        // A missing season is a recorded absence, never a fabricated multiplier.
        formBySeason.set(seasonId, new Map())
      } finally {
        formMs += Date.now() - began
      }
    }

    for (const leagueId of leagueIds) {
      const params = new URLSearchParams({
        api_token: token,
        include: 'participants;league;metadata;predictions.type;odds;odds.bookmaker',
        filters: `fixtureLeagues:${leagueId}`,
        per_page: '50',
        page: '1',
      })
      let data: any
      let leaguePerformancePayload: any = { data: [] }
      try {
        const [fixturesResult, performanceResult] = await Promise.all([
          api(`https://api.sportmonks.com/v3/football/fixtures/between/${fmt(start)}/${fmt(end)}?${params}`),
          api(
            `https://api.sportmonks.com/v3/football/predictions/predictability/leagues/${leagueId}` +
            `?api_token=${token}&include=type&per_page=50`,
          ).catch(() => ({ data: [] })),
        ])
        data = fixturesResult
        leaguePerformancePayload = performanceResult
      } catch {
        continue // one league failing must not lose the whole sweep
      }

      const leagueFixtures = data.data || []
      const seasonIds = Array.from(
        new Set<number>(leagueFixtures.map((f: any) => f.season_id).filter(Boolean)),
      )
      for (const seasonId of seasonIds) await loadSeasonForm(seasonId)

      for (const fixture of leagueFixtures) {
        fixturesSeen++
        const preds = fixture.predictions || []
        if (!preds.length) continue

        const home = fixture.participants?.find((p: any) => p.meta?.location === 'home')
        const away = fixture.participants?.find((p: any) => p.meta?.location === 'away')

        for (const [market, cfg] of Object.entries(PROVIDER_MARKETS) as
          [ProductMarket, typeof PROVIDER_MARKETS[ProductMarket]][]) {
          const pred = preds.find((p: any) => p.type_id === cfg.typeId)
          if (!pred?.predictions) continue

          // Full vector first — never a single side.
          const vector: Record<string, number> = {}
          const rawVector: Record<string, number> = {}
          for (const [providerKey, outcome] of Object.entries(cfg.outcomeMap)) {
            const raw = pred.predictions[providerKey]
            const norm = normalize(raw)
            if (norm === null) continue
            vector[outcome] = norm
            rawVector[outcome] = typeof raw === 'number' ? raw : Number(raw)
          }
          const expectedOutcomes = Object.values(cfg.outcomeMap)
          const vectorComplete = expectedOutcomes.every((o) => o in vector)
          const vectorSum = Object.values(vector).reduce((s, v) => s + v, 0)

          // Price EVERY outcome the market needs, so a de-vigged baseline is
          // possible. A baseline from the selected side alone is not one.
          const priceVector: Record<string, unknown> = {}
          let pricedCount = 0
          for (const outcome of MARKET_SPECS[market].outcomes) {
            const price = priceMarket(fixture.odds, market, outcome)
            if (price.status === 'verified') {
              pricedCount++
              priceVector[outcome] = {
                odds: price.odds,
                bookmaker: price.provenance.odds_bookmaker_name,
                market_id: price.provenance.odds_market_id,
                odds_entry_id: price.provenance.odds_entry_id ?? null,
                captured_at: price.provenance.odds_captured_at,
                selection_policy: price.provenance.odds_selection_policy,
              }
            } else {
              priceVector[outcome] = { odds: null, reason: price.unavailable_reason }
            }
          }
          const priceVectorComplete =
            pricedCount === MARKET_SPECS[market].outcomes.length

          // ── Variant B: the CURRENT heuristic, recorded as-is ──────────────
          // The live route applies its form multiplier to the SELECTED outcome
          // only, and never renormalises the rest of the vector. That is not a
          // complete transformed vector and must not be recorded as one, so
          // only the selected side carries variant-B fields; every other
          // outcome stores null with the reason.
          const entries = Object.entries(vector).sort((a, b) => b[1] - a[1])
          const selectedOutcome = entries[0]?.[0]
          const gap = entries.length > 1 ? entries[0][1] - entries[1][1] : null

          const seasonForm = formBySeason.get(fixture.season_id) ?? new Map()
          const homeParsed = formFor(seasonForm, home?.id)
          const awayParsed = formFor(seasonForm, away?.id)
          const homeForm = homeParsed.letters
          const awayForm = awayParsed.letters
          const predictingHome = selectedOutcome === 'home' || selectedOutcome === '1x'
          const predictingAway = selectedOutcome === 'away' || selectedOutcome === 'x2'
          const homeMomentum = calculateFormMomentum(homeForm, true, predictingHome)
          const awayMomentum = calculateFormMomentum(awayForm, false, predictingAway)
          const formMultiplier = (homeMomentum.multiplier + awayMomentum.multiplier) / 2
          // Variant B needs at least one side with usable form; otherwise the
          // multiplier would be a fabricated 1.0 rather than a measurement.
          const haveForm = homeParsed.available || awayParsed.available
          const formReason = homeParsed.available || awayParsed.available
            ? ''
            : (homeParsed.reason || awayParsed.reason || 'provider_form_unavailable')

          const selectedPrice = selectedOutcome
            ? priceMarket(fixture.odds, market, selectedOutcome)
            : null
          const selectedEv =
            selectedOutcome && selectedPrice
              ? canonicalEV(vector[selectedOutcome], selectedPrice)
              : null
          const rawAdjusted = selectedOutcome
            ? vector[selectedOutcome] * formMultiplier
            : null
          const adjustedScore = rawAdjusted === null ? null : Math.min(rawAdjusted, 0.95)
          const capApplied = rawAdjusted !== null && rawAdjusted > 0.95
          const marketScore =
            selectedOutcome && gap !== null
              ? calculateMarketScore(gap, Math.max(selectedEv ?? 0, 0), vector[selectedOutcome])
              : null

          const fixtureQuality = fixturePredictability(fixture.metadata)
          const leaguePerformance = leagueMarketPerformance(
            leaguePerformancePayload,
            market,
          )
          const valueBet = nativeValueBet(preds)
          const strategyEvaluation =
            selectedOutcome && selectedPrice?.status === 'verified'
              ? evaluateValueStrategy({
                  market,
                  predictedOutcome: selectedOutcome,
                  metadata: fixture.metadata,
                  predictions: preds,
                  leaguePerformancePayload,
                  odds: selectedPrice.odds,
                  oddsProvenance: selectedPrice.provenance,
                  evaluatedAt: new Date(observedAt),
                })
              : null

          // One candidate per OUTCOME, including the side we would not pick.
          for (const outcome of Object.keys(vector)) {
            const price = priceMarket(fixture.odds, market, outcome)
            const isSelected = outcome === selectedOutcome
            candidates.push({
              fixture_id: fixture.id,
              home_team: home?.name ?? 'Home',
              away_team: away?.name ?? 'Away',
              league: fixture.league?.name ?? '',
              league_id: fixture.league?.id ?? null,
              kickoff: fixture.starting_at,
              observed_at: observedAt,
              market,
              outcome,
              provider: 'sportmonks',
              provider_type_id: cfg.typeId,
              provider_predicted_at: pred.updated_at ?? null,
              provider_model_version: pred.type?.code ?? '',
              raw_probability: rawVector[outcome],
              normalized_probability: vector[outcome],
              provider_context: {
                fixture_predictable: fixtureQuality,
                league_market_performance: leaguePerformance,
                native_value_bet: valueBet,
                strategy_evaluation: isSelected ? strategyEvaluation : null,
              },
              raw_vector: vector,
              vector_sum: vectorSum,
              vector_complete: vectorComplete,
              price_status: price.status,
              odds: price.status === 'verified' ? price.odds : null,
              bookmaker:
                price.status === 'verified'
                  ? price.provenance.odds_bookmaker_name
                  : '',
              odds_captured_at:
                price.status === 'verified'
                  ? price.provenance.odds_captured_at
                  : null,
              odds_provenance: price.status === 'verified' ? price.provenance : null,
              market_price_vector: priceVector,
              price_vector_complete: priceVectorComplete,
              // Variant B, only where the live pipeline actually computes it.
              is_selected_outcome: isSelected,
              probability_gap: isSelected ? gap : null,
              form_multiplier: isSelected && haveForm ? formMultiplier : null,
              form_inputs: isSelected
                ? {
                    home_form: homeForm || null,
                    away_form: awayForm || null,
                    home_reason: homeMomentum.reason,
                    away_reason: awayMomentum.reason,
                    home_form_count: homeParsed.count,
                    away_form_count: awayParsed.count,
                    home_form_available: homeParsed.available,
                    away_form_available: awayParsed.available,
                    home_missing_reason: homeParsed.reason,
                    away_missing_reason: awayParsed.reason,
                    home_multiplier: homeMomentum.multiplier,
                    away_multiplier: awayMomentum.multiplier,
                    predicting_home: predictingHome,
                    predicting_away: predictingAway,
                  }
                : null,
              adjusted_score: isSelected && haveForm ? adjustedScore : null,
              cap_applied: isSelected && haveForm ? capApplied : false,
              market_score: isSelected ? marketScore : null,
              ranking_ev: isSelected ? selectedEv : null,
              variant_b_available: Boolean(isSelected && haveForm),
              variant_b_missing_reason: isSelected
                ? (haveForm ? '' : formReason)
                : 'not_selected_outcome_live_route_only_transforms_selection',
              selection_reason: isSelected ? 'highest_provider_probability' : '',
              // Versioned so a row is always readable as which regime produced
              // it: evidence-v1 (inert parser), -v2-shadow, or -v2-live.
              pipeline_version: pipelineVersion(),
              live_activation_state: formHeuristicActivationState(),
              calculation_version:
                process.env.VERCEL_GIT_COMMIT_SHA ||
                process.env.RAILWAY_GIT_COMMIT_SHA ||
                'unknown',
            })
          }
        }
      }
    }

    return NextResponse.json({
      success: true,
      observed_at: observedAt,
      fixtures_seen: fixturesSeen,
      candidate_count: candidates.length,
      // Request accounting, so cost is visible rather than inferred.
      form_requests: formRequests,
      form_ms: formMs,
      seasons_seen: formBySeason.size,
      candidates,
    })
  } catch (error: any) {
    // Controlled error. No provider detail, no stack, no token.
    console.error('[evidence] sweep failed:', error?.message)
    return NextResponse.json(
      { success: false, error: 'evidence sweep failed' },
      { status: 502 },
    )
  }
}
