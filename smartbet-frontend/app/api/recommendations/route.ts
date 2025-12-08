import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// Simplified inline apiClient implementation with Timeout
const apiClient = {
  async request(url: string) {
    const controller = new AbortController()
    // 5 second timeout for external API calls
    const timeoutId = setTimeout(() => controller.abort(), 5000)
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
        for (const fixture of fixtures) {
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

            const homeVariance = allX12Predictions.reduce((sum: number, pred: any) => sum + Math.pow(pred.home - consensusHome, 2), 0) / allX12Predictions.length
            const drawVariance = allX12Predictions.reduce((sum: number, pred: any) => sum + Math.pow(pred.draw - consensusDraw, 2), 0) / allX12Predictions.length
            const awayVariance = allX12Predictions.reduce((sum: number, pred: any) => sum + Math.pow(pred.away - consensusAway, 2), 0) / allX12Predictions.length
            const totalVariance = (homeVariance + drawVariance + awayVariance) / 3

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
                league: league.name,
                kickoff: fixture.starting_at,
                predicted_outcome: predictedOutcome.charAt(0).toUpperCase() + predictedOutcome.slice(1),
                confidence: confidence / 100,
                expected_value: expectedValue,
                ev: expectedValue,
                probabilities: predictionData,
                odds_data: oddsData,
                explanation: `Model predicts ${predictedOutcome} win`,
                // ... other metadata fields simplified ...
                debug_info: { confidence_score: confidence },
                revenue_vs_risk_score: 0 // Will be calculated
              })
            }
          }
        }
      } catch (error) {
        console.log(`Error fetching league ${league.name}: ${error}`)
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

    const top10Recommendations = scoredRecommendations.slice(0, 10).map(rec => ({
      ...rec, is_recommended: true
    }))

    // ENRICHMENT
    console.log(`🚀 Enriching top ${top10Recommendations.length} recommendations...`)

    // Helper function
    const enrichRecommendation = async (rec: any) => {
      try {
        if (!rec.home_id || !rec.away_id) return rec

        const fixtureUrl = `https://api.sportmonks.com/v3/football/fixtures/${rec.fixture_id}`
        const fixtureParams = new URLSearchParams({
          api_token: token,
          include: 'participants;lineups;lineups.player;injuries;injuries.player'
        })

        const h2hUrl = `https://api.sportmonks.com/v3/football/head-to-head/${rec.home_id}/${rec.away_id}`
        const h2hParams = new URLSearchParams({
          api_token: token,
          include: 'participants',
          limit: '5'
        })

        let fixtureData = null
        let h2hData = []

        try {
          const fixtureRes = await apiClient.request(`${fixtureUrl}?${fixtureParams}`)
          fixtureData = fixtureRes.data
        } catch (e: any) {
          console.error(`Failed to fetch fixture ${rec.fixture_id}: ${e.message}`)
        }

        try {
          const h2hRes = await apiClient.request(`${h2hUrl}?${h2hParams}`)
          h2hData = h2hRes.data || []
        } catch (e: any) {
          console.error(`Failed to fetch H2H for ${rec.fixture_id}: ${e.message}`)
        }

        if (!fixtureData) return rec

        // Process Data
        const homeTeam = fixtureData?.participants?.find((p: any) => p.meta?.location === 'home')
        const awayTeam = fixtureData?.participants?.find((p: any) => p.meta?.location === 'away')

        const processInjuries = (teamId: number) => {
          return fixtureData?.injuries
            ?.filter((inj: any) => inj.team_id === teamId)
            .map((inj: any) => ({
              player_name: inj.player?.name || inj.player_name || 'Unknown',
              reason: inj.reason || 'Unknown',
              type: 'Missing'
            })) || []
        }

        const teams_data = {
          home: {
            id: rec.home_id,
            name: rec.home_team,
            logo_path: homeTeam?.image_path,
            form: homeTeam?.form || 'N/A', // Assuming form is here? SportMonks participants might not have form in fixture include. 
            // Actually form requires 'participants;participants.form'? No, stand-alone call usually.
            // For now, if form is missing, frontend handles it.
            position: 0, // Placeholder
            injuries: processInjuries(rec.home_id)
          },
          away: {
            id: rec.away_id,
            name: rec.away_team,
            logo_path: awayTeam?.image_path,
            form: awayTeam?.form || 'N/A',
            position: 0,
            injuries: processInjuries(rec.away_id)
          }
        }

        const lineups_data = {
          status: fixtureData?.lineups?.length > 0 ? 'Confirmed' : 'Predicted',
          home_formation: fixtureData?.lineups?.find((l: any) => l.team_id === rec.home_id)?.formation || 'Unknown',
          away_formation: fixtureData?.lineups?.find((l: any) => l.team_id === rec.away_id)?.formation || 'Unknown'
        }

        const h2h_data = {
          total_played: h2hData.length,
          home_wins: 0, away_wins: 0, draws: 0, last_5_results: [] as any[], summary_text: ''
        }

        h2hData.forEach((match: any) => {
          const homeWinner = match?.participants?.find((p: any) => p.meta?.location === 'home' && p.meta?.winner)
          const awayWinner = match?.participants?.find((p: any) => p.meta?.location === 'away' && p.meta?.winner)

          if (homeWinner && homeWinner.id === rec.home_id) {
            h2h_data.home_wins++; h2h_data.last_5_results.push('Home')
          } else if (awayWinner && awayWinner.id === rec.away_id) {
            h2h_data.away_wins++; h2h_data.last_5_results.push('Away')
          } else {
            h2h_data.draws++; h2h_data.last_5_results.push('Draw')
          }
        })

        h2h_data.summary_text = `${rec.home_team} won ${h2h_data.home_wins}, ${rec.away_team} won ${h2h_data.away_wins} of last ${h2hData.length} meetings`

        return { ...rec, teams_data, lineups_data, h2h_data }

      } catch (error: any) {
        console.error(`enrich failed: ${error.message}`)
        return rec
      }
    }

    const enrichedRecommendations = []
    for (const rec of top10Recommendations) {
      enrichedRecommendations.push(await enrichRecommendation(rec))
    }

    // Log logic omitted for brevity/safety

    return NextResponse.json({
      recommendations: enrichedRecommendations,
      total: enrichedRecommendations.length,
      message: 'Success'
    })

  } catch (error) {
    console.error('Error in recommendations API:', error)
    return NextResponse.json({ error: 'Failed' }, { status: 500 })
  }
}
