import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// Simplified inline apiClient implementation with Timeout
const apiClient = {
  async request(url: string) {
    const controller = new AbortController()
    // 10 second timeout for external API calls to avoid AbortError on slow responses
    const timeoutId = setTimeout(() => controller.abort(), 10000)
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
          const x12Predictions = predictions.filter((p: any) => [233, 237, 238].includes(p.type_id))

          if (x12Predictions.length > 0 && fixture.odds && fixture.odds.length > 0) {
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

            // Analyze all X12 predictions
            const allX12Predictions = x12Predictions.map((pred: any) => ({
              type_id: pred.type_id,
              predictions: pred.predictions,
              home: normalizeProbability(pred.predictions.home || 0),
              draw: normalizeProbability(pred.predictions.draw || 0),
              away: normalizeProbability(pred.predictions.away || 0)
            }))

            const consensusHome = allX12Predictions.reduce((sum: number, pred: any) => sum + pred.home, 0) / allX12Predictions.length
            const consensusDraw = allX12Predictions.reduce((sum: number, pred: any) => sum + pred.draw, 0) / allX12Predictions.length
            const consensusAway = allX12Predictions.reduce((sum: number, pred: any) => sum + pred.away, 0) / allX12Predictions.length

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

            const confidence = maxProb * 100
            const oddsValue = oddsData?.[predictedOutcome] || 1
            const expectedValue = (maxProb * oddsValue) - 1

            if (expectedValue > 0 && confidence >= 55 && expectedValue >= 0.10) {
              allRecommendations.push({
                fixture_id: fixture.id,
                home_team: homeTeam,
                away_team: awayTeam,
                home_id: homeId,
                away_id: awayId,
                season_id: fixture.season_id,
                league: league.name,
                kickoff: fixture.starting_at,
                predicted_outcome: predictedOutcome.charAt(0).toUpperCase() + predictedOutcome.slice(1),
                confidence: confidence / 100,
                expected_value: expectedValue,
                ev: expectedValue,
                probabilities: predictionData,
                odds_data: oddsData,
                explanation: `Model predicts ${predictedOutcome} win`,
                debug_info: { confidence_score: confidence },
                revenue_vs_risk_score: 0, // Will be calculated
                // Adjusted Signal Quality Logic: Retained as it is purely computational, not data-dependent
                signal_quality: (() => {
                  const probs = [predictionData.home, predictionData.draw, predictionData.away].sort((a, b) => b - a)
                  const gap = (probs[0] - probs[1]) * 100

                  // Strong: >65% confidence OR (>55% and >10% gap)
                  if (confidence >= 65 || (confidence >= 55 && gap >= 10)) return 'Strong'
                  // Good: >55% conf OR (>45% and >5% gap)
                  if (confidence >= 55 || (confidence >= 45 && gap >= 5)) return 'Good'
                  // Moderate: >45% conf
                  if (confidence >= 45) return 'Moderate'
                  return 'Weak'
                })()
              })
            }
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
        console.log(`Examples of Season IDs: ${seasonIds.join(', ')}`)

        // 2. Fetch standings for each season in parallel
        const standingsPromises = seasonIds.map(seasonId =>
          apiClient.request(`https://api.sportmonks.com/v3/football/standings/seasons/${seasonId}?api_token=${token}&include=form`)
            .then(res => ({ seasonId, data: res.data || [] }))
            .catch(err => {
              console.error(`Failed to fetch standings for season ${seasonId}: ${err.message}`)
              return { seasonId, data: [] }
            })
        )

        const standingsResults = await Promise.all(standingsPromises)

        // 3. Create a map of TeamID -> Form String
        const formMap = new Map<number, string>()

        standingsResults.forEach(result => {
          result.data.forEach((standing: any) => {
            if (standing.participant_id && standing.form) {
              formMap.set(standing.participant_id, standing.form)
            }
          })
        })

        // 4. Enrich recommendations
        top10Recommendations = top10Recommendations.map(rec => {
          const homeForm = formMap.get(rec.home_id) || null
          const awayForm = formMap.get(rec.away_id) || null

          if (homeForm || awayForm) {
            return {
              ...rec,
              teams_data: {
                home: { form: homeForm, ...rec.teams_data?.home },
                away: { form: awayForm, ...rec.teams_data?.away }
              }
            }
          }
          return rec
        })
      }
    } catch (enrichError) {
      console.error(`Form enrichment failed: ${enrichError}`)
      // Continue without enrichment
    }
    // ------------------------------------------------

    // Log logic
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://smartbet-backend-production.up.railway.app'
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
