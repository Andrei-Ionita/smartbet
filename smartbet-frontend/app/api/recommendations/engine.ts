/**
 * The recommendation engine. Shared by both routes, owned by neither.
 *
 * Returns the INTERNAL payload - expected value, pre-adjustment EV, value-zone
 * classification, score components - because the ranking needs all of it and
 * the scheduler ingests it.
 *
 * Publication is the CALLER's decision:
 *   app/api/recommendations/route.ts          -> serializes to the public DTO
 *   app/api/internal/recommendations/route.ts -> authenticates, returns raw
 *
 * This module deliberately expresses no opinion about who may see what, and
 * contains no auth branch. That is why it was extracted: one handler deciding
 * both what to compute AND who may see it could leak internal fields to the
 * public URL through a single misread condition.
 *
 * Nothing in the computation changed when it moved here.
 */

import { type OddsProvenance } from '@/app/lib/oddsSelection'
import {
  expectedValue as canonicalEV,
  priceMarket,
  type MarketPrice,
} from '@/app/lib/marketPricing'
import {
  calculateFormMomentum,
  calculateMarketScore,
  evaluateValueZone,
} from '@/app/lib/heuristics'
import { buildFormMap, formFor } from '@/app/lib/providerForm'
import { isFormHeuristicLive } from '@/app/lib/modelActivation'
import { RANKING_VERSION } from '@/app/lib/rankingPolicy'
import {
  emptyGemRejectionCounts,
  publicGemRejectionBreakdown,
  recordGemRejection,
} from '@/app/lib/gemDiagnostics'
import {
  compareGemStrategy,
  evaluateValueStrategy,
  VALUE_STRATEGY_POLICY,
} from '@/app/lib/providerStrategy'


// Simplified inline apiClient implementation with Timeout
const apiClient = {
  async request(url: string) {
    const controller = new AbortController()
    // 10 second timeout for external API calls to avoid AbortError on slow responses
    const timeoutId = setTimeout(() => controller.abort(), 30000)
    try {
      const response = await fetch(url, { signal: controller.signal })
      clearTimeout(timeoutId)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return response.json()
    } catch (e: any) {
      clearTimeout(timeoutId)
      throw e
    }
  }
}

// Helper function to get API token
function getApiToken(): string {
  const token = process.env.SPORTMONKS_API_TOKEN
  if (!token) {
    throw new Error('SPORTMONKS_API_TOKEN environment variable is not set')
  }
  return token
}

// ============= MULTI-MARKET CONFIGURATION =============
// Market Type IDs from SportMonks API
// NOTE: SportMonks odds market_ids deliberately live in app/lib/oddsSelection.ts
// (MARKET_SPECS), not here. The stale values previously in this block (28/18/12)
// were wrong — 28 is "1st Half Goals" — and contributed to the 2026-07-29
// odds-capture defect. Do not reintroduce them.
const MARKET_CONFIG = {
  '1x2': {
    name: '1X2',
    display_name: 'Match Result',
    // Bugfix (2026-07-25): previously [233, 237, 238], averaged as if they were
    // three models of the same 1X2 outcome. They are three DIFFERENT markets:
    //   233 = First Half Winner Probability   (who leads at half-time)
    //   237 = Fulltime Result Probability      (the actual match winner — real 1X2)
    //   238 = Team To Score First Probability  (who scores first)
    // All three return {home, draw, away} shape so the average did not error, it
    // just produced a semantically meaningless blend (e.g. a side likely to score
    // first but lose the match muddied the signal). 237 is the correct and only
    // fulltime-result model. Verified via SportMonks /core/types lookup.
    type_ids: [237],
    outcomes: ['home', 'draw', 'away'],
    min_gap: 0.12,  // 12% for home/away, 15% for draw (handled in code)
  },
  'btts': {
    name: 'BTTS',
    display_name: 'Both Teams to Score',
    type_ids: [231],
    outcomes: ['yes', 'no'],
    min_gap: 0.12,
  },
  'over_under_2.5': {
    name: 'O/U 2.5',
    display_name: 'Over/Under 2.5 Goals',
    type_ids: [235],
    outcomes: ['yes', 'no'],  // yes = over, no = under
    min_gap: 0.12,
  },
  'double_chance': {
    name: 'DC',
    display_name: 'Double Chance',
    type_ids: [239],
    outcomes: ['draw_home', 'draw_away', 'home_away'],  // 1X, X2, 12
    min_gap: 0.10,  // Lower gap since each outcome has ~33% base
  }
} as const

type MarketType = keyof typeof MARKET_CONFIG

interface MarketPrediction {
  market_type: MarketType
  type_id: number
  predicted_outcome: string
  probability: number
  probability_gap: number
  /** `null` when no canonical quote exists. Never a placeholder. */
  odds: number | null
  /** `null` whenever `odds` is null — EV without a price is not a number. */
  expected_value: number | null
  market_score: number
  raw_predictions: Record<string, number>
  price_status: MarketPrice['status']
  /**
   * Full audit trail for the selected price (market, line, label, bookmaker).
   * Null when no valid quote exists for the exact market — in that case the
   * market must NOT be recommended (see the 2026-07-29 odds-capture audit).
   */
  odds_provenance: OddsProvenance | null
  /** Why a price was unavailable, when it was. */
  odds_unavailable_reason?: string
}

/**
 * A market qualifies only on the strength of a price we would publish. With no
 * canonical quote there is no EV, so it cannot clear the floor — the same
 * outcome the previous `oddsValue = 1` placeholder produced (EV always
 * negative), now for the honest reason rather than by arithmetic accident.
 */
function clearsEV(ev: number | null, floor: number): boolean {
  return ev !== null && ev >= floor
}

// Calculate MarketScore = (probability_gap × 0.4) + (expected_value × 0.3) + (confidence × 0.3)

/**
 * The recommendation engine, shared by BOTH routes.
 *
 * It returns the INTERNAL payload — expected value, the pre-adjustment EV, the
 * value-zone classification, the score components — because ranking needs all
 * of it and the scheduler ingests it.
 *
 * Publication is a separate decision made by the caller:
 *   /api/recommendations           serializes through toPublicRecommendationList
 *   /api/internal/recommendations  authenticates, then returns this verbatim
 *
 * The two used to be one route that branched on a header. That worked, but it
 * meant a single misread condition anywhere in the handler could serve internal
 * fields on the public URL, and it made the public response cacheable under a
 * key that a header-bearing request could populate. Two routes cannot be
 * confused by a boolean.
 *
 * Nothing in the computation below changed when it was extracted.
 */
export async function buildRecommendationPayload(): Promise<
  { ok: false; status: number; body: Record<string, unknown> }
  | { ok: true; recommendations: any[]; envelope: Record<string, unknown>; confidenceThreshold: number }
> {
  {
    console.log('🔍 Fetching real recommendations from SportMonks - no test data')

    // Only use real SportMonks data - no test data fallback
    const token = process.env.SPORTMONKS_API_TOKEN
    if (!token) {
      console.error('❌ SPORTMONKS_API_TOKEN not found in environment')
      return {
        ok: false,
        status: 500,
        body: {
          recommendations: [],
          total: 0,
          leagues_covered: 0,
          fixtures_analyzed: 0,
          fixtures_with_predictions: 0,
          lastUpdated: new Date().toISOString(),
          error: 'API configuration error - no real data available'
        },
      }
    }

    // Calculate date range for next 14 days
    const now = new Date()
    const fourteenDaysFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000)
    const startDate = now.toISOString().split('T')[0]
    const endDate = fourteenDaysFromNow.toISOString().split('T')[0]

    // The competitions swept for signals. Mirrored, and asserted equal, by
    // SIGNAL_COMPETITION_IDS in app/lib/coverage.ts — the single source of
    // truth for every coverage number the product displays. Changing this list
    // changes pipeline behaviour, so change it deliberately and let the
    // coverage test tell you which public copy needs to follow.
    const keyLeagues = [
      { id: 8, name: 'Premier League' },
      { id: 9, name: 'Championship' },
      { id: 24, name: 'FA Cup' },
      { id: 27, name: 'Carabao Cup' },
      { id: 72, name: 'Eredivisie' },
      { id: 82, name: 'Bundesliga' },
      { id: 181, name: 'Admiral Bundesliga' },
      { id: 208, name: 'Pro League' },
      { id: 244, name: '1. HNL' },
      { id: 271, name: 'Superliga' },
      { id: 301, name: 'Ligue 1' },
      { id: 384, name: 'Serie A' },
      { id: 387, name: 'Serie B' },
      { id: 390, name: 'Coppa Italia' },
      { id: 444, name: 'Eliteserien' },
      { id: 453, name: 'Ekstraklasa' },
      { id: 462, name: 'Liga Portugal' },
      { id: 486, name: 'Russian Premier League' },
      { id: 501, name: 'Premiership' },
      { id: 564, name: 'La Liga' },
      { id: 567, name: 'La Liga 2' },
      { id: 570, name: 'Copa Del Rey' },
      { id: 573, name: 'Allsvenskan' },
      { id: 591, name: 'Super League' },
      { id: 600, name: 'Super Lig' },
      { id: 609, name: 'Premier League (additional)' },
      { id: 1371, name: 'UEFA Europa League Play-offs' }
    ]

    const allRecommendations: any[] = []
    let totalFixtures = 0
    let fixturesWithPredictions = 0
    let strategyEvaluatedFixtures = 0
    const strategyRejectionCounts = emptyGemRejectionCounts()

    // Limited loop for safety if needed, but processing keyLeagues logic remains
    for (const league of keyLeagues) {
      try {
        const url = `https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`
        const params = new URLSearchParams({
          api_token: token,
          include: 'participants;league;metadata;predictions.type;odds;odds.bookmaker;sidelined',
          filters: `fixtureLeagues:${league.id}`,
          per_page: '50',
          page: '1',
          timezone: 'Europe/Bucharest'
        })

        const performanceUrl =
          `https://api.sportmonks.com/v3/football/predictions/predictability/leagues/${league.id}` +
          `?api_token=${token}&include=type&per_page=50`
        const [data, leaguePerformancePayload] = await Promise.all([
          apiClient.request(`${url}?${params}`),
          // Missing report-card data is not silently treated as positive
          // evidence. The strategy evaluator receives an empty payload and
          // rejects the candidate with a diagnostic reason.
          apiClient.request(performanceUrl).catch(() => ({ data: [] })),
        ])
        const fixtures = data.data || []
        totalFixtures += fixtures.length

        // Process fixtures with predictions and odds
        let hasLogged = false
        for (const fixture of fixtures) {
          if (!hasLogged) {
            console.log('🔍 Sample Participant Data:', JSON.stringify(fixture.participants?.[0], null, 2))
            hasLogged = true
          }
          const predictions = fixture.predictions || []

          // Get all market type IDs we support
          const allSupportedTypeIds = Object.values(MARKET_CONFIG).flatMap(m => m.type_ids)
          const relevantPredictions = predictions.filter((p: any) => allSupportedTypeIds.includes(p.type_id))

          // For backwards compatibility, also check for 1X2 specifically
          const x12Predictions = predictions.filter((p: any) => MARKET_CONFIG['1x2'].type_ids.includes(p.type_id))

          if (relevantPredictions.length > 0 && fixture.odds && fixture.odds.length > 0) {
            fixturesWithPredictions++

            const homeParticipant = fixture.participants?.find((p: any) => p.meta?.location === 'home')
            const awayParticipant = fixture.participants?.find((p: any) => p.meta?.location === 'away')
            const homeTeam = homeParticipant?.name || 'Home'
            const awayTeam = awayParticipant?.name || 'Away'
            const homeId = homeParticipant?.id
            const awayId = awayParticipant?.id

            // Smart conversion
            const normalizeProbability = (value: number) => {
              if (!value || value <= 0) return 0
              if (value > 1) return value / 100
              return value
            }

            // ============= MULTI-MARKET PROCESSING =============
            // Process each market type and find the best one
            // allMarketsData = ALL markets for display (even if they don't pass filters)
            // marketResults = Only markets that pass filters (for best market selection)
            const allMarketsData: MarketPrediction[] = []
            const marketResults: MarketPrediction[] = []

            // --- 1X2 Market ---
            if (x12Predictions.length > 0) {
              const x12Data = x12Predictions.map((pred: any) => ({
                home: normalizeProbability(pred.predictions.home || 0),
                draw: normalizeProbability(pred.predictions.draw || 0),
                away: normalizeProbability(pred.predictions.away || 0)
              }))
              const avgHome = x12Data.reduce((s: number, p: any) => s + p.home, 0) / x12Data.length
              const avgDraw = x12Data.reduce((s: number, p: any) => s + p.draw, 0) / x12Data.length
              const avgAway = x12Data.reduce((s: number, p: any) => s + p.away, 0) / x12Data.length

              const probs = [avgHome, avgDraw, avgAway]
              const sortedProbs = [...probs].sort((a, b) => b - a)
              const maxProb = sortedProbs[0]
              const gap = sortedProbs[0] - sortedProbs[1]

              let outcome = 'draw'
              if (maxProb === avgHome) outcome = 'home'
              else if (maxProb === avgAway) outcome = 'away'

              // Deterministic price: market_id 1 ("Fulltime Result"), exact label.
              const x12Price = priceMarket(fixture.odds, '1x2', outcome)
              const ev = canonicalEV(maxProb, x12Price)
              const minGap = outcome === 'draw' ? 0.15 : 0.12

              const marketData: MarketPrediction = {
                market_type: '1x2',
                type_id: x12Predictions[0].type_id,
                predicted_outcome: outcome.charAt(0).toUpperCase() + outcome.slice(1),
                probability: maxProb,
                probability_gap: gap,
                odds: x12Price.status === 'verified' ? x12Price.odds : null,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev ?? 0, 0), maxProb),
                raw_predictions: { home: avgHome, draw: avgDraw, away: avgAway },
                price_status: x12Price.status,
                odds_provenance: x12Price.status === 'verified' ? x12Price.provenance : null,
                odds_unavailable_reason: x12Price.unavailable_reason
              }

              // Always add to display array
              allMarketsData.push(marketData)

              // Do not make our own EV the eligibility gate. BetGlitch has not
              // calibrated this provider score, so score*odds-1 is not a
              // defensible bet/no-bet test. The provider's dedicated value-bet
              // model is checked after canonical price selection instead.
              if (gap >= minGap && x12Price.status === 'verified') {
                marketResults.push(marketData)
              }
            }

            // --- BTTS Market ---
            const bttsPrediction = predictions.find((p: any) => p.type_id === 231)
            if (bttsPrediction) {
              const yesProb = normalizeProbability(bttsPrediction.predictions.yes || 0)
              const noProb = normalizeProbability(bttsPrediction.predictions.no || 0)
              const gap = Math.abs(yesProb - noProb)
              const maxProb = Math.max(yesProb, noProb)
              const outcome = yesProb > noProb ? 'yes' : 'no'

              // Deterministic price: market_id 14 ("Both Teams to Score") only —
              // markets 15/16 are the 1st/2nd half variants and must never match.
              const bttsPrice = priceMarket(fixture.odds, 'btts', outcome)
              const ev = canonicalEV(maxProb, bttsPrice)

              const marketData: MarketPrediction = {
                market_type: 'btts',
                type_id: 231,
                predicted_outcome: outcome === 'yes' ? 'BTTS Yes' : 'BTTS No',
                probability: maxProb,
                probability_gap: gap,
                odds: bttsPrice.status === 'verified' ? bttsPrice.odds : null,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev ?? 0, 0), maxProb),
                raw_predictions: { yes: yesProb, no: noProb },
                price_status: bttsPrice.status,
                odds_provenance: bttsPrice.status === 'verified' ? bttsPrice.provenance : null,
                odds_unavailable_reason: bttsPrice.unavailable_reason
              }

              allMarketsData.push(marketData)
              if (gap >= 0.12 && clearsEV(ev, 0.05)) {
                marketResults.push(marketData)
              }
            }

            // --- Over/Under 2.5 Market ---
            const ouPrediction = predictions.find((p: any) => p.type_id === 235)
            if (ouPrediction) {
              const overProb = normalizeProbability(ouPrediction.predictions.yes || 0)
              const underProb = normalizeProbability(ouPrediction.predictions.no || 0)
              const gap = Math.abs(overProb - underProb)
              const maxProb = Math.max(overProb, underProb)
              const outcome = overProb > underProb ? 'over' : 'under'

              // 2026-07-29 DEFECT FIX. The previous matcher accepted ANY market
              // whose name/label contained "2.5" and took the first in arbitrary
              // API order — so a SECOND-HALF Over 2.5 quote (market_id 53,
              // legitimately ~3.50) could price a FULL-TIME pick worth ~1.60.
              // That inflated portfolio ROI from -4.90% to +10.61%.
              // Now: market_id 80/7 only, exact 2.5 line, exact label.
              const ouPrice = priceMarket(fixture.odds, 'over_under_2.5', outcome)

              // With no canonical quote there is no EV at all, so this market
              // cannot clear the floor below and cannot be recommended.
              const ev = canonicalEV(maxProb, ouPrice)

              const marketData: MarketPrediction = {
                market_type: 'over_under_2.5',
                type_id: 235,
                predicted_outcome: outcome === 'over' ? 'Over 2.5' : 'Under 2.5',
                probability: maxProb,
                probability_gap: gap,
                odds: ouPrice.status === 'verified' ? ouPrice.odds : null,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev ?? 0, 0), maxProb),
                raw_predictions: { over: overProb, under: underProb },
                price_status: ouPrice.status,
                odds_provenance: ouPrice.status === 'verified' ? ouPrice.provenance : null,
                odds_unavailable_reason: ouPrice.unavailable_reason
              }

              allMarketsData.push(marketData)

              // Fulltime-result confluence gate. SportMonks runs a dedicated
              // fulltime-result model (type_id 237, "Fulltime Result
              // Probability") in parallel with the O/U 2.5 model (type_id 235).
              // When 237's most-likely outcome exceeds 60% probability, the
              // fixture is being modeled with high overall conviction and our
              // O/U 2.5 picks land materially more often.
              // Backtest (n=252, 2026-07-23):
              //   baseline ROI +4.34% (wr 59.5%)
              //   filter >=60 ROI +14.5% (wr 68%, n=114)
              //   filter >=60 train-test split: train +7.97% / test +19.77%
              //   consistent lift across both time halves.
              const fulltimePred = predictions.find((p: any) => p.type_id === 237)
              let fulltimeConfluenceOK = true
              if (fulltimePred?.predictions) {
                const p237 = fulltimePred.predictions
                const maxProb237 = Math.max(
                  Number(p237.home) || 0,
                  Number(p237.away) || 0,
                  Number(p237.draw) || 0
                )
                fulltimeConfluenceOK = maxProb237 >= 60
              }

              // Valuebet confluence gate. SportMonks runs a dedicated value-bet
              // detector (type_id 33) that fires when it finds edge on ANY market
              // for this fixture. Presence of the flag is itself a quality signal:
              // fixtures where SportMonks can find value are being modeled well
              // enough that our O/U 2.5 picks land materially more often.
              // Backtest (n=252, 2026-07-24):
              //   BOTH gates fire (237>=60 AND has_33): n=32, ROI +41.75%, wr 84.4%
              //   Only 237 fires:                       n=25, ROI +14.86%, wr 76.0%
              //   Only 33 fires:                        n=79, ROI +5.42%,  wr 57.0%
              //   Neither:                              n=116, ROI -8.98%, wr 50.9%
              // Stacking both gates gives max quality at the cost of ~80% volume drop.
              const valuebetPred = predictions.find((p: any) => p.type_id === 33)
              const valuebetConfluenceOK = !!valuebetPred

              // Sidelined confluence gate — orthogonal STRUCTURAL signal (not
              // derived from any prediction model). When teams have many injuries,
              // defenses are compromised and OVER 2.5 picks land more often.
              // Backtest on n=252 (2026-07-24):
              //   sidelined>=4 alone: n=190, ROI +10.61%, wr 63.2% (vs baseline +4.34%)
              //   sidelined 0-3 (fresh lineups): n=62, ROI -14.85% -- losing zone
              //   Stacked on 237+33: n=25, ROI +57.46%, wr 92% (vs stack-only +41.75%)
              // Removes 7 losing bets from the current stack (the "fresh lineup" outliers).
              const sidelinedList = (fixture.sidelined || []) as any[]
              const sidelinedTotal = sidelinedList.length
              const sidelinedConfluenceOK = sidelinedTotal >= 4

              // Hard-block Under 2.5: backtest on 203 settled rows shows dropping it
              // lifts yield from 13.76% to 21.60%. The model overrates this outcome
              // (41.7% historical accuracy vs 77.4% for Over 2.5). Under 2.5 still
              // surfaces in `all_markets` for transparency; just not as a pick.
              if (outcome === 'over' && gap >= 0.12 && clearsEV(ev, 0.05) && fulltimeConfluenceOK && valuebetConfluenceOK && sidelinedConfluenceOK) {
                marketResults.push(marketData)
              }
            }

            // --- Double Chance Market ---
            const dcPrediction = predictions.find((p: any) => p.type_id === 239)
            if (dcPrediction) {
              const homeOrDraw = normalizeProbability(dcPrediction.predictions.draw_home || 0)
              const awayOrDraw = normalizeProbability(dcPrediction.predictions.draw_away || 0)
              const homeOrAway = normalizeProbability(dcPrediction.predictions.home_away || 0)

              const probs = [homeOrDraw, awayOrDraw, homeOrAway]
              const sortedProbs = [...probs].sort((a, b) => b - a)
              const maxProb = sortedProbs[0]
              const gap = sortedProbs[0] - sortedProbs[1]

              let outcome = '1X'
              if (maxProb === awayOrDraw) outcome = 'X2'
              else if (maxProb === homeOrAway) outcome = '12'

              // Deterministic price: market_id 2 ("Double Chance") only — market 47
              // is the half-time variant. Real payloads label these with TEAM NAMES
              // ("Cambuur Leeuwarden or Draw"), which the previous exact-string
              // match never handled, so DC odds effectively never resolved.
              const dcPrice = priceMarket(fixture.odds, 'double_chance', outcome, {
                homeTeam: fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name,
                awayTeam: fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name,
              })
              const ev = canonicalEV(maxProb, dcPrice)

              const marketData: MarketPrediction = {
                market_type: 'double_chance',
                type_id: 239,
                predicted_outcome: outcome,
                probability: maxProb,
                probability_gap: gap,
                odds: dcPrice.status === 'verified' ? dcPrice.odds : null,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev ?? 0, 0), maxProb),
                raw_predictions: { '1X': homeOrDraw, 'X2': awayOrDraw, '12': homeOrAway },
                price_status: dcPrice.status,
                odds_provenance: dcPrice.status === 'verified' ? dcPrice.provenance : null,
                odds_unavailable_reason: dcPrice.unavailable_reason
              }

              allMarketsData.push(marketData)
              if (gap >= 0.10 && clearsEV(ev, 0.05)) {
                marketResults.push(marketData)
              }
            }

            // ============= SELECT BEST MARKET =============
            // Uniform confidence floor. The response advertises a 55% confidence
            // threshold, but historically only over_under_2.5 enforced it — the
            // 1x2/btts/dc branches gated on gap+ev only, letting sub-0.55 picks
            // (1x2 coin-flips at ~0.48) reach the homepage whenever the tighter
            // O/U 2.5 stack produced nothing. Enforce >= 0.55 on `probability`
            // (max side probability, 0-1 scale) for EVERY market so the advertised
            // threshold is real. If nothing clears the floor, the fixture is
            // skipped (honest empty slot) rather than filled with a coin-flip.
            const CONFIDENCE_FLOOR = 0.55
            // Generation 2 promotes only the market for which the provider's
            // native VALUEBET object supplies a direction, fair odd and active
            // state. Other markets remain in the append-only evidence feed.
            const qualifiedMarkets = marketResults.filter(
              m => m.market_type === '1x2' && m.probability >= CONFIDENCE_FLOOR,
            )

            // Sort by market_score descending and pick the best
            qualifiedMarkets.sort((a, b) => b.market_score - a.market_score)
            const bestMarket = qualifiedMarkets[0]

            // Skip if no valid market found
            if (!bestMarket) {
              continue
            }

            // A qualified market always cleared an EV floor, which is only
            // reachable with a canonical price — assert it rather than assume it,
            // so a future edit to the filters cannot let an unpriced market reach
            // the publication payload.
            const bestMarketProvenance = bestMarket.odds_provenance
            if (
              bestMarket.price_status !== 'verified' ||
              bestMarket.odds === null ||
              bestMarket.expected_value === null ||
              bestMarketProvenance === null
            ) {
              continue
            }
            const bestMarketOdds: number = bestMarket.odds
            const bestMarketEV: number = bestMarket.expected_value

            const strategyEvaluation = evaluateValueStrategy({
              market: bestMarket.market_type,
              predictedOutcome: bestMarket.predicted_outcome,
              metadata: fixture.metadata,
              predictions,
              leaguePerformancePayload,
              odds: bestMarketOdds,
              oddsProvenance: bestMarketProvenance,
            })
            strategyEvaluatedFixtures++
            if (!strategyEvaluation.eligible) {
              recordGemRejection(
                strategyRejectionCounts,
                strategyEvaluation.rejectionReasons,
              )
              continue
            }

            // For backwards compatibility, also keep 1X2 specific data
            const allX12Predictions = x12Predictions.map((pred: any) => ({
              type_id: pred.type_id,
              predictions: pred.predictions,
              home: normalizeProbability(pred.predictions.home || 0),
              draw: normalizeProbability(pred.predictions.draw || 0),
              away: normalizeProbability(pred.predictions.away || 0)
            }))

            const consensusHome = allX12Predictions.length > 0 ? allX12Predictions.reduce((sum: number, pred: any) => sum + pred.home, 0) / allX12Predictions.length : 0
            const consensusDraw = allX12Predictions.length > 0 ? allX12Predictions.reduce((sum: number, pred: any) => sum + pred.draw, 0) / allX12Predictions.length : 0
            const consensusAway = allX12Predictions.length > 0 ? allX12Predictions.reduce((sum: number, pred: any) => sum + pred.away, 0) / allX12Predictions.length : 0

            const bestPred = allX12Predictions.reduce((best: any, current: any) => {
              const currentMax = Math.max(current.home, current.draw, current.away)
              const bestMax = Math.max(best.home, best.draw, best.away)
              return currentMax > bestMax ? current : best
            })

            const rawPredictions = bestPred.predictions

            const predictionData = {
              home: normalizeProbability(rawPredictions.home || 0),
              draw: normalizeProbability(rawPredictions.draw || 0),
              away: normalizeProbability(rawPredictions.away || 0)
            }

            // Extract Form Data
            // SportMonks returns form in various ways, check meta or direct property
            const getForm = (p: any) => {
              if (!p) return '?????'
              // Check direct form property
              if (p.form) return typeof p.form === 'string' ? p.form : JSON.stringify(p.form)
              // Check meta form
              if (p.meta?.form) return p.meta.form
              // Check last 5 games if specific fields exist (fallback)
              return '?????'
            }

            const teamsData = {
              home: { form: getForm(homeParticipant) },
              away: { form: getForm(awayParticipant) }
            }

            const x12Odds = fixture.odds.filter((odd: any) => odd.market_id === 1)
            let oddsData: any = null

            if (x12Odds.length > 0) {
              const getBookmakerName = (odd: any) => {
                if (odd.bookmaker?.name) return odd.bookmaker.name
                if (odd.bookmaker_name) return odd.bookmaker_name
                // ... simplified for brevity, assume maps exist ...
                return `Bookmaker ${odd.bookmaker_id || 'Unknown'}`
              }

              const odds = {
                home: null as number | null, draw: null as number | null, away: null as number | null,
                home_bookmaker: null as string | null, draw_bookmaker: null as string | null, away_bookmaker: null as string | null
              }

              for (const odd of x12Odds) {
                const bookmakerName = getBookmakerName(odd)
                const oddValue = parseFloat(odd.value)
                if (odd.label.toLowerCase() === 'home') { odds.home = oddValue; odds.home_bookmaker = bookmakerName }
                else if (odd.label.toLowerCase() === 'draw') { odds.draw = oddValue; odds.draw_bookmaker = bookmakerName }
                else if (odd.label.toLowerCase() === 'away') { odds.away = oddValue; odds.away_bookmaker = bookmakerName }
              }

              oddsData = { ...odds, bookmaker: odds.home_bookmaker || 'Multiple' }
            }

            const maxProb = Math.max(predictionData.home, predictionData.draw, predictionData.away)
            let predictedOutcome = 'draw'
            if (maxProb === predictionData.home) predictedOutcome = 'home'
            else if (maxProb === predictionData.away) predictedOutcome = 'away'

            // ============= APPLY ACCURACY ENHANCEMENTS =============

            // Enhancement #1: Form Momentum Adjustment
            const homeForm = teamsData.home.form
            const awayForm = teamsData.away.form

            // Determine if prediction favors home, away, or neither (draw)
            const predictedOutcomeLower = bestMarket.predicted_outcome.toLowerCase()
            const predictingHome = predictedOutcomeLower === 'home' ||
              predictedOutcomeLower.includes('1x') ||
              predictedOutcomeLower.includes('12')
            const predictingAway = predictedOutcomeLower === 'away' ||
              predictedOutcomeLower.includes('x2') ||
              predictedOutcomeLower.includes('12')

            const homeMomentum = calculateFormMomentum(homeForm, true, predictingHome)
            const awayMomentum = calculateFormMomentum(awayForm, false, predictingAway)

            // Combine momentum effects (average the multipliers)
            const formMultiplier = (homeMomentum.multiplier + awayMomentum.multiplier) / 2
            const formReasons = [homeMomentum.reason, awayMomentum.reason]
              .filter(r => r !== 'No form data' && r !== 'Form is mixed')

            // Enhancement #2: Value Zone Filtering
            const valueZone = evaluateValueZone(bestMarketEV)

            // Apply adjustments to probability and score
            // Variant B is computed for evidence and parity, but it reaches
            // PUBLIC output only behind the activation flag. The parser repair
            // on 2026-08-05 made this multiplier real for the first time; the
            // heuristic has still never been tested against a settled fixture,
            // so the public route keeps using the raw provider probability
            // (Variant A) — the same effective behaviour that shipped while the
            // multiplier was stuck at 1.0.
            const shadowAdjustedProbability = Math.min(
              bestMarket.probability * formMultiplier,
              0.95 // Cap at 95% to avoid overconfidence
            )
            const adjustedProbability = isFormHeuristicLive()
              ? shadowAdjustedProbability
              : bestMarket.probability
            const adjustedScore = Math.max(
              bestMarket.market_score - valueZone.scorePenalty,
              0
            )
            const adjustedEV = valueZone.adjustedEV

            const confidence = adjustedProbability * 100
            const probabilityGap = bestMarket.probability_gap

            // Use the best market's data for the recommendation
            const marketConfig = MARKET_CONFIG[bestMarket.market_type]

            // Public enhancement metadata.
            //
            // The form_adjustment block is deliberately ABSENT. It exposed the
            // Variant-B multiplier, the shadow-adjusted probability, the raw
            // form inputs and the server-side activation state — an unvalidated
            // heuristic and an internal switch, neither of which belongs in a
            // public response. Variant B is reachable only through the
            // authenticated evidence feed and SignalObservation.
            // `original_ev` and `adjusted_ev` no longer ship. The rendered card
            // stopped publishing a numeric expected value, but the API kept
            // emitting both figures — a public numeric EV is a public numeric
            // EV whether a component renders it or a reader opens the JSON, and
            // anyone building on this feed would have taken them as an
            // assessment BetGlitch has made. EV is derived from the signal
            // score, which is a ranking, so no figure is defensible.
            //
            // The zone label stays: it is a data-quality verdict about the
            // PRICE ('trap' means the quote looks like a provider error), not a
            // claim about value, and suppressing it would hide a caveat.
            //
            // The form_adjustment block is deliberately ABSENT. It exposed the
            // Variant-B multiplier, the shadow-adjusted probability, the raw
            // form inputs and the server-side activation state — an unvalidated
            // heuristic and an internal switch, neither of which belongs in a
            // public response. Variant B is reachable only through the
            // authenticated evidence feed and SignalObservation.
            const enhancementData = {
              value_zone: {
                zone: valueZone.zone,
                warning: valueZone.warning,
              },
              // Reports the value-zone adjustment only. The form heuristic is
              // never applied to public output while activation is off, so
              // including it here would leak its state by implication.
              adjustments_applied: valueZone.scorePenalty > 0
            }

            allRecommendations.push({
              fixture_id: fixture.id,
              home_team: homeTeam,
              away_team: awayTeam,
              home_id: homeId,
              away_id: awayId,
              season_id: fixture.season_id,
              league: league.name,
              kickoff: fixture.starting_at,
              // Use best market's predicted outcome
              predicted_outcome: bestMarket.predicted_outcome,
              // Use ADJUSTED confidence and EV (with form momentum and value zone applied)
              confidence: adjustedProbability,
              expected_value: adjustedEV,
              ev: adjustedEV,
              // Best market odds for display
              odds: bestMarketOdds,
              // Full provenance so the recorded price can be independently audited.
              odds_provenance: bestMarket.odds_provenance,
              // Keep 1X2 probabilities for backwards compatibility
              probabilities: predictionData,
              odds_data: oddsData,
              teams_data: teamsData,
              // "Best bet: …" told the reader to bet, and called the selection
              // best. It is the highest-ranked outcome in one market — which is
              // a statement about our ordering, not about what anyone should do.
              explanation: `Highest-ranked outcome: ${marketConfig.display_name} — ${bestMarket.predicted_outcome}`,

              // NEW: Multi-market data (with adjusted score)
              best_market: {
                type: bestMarket.market_type,
                name: marketConfig.name,
                display_name: marketConfig.display_name,
                predicted_outcome: bestMarket.predicted_outcome,
                probability: adjustedProbability, // Using adjusted
                probability_gap: bestMarket.probability_gap,
                odds: bestMarketOdds,
                expected_value: adjustedEV, // Using adjusted
                market_score: adjustedScore, // Using adjusted
                original_probability: bestMarket.probability,
                original_ev: bestMarketEV,
                // Audit trail for the published price (2026-07-29 defect fix).
                odds_provenance: bestMarket.odds_provenance
              },
              all_markets: allMarketsData.sort((a, b) => b.market_score - a.market_score).map(m => ({
                type: m.market_type,
                name: MARKET_CONFIG[m.market_type].name,
                predicted_outcome: m.predicted_outcome,
                probability: m.probability,
                odds: m.odds,
                expected_value: m.expected_value,
                market_score: m.market_score,
                is_recommended: marketResults.some(r => r.market_type === m.market_type)  // Flag if passes filters
              })),

              // NEW: Accuracy enhancement metadata
              enhancement_data: enhancementData,

              debug_info: {
                confidence_score: confidence,
                probability_gap: probabilityGap,
                variance: probabilityGap >= 0.20 ? 'Low' : probabilityGap >= 0.15 ? 'Medium' : 'High',
                market_type: bestMarket.market_type,
                markets_evaluated: marketResults.length,
                value_zone: valueZone.zone
              },
              revenue_vs_risk_score: 0,
              signal_quality: (() => {
                const score = bestMarket.market_score * 100
                if (score >= 50) return 'Strong'
                if (score >= 35) return 'Good'
                if (score >= 25) return 'Moderate'
                return 'Weak'
              })(),
              // Internal-only audit context. The public DTO does not expose
              // provider internals or restate eligibility as an endorsement.
              strategy_evaluation: strategyEvaluation,
            })
          }
        }
      } catch (error) {
        console.error(`Error fetching league ${league.name}: ${error}`)
      }
    }

    // Every row here has passed all Generation 3 gates. Rank the survivors by
    // provider-probability/payout balance, then use the provider report card
    // and price consensus as deterministic tie-breakers.
    allRecommendations.sort((a, b) =>
      compareGemStrategy(a.strategy_evaluation, b.strategy_evaluation))

    const qualifiedGemCount = allRecommendations.length
    let featuredGems = allRecommendations
      .slice(0, VALUE_STRATEGY_POLICY.maximumSelections)
      .map((rec, index) => ({ ...rec, is_recommended: true, gem_rank: index + 1 }))

    // --- ENRICHMENT: Fetch Standings for Form Data ---
    try {
      // 1. Get unique season IDs from the featured Gems
      const seasonIds = Array.from(new Set(featuredGems.map(rec => rec.season_id).filter(id => !!id)))

      if (seasonIds.length > 0) {
        console.error(`DEBUG: Enrichment Season IDs: ${seasonIds.join(', ')}`)

        // 2. Fetch standings for each season in parallel
        const standingsPromises = seasonIds.map(seasonId =>
          apiClient.request(`https://api.sportmonks.com/v3/football/standings/seasons/${seasonId}?api_token=${token}&include=form`)
            .then(res => {
              console.error(`DEBUG: Standings for ${seasonId}: Found ${res.data?.length || 0} entries`)
              if (res.data?.length > 0) {
                console.error(`DEBUG: Sample Form:`, JSON.stringify(res.data[0].form))
              }
              return { seasonId, data: res.data || [] }
            })
            .catch(err => {
              console.error(`ERROR: Failed to fetch standings for season ${seasonId}: ${err.message}`)
              return { seasonId, data: [] }
            })
        )

        const standingsResults = await Promise.all(standingsPromises)

        // 3. Create a map of TeamID -> Form String
        // Parsed through THE canonical parser. `standing.form` is an ARRAY of
        // one-letter results with sort_order — the previous code stored it
        // raw and a later JSON.stringify fed `[{"id` to the momentum function,
        // which found no W/D/L and returned a 1.0 multiplier every single time.
        // The heuristic was inert in production until this fix.
        const parsedForms = buildFormMap(standingsResults)
        const formMap = new Map<string, string>()
        parsedForms.forEach((parsed, participantId) => {
          if (parsed.available) formMap.set(String(participantId), parsed.letters)
        })
        console.log(`✅ Enrichment: parsed form for ${formMap.size} teams`)
        console.log(`✅ Enrichment: Found form data for ${formMap.size} teams`)

        // 3.5 Fallback: Fetch specific team form for Cup matches (where standings failed)
        const missingFormTeamIds = new Set<string>()
        featuredGems.forEach(rec => {
          if (!formMap.has(String(rec.home_id))) missingFormTeamIds.add(String(rec.home_id))
          if (!formMap.has(String(rec.away_id))) missingFormTeamIds.add(String(rec.away_id))
        })

        if (missingFormTeamIds.size > 0) {
          console.log(`⚠️ Enrichment: Fetching fallback form for ${missingFormTeamIds.size} teams (Cup/Non-League)`)
          // Limit to 10 concurrent requests to be safe with rate limits
          const idsToFetch = Array.from(missingFormTeamIds).slice(0, 10)

          const teamPromises = idsToFetch.map(id =>
            apiClient.request(`https://api.sportmonks.com/v3/football/teams/${id}?api_token=${token}&include=form`)
              .then(res => {
                // Determine form string from team response
                let form = '?????'
                if (res.data?.form) form = res.data.form
                else if (Array.isArray(res.data?.form)) form = res.data.form.map((f: any) => f.result || '?').join('')

                return { id: String(id), form }
              })
              .catch(err => {
                console.error(`Failed to fetch team form ${id}: ${err.message}`)
                return { id: String(id), form: null }
              })
          )

          const teamResults = await Promise.all(teamPromises)
          teamResults.forEach(res => {
            if (res.form && res.form !== '?????') {
              formMap.set(res.id, res.form)
            }
          })
        }

        // 4. Enrich recommendations
        featuredGems = featuredGems.map(rec => {
          const homeIdStr = String(rec.home_id)
          const awayIdStr = String(rec.away_id)

          const homeForm = formMap.get(homeIdStr) || null
          const awayForm = formMap.get(awayIdStr) || null

          // Handle existing form data (from initial logic or fallback fetch)
          // We must treat '?????' as "no data"
          const currentHomeForm = rec.teams_data?.home?.form
          const currentAwayForm = rec.teams_data?.away?.form

          // Logic: 
          // 1. Enrich (Standings/Direct Fetch) -> if valid string
          // 2. Initial -> if valid string (not '?????')
          // 3. Last resort -> '?????' 
          // Note: homeForm from map is already validated to be non-empty string in previous steps

          const finalHomeForm = homeForm || (currentHomeForm !== '?????' ? currentHomeForm : null) || '?????'
          const finalAwayForm = awayForm || (currentAwayForm !== '?????' ? currentAwayForm : null) || '?????'

          return {
            ...rec,
            teams_data: {
              home: { ...rec.teams_data?.home, form: finalHomeForm },
              away: { ...rec.teams_data?.away, form: finalAwayForm }
            }
          }
        })
      }
    } catch (enrichError) {
      console.error(`Form enrichment failed: ${enrichError}`)
      // Continue without enrichment
    }
    // ------------------------------------------------

    // This route is READ-ONLY. It computes recommendations and returns them.
    //
    // It used to fire a background POST to /api/log-recommendations/, which
    // meant a GET — including one from a browser hitting the homepage — wrote
    // PredictionLog rows and appended immutable snapshots as a side effect.
    // It also duplicated the scheduler's work: the scheduler GETs this route
    // and then ingests the returned payload itself, so every cycle produced
    // two prediction runs and two snapshot sets for the same calculation.
    //
    // The scheduler's in-process call to core.services.recommendation_ingest
    // is now the single canonical write path. Nothing a public request can
    // reach may create or update a prediction record.

    // The engine stops here. It expresses no opinion about who may see what —
    // that is the caller's decision, and there is no branch in this function
    // that could serve internal fields to a public request.
    return {
      ok: true,
      recommendations: featuredGems,
      envelope: {
        total: featuredGems.length,
        leagues_covered: keyLeagues.length,
        fixtures_analyzed: totalFixtures,
        fixtures_with_predictions: fixturesWithPredictions,
        gem_scan: {
          fixtures_scanned: totalFixtures,
          fixtures_with_predictions: fixturesWithPredictions,
          qualified_fixtures: qualifiedGemCount,
          displayed_gems: featuredGems.length,
          maximum_gems: VALUE_STRATEGY_POLICY.maximumSelections,
          gate_funnel: {
            fixtures_scanned: totalFixtures,
            prediction_ready: fixturesWithPredictions,
            signal_and_price_ready: strategyEvaluatedFixtures,
            strategy_qualified: qualifiedGemCount,
            displayed: featuredGems.length,
          },
          rejection_breakdown: publicGemRejectionBreakdown(
            fixturesWithPredictions - strategyEvaluatedFixtures,
            strategyRejectionCounts,
          ),
          rejection_counts_overlap: true,
        },
        lastUpdated: new Date().toISOString(),
        // WHICH ranking policy produced these. Ingest stamps it onto every
        // snapshot and therefore onto every published claim, so a record
        // accumulated across changes to the logic stays interpretable rather
        // than silently blending several different systems.
        ranking_version: RANKING_VERSION,
        message: 'Success',
      },
      confidenceThreshold: 55,
    }
  }
}

/**
 * PUBLIC endpoint. Always the allowlisted DTO.
 *
 * There is deliberately no authentication branch here. This handler cannot
 * return an internal field even if someone presents a valid secret — the raw
 * payload is only reachable through /api/internal/recommendations, which is a
 * different file with its own auth. A leak would require someone to edit this
 * function to call the wrong serializer, which is a visible change rather than
 * a subtle condition.
 */
