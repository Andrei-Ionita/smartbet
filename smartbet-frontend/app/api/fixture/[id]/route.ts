import { NextRequest, NextResponse } from 'next/server'
import { apiClient } from '@/lib/api-client'

// Cache configuration
const CACHE_DURATION = {
  FIXTURE_DETAILS: 15 * 60 * 1000, // 15 minutes - fixture details don't change often
  PREDICTIONS: 30 * 60 * 1000,     // 30 minutes - predictions update less frequently  
  ODDS: 5 * 60 * 1000              // 5 minutes - odds change frequently
}

// In-memory cache store
const cache = new Map<string, { data: any; timestamp: number; duration: number }>()

// Cache utility functions
function getCacheKey(endpoint: string, params: Record<string, any> = {}): string {
  const sortedParams = Object.keys(params).sort().reduce((result, key) => {
    result[key] = params[key]
    return result
  }, {} as Record<string, any>)
  return `${endpoint}:${JSON.stringify(sortedParams)}`
}

function getFromCache(key: string): any | null {
  const cached = cache.get(key)
  if (!cached) return null
  
  const now = Date.now()
  if (now - cached.timestamp > cached.duration) {
    cache.delete(key)
    return null
  }
  
  return cached.data
}

function setCache(key: string, data: any, duration: number): void {
  cache.set(key, {
    data,
    timestamp: Date.now(),
    duration
  })
}

const SPORTMONKS_API_TOKEN = process.env.SPORTMONKS_API_TOKEN
if (!SPORTMONKS_API_TOKEN) {
  throw new Error('SPORTMONKS_API_TOKEN environment variable is not set')
}

interface SportMonksFixture {
  id: number
  name: string
  starting_at: string
  participants: Array<{ 
    name: string
    meta?: {
      location?: 'home' | 'away'
      winner?: boolean | null
      position?: number | null
    }
  }>
  predictions: Array<{
    type_id: number
    predictions: {
      home?: number
      draw?: number
      away?: number
      scores?: Record<string, number>
    }
  }>
  odds?: Array<{
    market_id: number
    bookmaker_id: number
    label: string
    value: string
    market_description: string
  }>
  league_id: number
  league: {
    name: string
  }
  metadata?: {
    predictable?: boolean
  }
}

interface FixtureAnalysis {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predictions: {
    home: number
    draw: number
    away: number
  }
  predicted_outcome: 'home' | 'draw' | 'away'
  prediction_confidence: number
  odds_data?: {
    home: number | null
    draw: number | null
    away: number | null
    bookmaker: string
  }
  ev_analysis: {
    home: number | null
    draw: number | null
    away: number | null
    best_bet: 'home' | 'draw' | 'away' | null
    best_ev: number | null
  }
  prediction_strength: string
  ensemble_info: {
    model_count: number
    consensus: number
    variance: number
    strategy: string
  }
}

// 1X2 prediction type IDs from SportMonks
const X12_TYPE_IDS = [233, 237, 238]

// Common bookmaker ID to name mapping
const BOOKMAKER_NAMES: { [key: number]: string } = {
  1: 'Bet365',
  2: 'William Hill', 
  3: 'Ladbrokes',
  4: 'Paddy Power',
  5: 'Sky Bet',
  6: 'Betfair',
  7: 'Unibet',
  8: 'BetVictor',
  9: 'Coral',
  10: '888sport',
  11: 'Betway',
  12: 'Pinnacle',
  13: 'Marathon',
  14: 'SBOBET',
  15: 'Interwetten',
  16: 'Tipico',
  17: 'Bwin',
  18: 'Betfred',
  19: 'Boylesports',
  20: 'Paddy Power Betfair'
}

// Function to extract 1X2 odds from fixture
function extract1X2Odds(fixture: SportMonksFixture): { home: number | null; draw: number | null; away: number | null; bookmaker: string } | undefined {
  if (!fixture.odds || fixture.odds.length === 0) {
    return undefined
  }

  // Find 1X2 odds (market_id: 1, Fulltime Result)
  const x12Odds = fixture.odds.filter(odd => odd.market_id === 1)
  
  if (x12Odds.length === 0) {
    return undefined
  }

  // Group by bookmaker and get the first available bookmaker
  const bookmakerOdds: { [key: number]: { home?: number; draw?: number; away?: number; bookmaker_id: number } } = {}
  
  for (const odd of x12Odds) {
    const bookmakerId = odd.bookmaker_id
    if (!bookmakerOdds[bookmakerId]) {
      bookmakerOdds[bookmakerId] = { bookmaker_id: bookmakerId }
    }
    
    const value = parseFloat(odd.value)
    if (!isNaN(value)) {
      if (odd.label.toLowerCase() === 'home') {
        bookmakerOdds[bookmakerId].home = value
      } else if (odd.label.toLowerCase() === 'draw') {
        bookmakerOdds[bookmakerId].draw = value
      } else if (odd.label.toLowerCase() === 'away') {
        bookmakerOdds[bookmakerId].away = value
      }
    }
  }

  // Find the first bookmaker with complete odds (all three outcomes)
  for (const [bookmakerId, odds] of Object.entries(bookmakerOdds)) {
    if (odds.home && odds.draw && odds.away) {
      return {
        home: odds.home,
        draw: odds.draw,
        away: odds.away,
        bookmaker: BOOKMAKER_NAMES[parseInt(bookmakerId)] || `Bookmaker ${bookmakerId}`
      }
    }
  }

  // If no complete odds found, return the first available
  const firstBookmaker = Object.values(bookmakerOdds)[0]
  if (firstBookmaker) {
    return {
      home: firstBookmaker.home || null,
      draw: firstBookmaker.draw || null,
      away: firstBookmaker.away || null,
      bookmaker: BOOKMAKER_NAMES[firstBookmaker.bookmaker_id] || `Bookmaker ${firstBookmaker.bookmaker_id}`
    }
  }

  return undefined
}

// Consensus ensemble method
function consensusEnsemble(models: any[]): { home: number; draw: number; away: number } {
  if (models.length === 0) {
    throw new Error('No models provided for ensemble')
  }

  // Find the outcome each model predicts
  const modelOutcomes: Array<'home' | 'draw' | 'away'> = []
  for (const model of models) {
    const maxProb = Math.max(model.home, model.draw, model.away)
    if (maxProb === model.home) {
      modelOutcomes.push('home')
    } else if (maxProb === model.draw) {
      modelOutcomes.push('draw')
    } else {
      modelOutcomes.push('away')
    }
  }

  // Count votes
  const voteCounts: Record<string, number> = { home: 0, draw: 0, away: 0 }
  for (const outcome of modelOutcomes) {
    voteCounts[outcome]++
  }

  // Find majority outcome
  const majorityOutcome = Object.entries(voteCounts).reduce((a, b) => 
    b[1] > a[1] ? b : a
  )[0] as 'home' | 'draw' | 'away'

  // Calculate consensus probabilities
  let consensusHome: number
  let consensusDraw: number
  let consensusAway: number

  if (majorityOutcome === 'home') {
    consensusHome = Math.max(...models.map(m => m.home))
    consensusDraw = models.reduce((sum, m) => sum + m.draw, 0) / models.length
    consensusAway = models.reduce((sum, m) => sum + m.away, 0) / models.length
  } else if (majorityOutcome === 'draw') {
    consensusHome = models.reduce((sum, m) => sum + m.home, 0) / models.length
    consensusDraw = Math.max(...models.map(m => m.draw))
    consensusAway = models.reduce((sum, m) => sum + m.away, 0) / models.length
  } else { // away
    consensusHome = models.reduce((sum, m) => sum + m.home, 0) / models.length
    consensusDraw = models.reduce((sum, m) => sum + m.draw, 0) / models.length
    consensusAway = Math.max(...models.map(m => m.away))
  }

  return {
    home: consensusHome,
    draw: consensusDraw,
    away: consensusAway
  }
}

function analyzeFixture(fixture: SportMonksFixture): FixtureAnalysis | null {
  try {
    // Extract 1X2 predictions
    const x12Predictions = fixture.predictions?.filter(pred => X12_TYPE_IDS.includes(pred.type_id)) || []
    
    if (x12Predictions.length === 0) {
      return null // No 1X2 predictions available
    }

    // Use consensus ensemble if we have 3 models, otherwise use best available
    let finalPredictions: { home: number; draw: number; away: number }
    let strategy = 'single_model'
    let modelCount = x12Predictions.length

    if (x12Predictions.length === 3) {
      const models = x12Predictions.map(p => p.predictions)
      finalPredictions = consensusEnsemble(models)
      strategy = 'consensus_ensemble_3_models'
    } else if (x12Predictions.length > 0) {
      // Use the highest confidence prediction
      const bestPred = x12Predictions.reduce((best, current) => {
        const currentMax = Math.max(
          current.predictions.home || 0, 
          current.predictions.draw || 0, 
          current.predictions.away || 0
        )
        const bestMax = Math.max(
          best.predictions.home || 0, 
          best.predictions.draw || 0, 
          best.predictions.away || 0
        )
        return currentMax > bestMax ? current : best
      })
      finalPredictions = {
        home: bestPred.predictions.home || 0,
        draw: bestPred.predictions.draw || 0,
        away: bestPred.predictions.away || 0
      }
      strategy = `partial_1x2_${x12Predictions.length}_models`
    } else {
      return null
    }

    // Calculate prediction strength
    const probs = [finalPredictions.home, finalPredictions.draw, finalPredictions.away]
    const sortedProbs = [...probs].sort((a, b) => b - a)
    const gap = sortedProbs[0] - sortedProbs[1]
    
    let predictionStrength = 'Low'
    if (gap >= 60) predictionStrength = 'Very Strong'
    else if (gap >= 40) predictionStrength = 'Strong'
    else if (gap >= 20) predictionStrength = 'Moderate'

    // Extract odds data
    const oddsData = extract1X2Odds(fixture)

    // Calculate EV for all outcomes
    let evAnalysis = {
      home: null as number | null,
      draw: null as number | null,
      away: null as number | null,
      best_bet: null as 'home' | 'draw' | 'away' | null,
      best_ev: null as number | null
    }

    if (oddsData) {
      // Calculate EV for each outcome
      if (oddsData.home) {
        evAnalysis.home = (finalPredictions.home / 100) * oddsData.home - 1
      }
      if (oddsData.draw) {
        evAnalysis.draw = (finalPredictions.draw / 100) * oddsData.draw - 1
      }
      if (oddsData.away) {
        evAnalysis.away = (finalPredictions.away / 100) * oddsData.away - 1
      }

      // Find best bet (highest positive EV)
      const evs = [
        { outcome: 'home' as const, ev: evAnalysis.home },
        { outcome: 'draw' as const, ev: evAnalysis.draw },
        { outcome: 'away' as const, ev: evAnalysis.away }
      ].filter(item => item.ev !== null && item.ev > 0)

      if (evs.length > 0) {
        const best = evs.reduce((max, current) => current.ev! > max.ev! ? current : max)
        evAnalysis.best_bet = best.outcome
        evAnalysis.best_ev = best.ev
      }
    }

    // Calculate ensemble metadata
    const homeAvg = x12Predictions.reduce((sum, p) => sum + (p.predictions.home || 0), 0) / modelCount
    const drawAvg = x12Predictions.reduce((sum, p) => sum + (p.predictions.draw || 0), 0) / modelCount
    const awayAvg = x12Predictions.reduce((sum, p) => sum + (p.predictions.away || 0), 0) / modelCount

    // Calculate consensus (how many models agree with the final prediction)
    const bestOutcome = Math.max(finalPredictions.home, finalPredictions.draw, finalPredictions.away) === finalPredictions.home ? 'home' :
                       Math.max(finalPredictions.home, finalPredictions.draw, finalPredictions.away) === finalPredictions.draw ? 'draw' : 'away'

    const consensusCount = x12Predictions.filter(p => {
      const max = Math.max(p.predictions.home || 0, p.predictions.draw || 0, p.predictions.away || 0)
      return (max === (p.predictions.home || 0) && bestOutcome === 'home') ||
             (max === (p.predictions.draw || 0) && bestOutcome === 'draw') ||
             (max === (p.predictions.away || 0) && bestOutcome === 'away')
    }).length

    const consensus = consensusCount / modelCount

    // Calculate variance
    const homeVariance = x12Predictions.reduce((sum, p) => sum + Math.pow((p.predictions.home || 0) - homeAvg, 2), 0) / modelCount
    const drawVariance = x12Predictions.reduce((sum, p) => sum + Math.pow((p.predictions.draw || 0) - drawAvg, 2), 0) / modelCount
    const awayVariance = x12Predictions.reduce((sum, p) => sum + Math.pow((p.predictions.away || 0) - awayAvg, 2), 0) / modelCount
    const avgVariance = (homeVariance + drawVariance + awayVariance) / 3

    // Calculate the actual predicted outcome
    const maxPrediction = Math.max(finalPredictions.home, finalPredictions.draw, finalPredictions.away)
    let predictedOutcome: 'home' | 'draw' | 'away'
    if (maxPrediction === finalPredictions.home) {
      predictedOutcome = 'home'
    } else if (maxPrediction === finalPredictions.draw) {
      predictedOutcome = 'draw'
    } else {
      predictedOutcome = 'away'
    }

    // Correctly map home/away teams using meta.location
    const homeTeam = fixture.participants.find(p => p.meta?.location === 'home')?.name || 'Home'
    const awayTeam = fixture.participants.find(p => p.meta?.location === 'away')?.name || 'Away'

    return {
      fixture_id: fixture.id,
      home_team: homeTeam,
      away_team: awayTeam,
      league: fixture.league.name,
      kickoff: fixture.starting_at,
      predictions: finalPredictions,
      predicted_outcome: predictedOutcome,
      prediction_confidence: Math.round(maxPrediction),
      odds_data: oddsData,
      ev_analysis: evAnalysis,
      prediction_strength: predictionStrength,
      ensemble_info: {
        model_count: modelCount,
        consensus: Math.round(consensus * 100),
        variance: Math.round(avgVariance),
        strategy
      }
    }

  } catch (error) {
    console.error('Error analyzing fixture:', error)
    return null
  }
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

    // Check cache first
    const cacheKey = getCacheKey(`fixture:${fixtureId}`)
    const cachedData = getFromCache(cacheKey)
    if (cachedData) {
      console.log(`🎯 Cache HIT for fixture ${fixtureId}`)
      return NextResponse.json(cachedData)
    }

    console.log(`🚀 Cache MISS - Fetching fixture ${fixtureId}`)

    // Fetch fixture from SportMonks
    const url = `https://api.sportmonks.com/v3/football/fixtures/${fixtureId}`
    const params_api = new URLSearchParams({
      api_token: SPORTMONKS_API_TOKEN || '',
      include: 'participants;league;metadata;predictions;odds',
      timezone: 'Europe/Bucharest'
    })

    const data = await apiClient.request(`${url}?${params_api}`)
    const fixture: SportMonksFixture = data.data

    if (!fixture) {
      return NextResponse.json(
        { error: 'Fixture not found' },
        { status: 404 }
      )
    }

    // Analyze the fixture
    const analysis = analyzeFixture(fixture)

    if (!analysis) {
      return NextResponse.json(
        { error: 'No predictions available for this fixture' },
        { status: 404 }
      )
    }

    // Prepare response data
    const responseData = {
      fixture: analysis,
      lastUpdated: new Date().toISOString()
    }

    // Cache the response
    setCache(cacheKey, responseData, CACHE_DURATION.FIXTURE_DETAILS)
    console.log(`💾 Cached fixture ${fixtureId} analysis`)

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('Error fetching fixture:', error)
    return NextResponse.json(
      { error: 'Failed to fetch fixture analysis' },
      { status: 500 }
    )
  }
}
