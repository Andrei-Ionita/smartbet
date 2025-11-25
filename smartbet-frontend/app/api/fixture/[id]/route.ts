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
      
      console.log('🔍 Raw prediction data:', JSON.stringify(bestPred.predictions, null, 2))
      
      // Smart conversion: if values are > 1, they're percentages and need division by 100
      // If values are <= 1, they're already decimals
      const normalizeProbability = (value: number) => {
        if (!value || value <= 0) return 0
        if (value > 1) return value / 100  // Convert percentage to decimal
        return value  // Already a decimal
      }
      
      predictionData = {
        home: normalizeProbability(bestPred.predictions.home || 0) * 100, // Convert to percentage for consistency
        draw: normalizeProbability(bestPred.predictions.draw || 0) * 100,
        away: normalizeProbability(bestPred.predictions.away || 0) * 100
      }

      console.log('📊 Normalized prediction data (as percentages):', predictionData)

      // Validate that probabilities sum to approximately 100%
      const total = predictionData.home + predictionData.draw + predictionData.away
      const tolerance = 5 // Allow 5% deviation

      if (Math.abs(total - 100) > tolerance) {
        console.warn(`⚠️ Fixture ${fixture.id}: Probabilities don't sum to 100%`, {
          home: predictionData.home.toFixed(2),
          draw: predictionData.draw.toFixed(2),
          away: predictionData.away.toFixed(2),
          total: total.toFixed(2),
          deviation: (total - 100).toFixed(2)
        })

        // Normalize probabilities to sum to exactly 100%
        const factor = 100 / total
        predictionData.home *= factor
        predictionData.draw *= factor
        predictionData.away *= factor

        const newTotal = predictionData.home + predictionData.draw + predictionData.away
        console.log('✅ Normalized to sum to 100%:', {
          home: predictionData.home.toFixed(2),
          draw: predictionData.draw.toFixed(2),
          away: predictionData.away.toFixed(2),
          total: newTotal.toFixed(2)
        })
      } else {
        console.log(`✅ Probabilities sum correctly: ${total.toFixed(2)}%`)
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

        // Validate odds are in reasonable range (1.01 to 1000)
        const validateOdds = (odds: number | null, label: string): boolean => {
          if (!odds) return false
          if (odds < 1.01 || odds > 1000) {
            console.warn(`⚠️ Fixture ${fixture.id}: Suspicious ${label} odds: ${odds}`)
            return false
          }
          return true
        }

        const validHome = validateOdds(oddsData.home, 'home')
        const validDraw = validateOdds(oddsData.draw, 'draw')
        const validAway = validateOdds(oddsData.away, 'away')

        if (!validHome && !validDraw && !validAway) {
          console.warn(`⚠️ Fixture ${fixture.id}: All odds are invalid - discarding odds data`)
          oddsData = null
        } else {
          console.log(`✅ Odds validation passed: Home=${validHome}, Draw=${validDraw}, Away=${validAway}`)
        }
      }
    }

    // Calculate additional metrics like in recommendations API
    let predictedOutcome: 'home' | 'draw' | 'away' = 'home'
    let confidence = 0
    let evAnalysis = {
      home: null as number | null,
      draw: null as number | null,
      away: null as number | null,
      best_bet: null as 'home' | 'draw' | 'away' | null,
      best_ev: null as number | null
    }
    let signalQuality: 'Strong' | 'Good' | 'Moderate' | 'Weak' = 'Weak'
    
    if (predictionData) {
      // Determine predicted outcome (predictionData is now in percentage format)
      const probs = [predictionData.home, predictionData.draw, predictionData.away]
      const maxProb = Math.max(...probs)
      const maxIndex = probs.indexOf(maxProb)
      predictedOutcome = ['home', 'draw', 'away'][maxIndex] as 'home' | 'draw' | 'away'
      confidence = maxProb // Already a percentage
      
      // Calculate expected value for all outcomes
      if (oddsData) {
        console.log('💰 Calculating EV with odds:', oddsData)
        console.log('📊 Using probabilities (as percentages):', predictionData)

        // Calculate EV for home (convert percentage to decimal for calculation)
        if (oddsData.home && predictionData.home > 0) {
          const probDecimal = predictionData.home / 100
          const rawEV = (probDecimal * oddsData.home) - 1
          evAnalysis.home = rawEV * 100
          console.log(`🏠 Home EV: prob=${probDecimal}, odds=${oddsData.home}, rawEV=${rawEV}, EV%=${evAnalysis.home}`)
        }

        // Calculate EV for draw
        if (oddsData.draw && predictionData.draw > 0) {
          const probDecimal = predictionData.draw / 100
          const rawEV = (probDecimal * oddsData.draw) - 1
          evAnalysis.draw = rawEV * 100
          console.log(`🤝 Draw EV: prob=${probDecimal}, odds=${oddsData.draw}, rawEV=${rawEV}, EV%=${evAnalysis.draw}`)
        }

        // Calculate EV for away
        if (oddsData.away && predictionData.away > 0) {
          const probDecimal = predictionData.away / 100
          const rawEV = (probDecimal * oddsData.away) - 1
          evAnalysis.away = rawEV * 100
          console.log(`✈️ Away EV: prob=${probDecimal}, odds=${oddsData.away}, rawEV=${rawEV}, EV%=${evAnalysis.away}`)
        }
        
        // Determine best bet (highest EV)
        const evValues = [
          { outcome: 'home' as const, ev: evAnalysis.home },
          { outcome: 'draw' as const, ev: evAnalysis.draw },
          { outcome: 'away' as const, ev: evAnalysis.away }
        ]
        
        const validEvs = evValues.filter(v => v.ev !== null && v.ev > 0)
        if (validEvs.length > 0) {
          const bestBet = validEvs.reduce((max, current) => 
            (current.ev! > max.ev!) ? current : max
          )
          evAnalysis.best_bet = bestBet.outcome
          evAnalysis.best_ev = bestBet.ev
          
          console.log('🎯 Best bet:', bestBet)
          
          // Safety check: cap unrealistic EV values
          if (evAnalysis.best_ev && evAnalysis.best_ev > 100) {
            console.warn('⚠️ Unrealistic EV detected - capping:', {
              original: evAnalysis.best_ev,
              predictionData,
              oddsData,
              evAnalysis
            })
            evAnalysis.best_ev = Math.min(evAnalysis.best_ev, 50)
            // Also cap individual EVs
            if (evAnalysis.home && evAnalysis.home > 100) evAnalysis.home = Math.min(evAnalysis.home, 50)
            if (evAnalysis.draw && evAnalysis.draw > 100) evAnalysis.draw = Math.min(evAnalysis.draw, 50)
            if (evAnalysis.away && evAnalysis.away > 100) evAnalysis.away = Math.min(evAnalysis.away, 50)
          }
        }
        
        console.log('📈 Final EV Analysis:', evAnalysis)
      }
      
      // Determine signal quality
      if (confidence >= 70) signalQuality = 'Strong'
      else if (confidence >= 60) signalQuality = 'Good'
      else if (confidence >= 50) signalQuality = 'Moderate'
      else signalQuality = 'Weak'
    }

    // Calculate market indicators
    let marketIndicators = null
    if (predictionData && oddsData) {
      const impliedProbs = {
        home: oddsData.home ? (100 / oddsData.home) : 0,
        draw: oddsData.draw ? (100 / oddsData.draw) : 0,
        away: oddsData.away ? (100 / oddsData.away) : 0
      }
      const totalImplied = impliedProbs.home + impliedProbs.draw + impliedProbs.away
      const bookmakerMargin = totalImplied - 100

      // Determine favorite based on odds
      const favorites = [
        { outcome: 'Home', odds: oddsData.home, implied: impliedProbs.home },
        { outcome: 'Draw', odds: oddsData.draw, implied: impliedProbs.draw },
        { outcome: 'Away', odds: oddsData.away, implied: impliedProbs.away }
      ].sort((a, b) => (b.implied || 0) - (a.implied || 0))

      const marketFavorite = favorites[0].outcome.toLowerCase()

      // Compare AI prediction vs market
      const aiVsMarket = predictedOutcome === marketFavorite ?
        'Agreement' : 'Disagreement'

      // Estimate volume based on odds tightness (lower margin = higher volume)
      const volumeEstimate = bookmakerMargin < 5 ? 'High' :
                            bookmakerMargin < 8 ? 'Medium' : 'Low'

      marketIndicators = {
        market_favorite: favorites[0].outcome,
        market_implied_prob: favorites[0].implied?.toFixed(1) + '%',
        bookmaker_margin: bookmakerMargin.toFixed(2) + '%',
        volume_estimate: volumeEstimate,
        ai_vs_market: aiVsMarket,
        value_opportunity: aiVsMarket === 'Disagreement' ? 'Potential arbitrage' : 'Market aligned',
        odds_efficiency: bookmakerMargin < 5 ? 'Efficient' : 'Less efficient'
      }

      console.log('📊 Market Indicators:', marketIndicators)
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
        prediction_confidence: confidence,
        predictions: predictionData || { home: 0, draw: 0, away: 0 },
        odds_data: oddsData,
        ev_analysis: evAnalysis,
        signal_quality: signalQuality,
        prediction_strength: signalQuality,
        market_indicators: marketIndicators,
        prediction_info: {
          source: 'SportMonks AI',
          confidence_level: confidence >= 70 ? 'High' : confidence >= 60 ? 'Good' : confidence >= 50 ? 'Moderate' : 'Low',
          reliability_score: confidence / 100,
          data_quality: (predictionData && oddsData) ? 'Complete' : predictionData ? 'Predictions Only' : 'Limited',
          // Confidence intervals - wider for lower confidence predictions
          confidence_interval: {
            point_estimate: confidence,
            lower_bound: Math.max(0, confidence - (confidence >= 70 ? 5 : confidence >= 60 ? 7 : 10)),
            upper_bound: Math.min(100, confidence + (confidence >= 70 ? 5 : confidence >= 60 ? 7 : 10)),
            interval_width: confidence >= 70 ? 10 : confidence >= 60 ? 14 : 20,
            interpretation: confidence >= 70 ? 'Narrow interval indicates high certainty' :
                           confidence >= 60 ? 'Moderate interval indicates good confidence' :
                           'Wide interval reflects higher uncertainty'
          }
        },
        // Keep ensemble_info for backwards compatibility with existing code
        ensemble_info: {
          model_count: 1,
          consensus: confidence / 100,
          variance: confidence >= 70 ? 0.1 : confidence >= 50 ? 0.2 : 0.3,
          strategy: confidence >= 70 ? 'conservative' : confidence >= 50 ? 'balanced' : 'aggressive'
        },
        debug_info: {
          confidence_category: confidence > 70 ? 'High' : confidence > 50 ? 'Medium' : 'Low',
          prediction_strength: confidence > 70 ? 'Strong' : confidence > 50 ? 'Moderate' : 'Weak',
          confidence_score: confidence,
          certainty_level: confidence > 70 ? 'High Certainty' : confidence > 50 ? 'Moderate Certainty' : 'Low Certainty',
          probabilities_decimal: {
            home: (predictionData?.home || 0) / 100, // Convert percentage to decimal
            draw: (predictionData?.draw || 0) / 100,
            away: (predictionData?.away || 0) / 100
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