import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

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
const MARKET_CONFIG = {
  '1x2': {
    name: '1X2',
    display_name: 'Match Result',
    type_ids: [233, 237, 238],  // Multiple models for 1X2
    outcomes: ['home', 'draw', 'away'],
    odds_market_id: 1,
    min_gap: 0.12,  // 12% for home/away, 15% for draw (handled in code)
  },
  'btts': {
    name: 'BTTS',
    display_name: 'Both Teams to Score',
    type_ids: [231],
    outcomes: ['yes', 'no'],
    odds_market_id: 28,  // BTTS market
    min_gap: 0.12,
  },
  'over_under_2.5': {
    name: 'O/U 2.5',
    display_name: 'Over/Under 2.5 Goals',
    type_ids: [235],
    outcomes: ['yes', 'no'],  // yes = over, no = under
    odds_market_id: 18,  // Over/Under market
    min_gap: 0.12,
  },
  'double_chance': {
    name: 'DC',
    display_name: 'Double Chance',
    type_ids: [239],
    outcomes: ['draw_home', 'draw_away', 'home_away'],  // 1X, X2, 12
    odds_market_id: 12,  // Double Chance market
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
  odds: number
  expected_value: number
  market_score: number
  raw_predictions: Record<string, number>
}

// Calculate MarketScore = (probability_gap × 0.4) + (expected_value × 0.3) + (confidence × 0.3)
function calculateMarketScore(probabilityGap: number, expectedValue: number, confidence: number): number {
  // Normalize values to 0-1 scale
  const normalizedGap = Math.min(probabilityGap, 0.5) / 0.5  // Cap at 50% gap
  const normalizedEV = Math.min(Math.max(expectedValue, 0), 0.5) / 0.5  // Cap at 50% EV
  const normalizedConf = confidence  // Already 0-1

  return (normalizedGap * 0.4) + (normalizedEV * 0.3) + (normalizedConf * 0.3)
}

export async function GET(request: NextRequest) {
  try {
    console.log('🔍 Fetching real recommendations from SportMonks - no test data')

    // Only use real SportMonks data - no test data fallback
    const token = process.env.SPORTMONKS_API_TOKEN
    if (!token) {
      console.error('❌ SPORTMONKS_API_TOKEN not found in environment')
      return NextResponse.json({
        recommendations: [],
        total: 0,
        leagues_covered: 0,
        fixtures_analyzed: 0,
        fixtures_with_predictions: 0,
        lastUpdated: new Date().toISOString(),
        error: 'API configuration error - no real data available'
      }, { status: 500 })
    }

    // Calculate date range for next 14 days
    const now = new Date()
    const fourteenDaysFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000)
    const startDate = now.toISOString().split('T')[0]
    const endDate = fourteenDaysFromNow.toISOString().split('T')[0]

    // All 27 leagues covered by subscription
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
      { id: 283, name: 'Romanian SuperLiga' },
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

    // Limited loop for safety if needed, but processing keyLeagues logic remains
    for (const league of keyLeagues) {
      try {
        const url = `https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`
        const params = new URLSearchParams({
          api_token: token,
          include: 'participants;league;metadata;predictions;odds;odds.bookmaker',
          filters: `fixtureLeagues:${league.id}`,
          per_page: '50',
          page: '1',
          timezone: 'Europe/Bucharest'
        })

        const data = await apiClient.request(`${url}?${params}`)
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

              // Get odds for this market
              const x12Odds = fixture.odds.filter((odd: any) => odd.market_id === 1)
              let oddsValue = 1
              for (const odd of x12Odds) {
                if (odd.label?.toLowerCase() === outcome) oddsValue = parseFloat(odd.value) || 1
              }

              const ev = (maxProb * oddsValue) - 1
              const minGap = outcome === 'draw' ? 0.15 : 0.12

              const marketData: MarketPrediction = {
                market_type: '1x2',
                type_id: x12Predictions[0].type_id,
                predicted_outcome: outcome.charAt(0).toUpperCase() + outcome.slice(1),
                probability: maxProb,
                probability_gap: gap,
                odds: oddsValue,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
                raw_predictions: { home: avgHome, draw: avgDraw, away: avgAway }
              }

              // Always add to display array
              allMarketsData.push(marketData)

              // Only add to results if passes filters
              if (gap >= minGap && ev > 0) {
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

              // Get BTTS odds (market_id 28 or search by name)
              const bttsOdds = fixture.odds.filter((odd: any) =>
                odd.market_id === 28 || odd.name?.toLowerCase().includes('btts') || odd.name?.toLowerCase().includes('both')
              )
              let oddsValue = 1
              for (const odd of bttsOdds) {
                const label = odd.label?.toLowerCase()
                if ((outcome === 'yes' && label === 'yes') || (outcome === 'no' && label === 'no')) {
                  oddsValue = parseFloat(odd.value) || 1
                }
              }

              const ev = (maxProb * oddsValue) - 1

              const marketData: MarketPrediction = {
                market_type: 'btts',
                type_id: 231,
                predicted_outcome: outcome === 'yes' ? 'BTTS Yes' : 'BTTS No',
                probability: maxProb,
                probability_gap: gap,
                odds: oddsValue,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
                raw_predictions: { yes: yesProb, no: noProb }
              }

              allMarketsData.push(marketData)
              if (gap >= 0.12 && ev > 0) {
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

              // Get O/U 2.5 odds - be specific about the 2.5 threshold!
              // SportMonks market_id 18 is "Over/Under" but we need to match the specific 2.5 line
              const ouOdds = fixture.odds.filter((odd: any) => {
                // Must contain "2.5" in the name or label to be the right market
                const nameMatch = odd.name?.toLowerCase().includes('2.5') ||
                  odd.label?.toLowerCase().includes('2.5')
                // Alternatively, check market_id 18 with specific label containing over/under
                const marketMatch = odd.market_id === 18 &&
                  (odd.label?.toLowerCase().includes('over 2.5') ||
                    odd.label?.toLowerCase().includes('under 2.5'))
                return nameMatch || marketMatch
              })

              let oddsValue = 1
              for (const odd of ouOdds) {
                const label = odd.label?.toLowerCase() || ''
                const name = odd.name?.toLowerCase() || ''
                // Match specifically Over 2.5 or Under 2.5
                if (outcome === 'over' && (label.includes('over 2.5') || label === 'over' ||
                  (label.includes('over') && (name.includes('2.5') || label.includes('2.5'))))) {
                  oddsValue = parseFloat(odd.value) || 1
                  break  // Take the first match, don't iterate through all
                }
                if (outcome === 'under' && (label.includes('under 2.5') || label === 'under' ||
                  (label.includes('under') && (name.includes('2.5') || label.includes('2.5'))))) {
                  oddsValue = parseFloat(odd.value) || 1
                  break
                }
              }

              // Fallback: try to find any Over/Under with reasonable odds
              if (oddsValue === 1 && ouOdds.length > 0) {
                for (const odd of ouOdds) {
                  const label = odd.label?.toLowerCase() || ''
                  if (outcome === 'over' && label.includes('over')) {
                    const value = parseFloat(odd.value)
                    if (value > 1 && value < 10) {
                      oddsValue = value
                      break
                    }
                  }
                  if (outcome === 'under' && label.includes('under')) {
                    const value = parseFloat(odd.value)
                    if (value > 1 && value < 10) {
                      oddsValue = value
                      break
                    }
                  }
                }
              }

              const ev = (maxProb * oddsValue) - 1

              const marketData: MarketPrediction = {
                market_type: 'over_under_2.5',
                type_id: 235,
                predicted_outcome: outcome === 'over' ? 'Over 2.5' : 'Under 2.5',
                probability: maxProb,
                probability_gap: gap,
                odds: oddsValue,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
                raw_predictions: { over: overProb, under: underProb }
              }

              allMarketsData.push(marketData)
              if (gap >= 0.12 && ev > 0) {
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

              // Get DC odds (market_id 12)
              const dcOdds = fixture.odds.filter((odd: any) => odd.market_id === 12)
              let oddsValue = 1
              for (const odd of dcOdds) {
                const label = odd.label?.toLowerCase().replace(/\s/g, '')
                if (label === outcome.toLowerCase() || label === outcome.toLowerCase().split('').reverse().join('')) {
                  oddsValue = parseFloat(odd.value) || 1
                }
              }

              const ev = (maxProb * oddsValue) - 1

              const marketData: MarketPrediction = {
                market_type: 'double_chance',
                type_id: 239,
                predicted_outcome: outcome,
                probability: maxProb,
                probability_gap: gap,
                odds: oddsValue,
                expected_value: ev,
                market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
                raw_predictions: { '1X': homeOrDraw, 'X2': awayOrDraw, '12': homeOrAway }
              }

              allMarketsData.push(marketData)
              if (gap >= 0.10 && ev > 0) {
                marketResults.push(marketData)
              }
            }

            // ============= SELECT BEST MARKET =============
            // Sort by market_score descending and pick the best
            marketResults.sort((a, b) => b.market_score - a.market_score)
            const bestMarket = marketResults[0]

            // Skip if no valid market found
            if (!bestMarket || bestMarket.market_score < 0.15) {
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

            const confidence = bestMarket.probability * 100
            const probabilityGap = bestMarket.probability_gap

            // Use the best market's data for the recommendation
            const marketConfig = MARKET_CONFIG[bestMarket.market_type]

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
              confidence: bestMarket.probability,
              expected_value: bestMarket.expected_value,
              ev: bestMarket.expected_value,
              // Best market odds for display
              odds: bestMarket.odds,
              // Keep 1X2 probabilities for backwards compatibility
              probabilities: predictionData,
              odds_data: oddsData,
              teams_data: teamsData,
              explanation: `Best bet: ${marketConfig.display_name} - ${bestMarket.predicted_outcome}`,

              // NEW: Multi-market data
              best_market: {
                type: bestMarket.market_type,
                name: marketConfig.name,
                display_name: marketConfig.display_name,
                predicted_outcome: bestMarket.predicted_outcome,
                probability: bestMarket.probability,
                probability_gap: bestMarket.probability_gap,
                odds: bestMarket.odds,
                expected_value: bestMarket.expected_value,
                market_score: bestMarket.market_score
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

              debug_info: {
                confidence_score: confidence,
                probability_gap: probabilityGap,
                variance: probabilityGap >= 0.20 ? 'Low' : probabilityGap >= 0.15 ? 'Medium' : 'High',
                market_type: bestMarket.market_type,
                markets_evaluated: marketResults.length
              },
              revenue_vs_risk_score: 0, // Will be calculated
              signal_quality: (() => {
                const score = bestMarket.market_score * 100
                if (score >= 50) return 'Strong'
                if (score >= 35) return 'Good'
                if (score >= 25) return 'Moderate'
                return 'Weak'
              })()
            })
          }
        }
      } catch (error) {
        console.error(`Error fetching league ${league.name}: ${error}`)
      }
    }

    // Scoring
    const scoredRecommendations = allRecommendations.map(rec => {
      const revenueScore = rec.expected_value * (rec.confidence / 100)
      const riskScore = 1 - (rec.confidence / 100)
      const combinedScore = revenueScore - (riskScore * 0.8)
      // Quality bonuses
      const qualityBonus = rec.confidence >= 70 ? 0.5 : rec.confidence >= 65 ? 0.3 : 0
      return { ...rec, revenue_vs_risk_score: combinedScore + qualityBonus }
    })

    scoredRecommendations.sort((a, b) => b.revenue_vs_risk_score - a.revenue_vs_risk_score)

    let top10Recommendations = scoredRecommendations.slice(0, 10).map(rec => ({
      ...rec, is_recommended: true
    }))

    // --- ENRICHMENT: Fetch Standings for Form Data ---
    try {
      // 1. Get unique season IDs from the top 10
      const seasonIds = Array.from(new Set(top10Recommendations.map(rec => rec.season_id).filter(id => !!id)))

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
        const formMap = new Map<string, string>()

        standingsResults.forEach(result => {
          if (result.data.length > 0) {
            console.error(`DEBUG: First standing keys:`, Object.keys(result.data[0]))
            if (!result.data[0].participant_id) console.error(`WARNING: participant_id missing in standing!`)
          }
          result.data.forEach((standing: any) => {
            if (standing.participant_id && standing.form) {
              // Normalize ID to string to ensure matching works
              formMap.set(String(standing.participant_id), standing.form)
            }
          })
        })
        console.log(`✅ Enrichment: Found form data for ${formMap.size} teams`)

        // 3.5 Fallback: Fetch specific team form for Cup matches (where standings failed)
        const missingFormTeamIds = new Set<string>()
        top10Recommendations.forEach(rec => {
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
        top10Recommendations = top10Recommendations.map(rec => {
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

    // Log logic
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : 'https://smartbet-backend-production.up.railway.app')
    fetch(`${djangoBaseUrl}/api/log-recommendations/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recommendations: top10Recommendations }),
    }).catch(() => { })

    return NextResponse.json({
      recommendations: top10Recommendations,
      total: top10Recommendations.length,
      leagues_covered: keyLeagues.length,
      fixtures_analyzed: totalFixtures,
      fixtures_with_predictions: fixturesWithPredictions,
      confidence_threshold: 55,
      lastUpdated: new Date().toISOString(),
      message: 'Success'
    })

  } catch (error) {
    console.error('Error in recommendations API:', error)
    return NextResponse.json({ error: 'Failed' }, { status: 500 })
  }
}
