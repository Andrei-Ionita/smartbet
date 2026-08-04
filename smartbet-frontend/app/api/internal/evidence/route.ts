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
import { priceMarket } from '@/app/lib/marketPricing'

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

const PIPELINE_VERSION = 'evidence-v1'

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

    for (const leagueId of leagueIds) {
      const params = new URLSearchParams({
        api_token: token,
        include: 'participants;league;predictions;odds;odds.bookmaker',
        filters: `fixtureLeagues:${leagueId}`,
        per_page: '50',
        page: '1',
      })
      let data: any
      try {
        data = await api(
          `https://api.sportmonks.com/v3/football/fixtures/between/${fmt(start)}/${fmt(end)}?${params}`,
        )
      } catch {
        continue // one league failing must not lose the whole sweep
      }

      for (const fixture of data.data || []) {
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

          // One candidate per OUTCOME, including the side we would not pick.
          for (const outcome of Object.keys(vector)) {
            const price = priceMarket(fixture.odds, market, outcome)
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
              pipeline_version: PIPELINE_VERSION,
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
