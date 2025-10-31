import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// Simplified inline apiClient implementation
const apiClient = {
  async request(url: string) {
    const response = await fetch(url)
    return response.json()
  }
}

// Helper function to get API token (will be called at request time, not build time)
function getApiToken(): string {
  const token = process.env.SPORTMONKS_API_TOKEN
  if (!token) {
    throw new Error('SPORTMONKS_API_TOKEN environment variable is not set')
  }
  return token
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fixtureId = params.id

    if (!fixtureId) {
      return NextResponse.json(
        { error: 'Fixture ID is required' },
        { status: 400 }
      )
    }

    console.log(`🔍 Fetching real fixture ${fixtureId} from SportMonks`)

    // Fetch fixture from SportMonks
    const url = `https://api.sportmonks.com/v3/football/fixtures/${fixtureId}`
    const params_api = new URLSearchParams({
      api_token: getApiToken(),
      include: 'participants;league;metadata;predictions;odds;odds.bookmaker',
      timezone: 'Europe/Bucharest'
    })

    const data = await apiClient.request(`${url}?${params_api}`)
    const fixture = data.data

    if (!fixture) {
      return NextResponse.json(
        { error: 'Fixture not found' },
        { status: 404 }
      )
    }

    // Extract fixture data
    const homeTeam = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name || 'Home'
    const awayTeam = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name || 'Away'
    
    // Extract predictions if available
    const predictions = fixture.predictions || []
    const x12Predictions = predictions.filter((p: any) => [233, 237, 238].includes(p.type_id))
    
    let predictionData = null
    if (x12Predictions.length > 0) {
      const bestPred = x12Predictions[0] // Use first prediction
      
      // Smart conversion: if values are > 1, they're percentages and need division by 100
      // If values are <= 1, they're already decimals
      const normalizeProbability = (value: number) => {
        if (!value || value <= 0) return 0
        if (value > 1) return value / 100  // Convert percentage to decimal
        return value  // Already a decimal
      }
      
      predictionData = {
        home: normalizeProbability(bestPred.predictions.home || 0),
        draw: normalizeProbability(bestPred.predictions.draw || 0),
        away: normalizeProbability(bestPred.predictions.away || 0)
      }
    }

    // Extract odds if available
    let oddsData = null
    if (fixture.odds && fixture.odds.length > 0) {
      const x12Odds = fixture.odds.filter((odd: any) => odd.market_id === 1)
      if (x12Odds.length > 0) {
        // Get bookmaker name from the first odds entry
        const firstOdd = x12Odds[0]
        let bookmakerName = 'Unknown'
        
        // Try multiple possible field names for bookmaker
        if (firstOdd.bookmaker_name) {
          bookmakerName = firstOdd.bookmaker_name
        } else if (firstOdd.bookmaker) {
          bookmakerName = firstOdd.bookmaker
        } else if (firstOdd.provider) {
          bookmakerName = firstOdd.provider
        } else if (firstOdd.source) {
          bookmakerName = firstOdd.source
        } else if (firstOdd.bookmaker_id) {
          // Try to get bookmaker name from metadata if available
          const bookmakerMeta = data.meta?.bookmakers?.find((bm: any) => bm.id === firstOdd.bookmaker_id)
          if (bookmakerMeta) {
            bookmakerName = bookmakerMeta.name
          }
        }
        
        // Helper function to get bookmaker name from odds entry
        const getBookmakerName = (odd: any) => {
          // First try to get bookmaker from the odds.bookmaker include
          if (odd.bookmaker && odd.bookmaker.name) {
            return odd.bookmaker.name
          }
          
          // Try to get bookmaker name from odds entry directly
          if (odd.bookmaker_name) return odd.bookmaker_name
          if (odd.provider) return odd.provider
          if (odd.source) return odd.source
          
          // Try to get bookmaker from metadata using bookmaker_id
          if (odd.bookmaker_id) {
            const bookmakerMeta = data.meta?.bookmakers?.find((bm: any) => bm.id === odd.bookmaker_id)
            if (bookmakerMeta) return bookmakerMeta.name
          }
          
          // Fallback: use a common bookmaker name based on ID patterns
          const bookmakerMap: { [key: number]: string } = {
            1: 'Bet365',
            2: 'Betfair', 
            14: 'William Hill',
            16: 'Paddy Power',
            26: 'Ladbrokes',
            29: 'Coral',
            32: 'Sky Bet',
            35: 'Unibet',
            38: 'Betway',
            64: '888Sport'
          }
          
          if (odd.bookmaker_id && bookmakerMap[odd.bookmaker_id]) {
            return bookmakerMap[odd.bookmaker_id]
          }
          
          // Final fallback
          return `Bookmaker ${odd.bookmaker_id || 'Unknown'}`
        }
        
        // Extract odds with individual bookmaker names
        const odds: {
          home: number | null
          draw: number | null
          away: number | null
          home_bookmaker: string | null
          draw_bookmaker: string | null
          away_bookmaker: string | null
        } = {
          home: null,
          draw: null,
          away: null,
          home_bookmaker: null,
          draw_bookmaker: null,
          away_bookmaker: null
        }
        
        // Process each odds entry and assign to the correct outcome
        for (const odd of x12Odds) {
          const bookmakerName = getBookmakerName(odd)
          const oddValue = parseFloat(odd.value)
          
          if (odd.label.toLowerCase() === 'home') {
            odds.home = oddValue
            odds.home_bookmaker = bookmakerName
          } else if (odd.label.toLowerCase() === 'draw') {
            odds.draw = oddValue
            odds.draw_bookmaker = bookmakerName
          } else if (odd.label.toLowerCase() === 'away') {
            odds.away = oddValue
            odds.away_bookmaker = bookmakerName
          }
        }
        
        // Determine the primary bookmaker (most common or first available)
        const bookmakers = [odds.home_bookmaker, odds.draw_bookmaker, odds.away_bookmaker].filter(Boolean)
        const primaryBookmaker = bookmakers.length > 0 ? bookmakers[0] : 'Multiple Bookmakers'
        
        // Create odds data with bookmaker information
        oddsData = {
          home: odds.home,
          draw: odds.draw,
          away: odds.away,
          bookmaker: primaryBookmaker,
          home_bookmaker: odds.home_bookmaker,
          draw_bookmaker: odds.draw_bookmaker,
          away_bookmaker: odds.away_bookmaker
        }
      }
    }

    // Calculate additional metrics like in recommendations API
    let predictedOutcome: 'home' | 'draw' | 'away' = 'home'
    let confidence = 0
    let expectedValue = 0
    let signalQuality: 'Strong' | 'Good' | 'Moderate' | 'Weak' = 'Weak'
    
    if (predictionData) {
      // Determine predicted outcome
      const probs = [predictionData.home, predictionData.draw, predictionData.away]
      const maxProb = Math.max(...probs)
      const maxIndex = probs.indexOf(maxProb)
      predictedOutcome = ['home', 'draw', 'away'][maxIndex] as 'home' | 'draw' | 'away'
      confidence = maxProb * 100
      
      // Calculate expected value for the predicted outcome
      if (oddsData) {
        const odds = predictedOutcome === 'home' ? oddsData.home :
                     predictedOutcome === 'draw' ? oddsData.draw : oddsData.away
        if (odds && maxProb > 0) {
          // EV = (Probability × Odds) - 1, then convert to percentage
          const rawEV = (maxProb * odds) - 1
          expectedValue = rawEV * 100
          
          // Safety check: cap unrealistic EV values
          if (expectedValue > 1000) {
            console.warn('Unrealistic EV detected:', { maxProb, odds, expectedValue })
            expectedValue = Math.min(expectedValue, 100) // Cap at 100%
          }
        }
      }
      
      // Determine signal quality
      if (confidence >= 70) signalQuality = 'Strong'
      else if (confidence >= 60) signalQuality = 'Good'
      else if (confidence >= 50) signalQuality = 'Moderate'
      else signalQuality = 'Weak'
    }

    // Prepare response data with rich structure like recommendations API
    const responseData = {
      fixture: {
        fixture_id: fixture.id,
        home_team: homeTeam,
        away_team: awayTeam,
        league: fixture.league?.name || 'Unknown',
        kickoff: fixture.starting_at,
        predicted_outcome: predictedOutcome,
        confidence: confidence,
        probabilities: predictionData || { home: 0, draw: 0, away: 0 },
        odds_data: oddsData,
        expected_value: expectedValue,
        signal_quality: signalQuality,
        ensemble_info: {
          prediction_consensus: confidence / 100,
          strategy: confidence >= 70 ? 'conservative' : confidence >= 50 ? 'balanced' : 'aggressive',
          consensus: confidence / 100,
          variance: confidence >= 70 ? 0.1 : confidence >= 50 ? 0.2 : 0.3
        },
        debug_info: {
          consensus: confidence > 70 ? 'High' : confidence > 50 ? 'Medium' : 'Low',
          variance: confidence > 70 ? 'Low' : confidence > 50 ? 'Medium' : 'High',
          confidence_score: confidence,
          prediction_agreement: confidence > 70 ? 'High Agreement' : confidence > 50 ? 'Medium Agreement' : 'Low Agreement',
          model_consensus: {
            home: predictionData?.home || 0,
            draw: predictionData?.draw || 0,
            away: predictionData?.away || 0,
            variance: confidence >= 70 ? 0.1 : confidence >= 50 ? 0.2 : 0.3
          }
        },
        has_predictions: x12Predictions.length > 0,
        has_odds: fixture.odds && fixture.odds.length > 0
      },
      lastUpdated: new Date().toISOString()
    }

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('Error fetching fixture:', error)
    return NextResponse.json(
      { error: 'Failed to fetch fixture analysis' },
      { status: 500 }
    )
  }
}