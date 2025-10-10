import { NextRequest, NextResponse } from 'next/server'
import { apiClient, createBatchedLeagueRequests } from '../../lib/api-client'
import { performanceMonitor } from '../../lib/performance-monitor'
import { logCacheOperation } from '../../lib/performance-logger'

// Cache configuration
const CACHE_DURATION = {
  FIXTURES: 15 * 60 * 1000,    // 15 minutes - fixtures don't change often
  PREDICTIONS: 30 * 60 * 1000, // 30 minutes - predictions update less frequently  
  ODDS: 5 * 60 * 1000          // 5 minutes - odds change frequently
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
  
  // Record cache hit for performance monitoring
  performanceMonitor.endRequest({
    url: key,
    method: 'GET',
    startTime: Date.now()
  } as any, true, undefined, true)
  
  logCacheOperation('hit', key)
  return cached.data
}

function setCache(key: string, data: any, duration: number): void {
  cache.set(key, {
    data,
    timestamp: Date.now(),
    duration
  })
  
  logCacheOperation('set', key)
}

// Smart cache cleanup - remove expired entries
function cleanupCache(): void {
  const now = Date.now()
  for (const [key, cached] of cache.entries()) {
    if (now - cached.timestamp > cached.duration) {
      cache.delete(key)
    }
  }
}

// All 27 leagues covered by subscription for maximum opportunity coverage
const SUPPORTED_LEAGUE_IDS = [
  8,     // Premier League
  9,     // Championship
  24,    // FA Cup
  27,    // Carabao Cup
  72,    // Eredivisie
  82,    // Bundesliga
  181,   // Admiral Bundesliga
  208,   // Pro League
  244,   // 1. HNL
  271,   // Superliga
  301,   // Ligue 1
  384,   // Serie A
  387,   // Serie B
  390,   // Coppa Italia
  444,   // Eliteserien
  453,   // Ekstraklasa
  462,   // Liga Portugal
  486,   // Premier League (Romanian)
  501,   // Premiership
  564,   // La Liga
  567,   // La Liga 2
  570,   // Copa Del Rey
  573,   // Allsvenskan
  591,   // Super League
  600,   // Super Lig
  609,   // Premier League (additional)
  1371,  // UEFA Europa League Play-offs
]

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

interface Recommendation {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: 'Home' | 'Draw' | 'Away'
  confidence: number
  odds: number | null
  ev: number | null
  score: number
  explanation: string
  probabilities: {
    home: number
    draw: number
    away: number
  }
  odds_data?: {
    home: number | null
    draw: number | null
    away: number | null
    bookmaker: string
    predicted_odd: number | null
  }
}

interface PredictionAnalysis {
  recommendedPrediction: any
  confidence: number
  consensus: number
  variance: number
  modelCount: number
  strategy: string
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
function extract1X2Odds(fixture: SportMonksFixture): { home: number | null; draw: number | null; away: number | null; bookmaker: string; predicted_odd: number | null } | null {
  if (!fixture.odds || fixture.odds.length === 0) {
    return null
  }

  // Find 1X2 odds (market_id: 1, Fulltime Result)
  const x12Odds = fixture.odds.filter(odd => odd.market_id === 1)
  
  if (x12Odds.length === 0) {
    return null
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
        bookmaker: BOOKMAKER_NAMES[parseInt(bookmakerId)] || `Bookmaker ${bookmakerId}`,
        predicted_odd: null // Will be set based on prediction
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
      bookmaker: BOOKMAKER_NAMES[firstBookmaker.bookmaker_id] || `Bookmaker ${firstBookmaker.bookmaker_id}`,
      predicted_odd: null
    }
  }

  return null
}

// Phase 1: Consensus Ensemble Method
// Combines 3 models (type_ids: 233, 237, 238) using majority vote with confidence weighting
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
  // Use max probability for the majority outcome, average for others
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

// Analyze multiple predictions and determine the best approach using Phase 1 ensemble logic
function analyzePredictions(predictions: any[]): PredictionAnalysis {
  const modelCount = predictions.length

  // Extract only 1X2 predictions (type_ids: 233, 237, 238)
  const x12Predictions = predictions.filter(p => X12_TYPE_IDS.includes(p.type_id))

  // If we have all 3 1X2 models, use consensus ensemble
  let finalPrediction: any
  let strategy = 'single_model'

  if (x12Predictions.length === 3) {
    // Phase 1: Consensus Ensemble Method
    const models = x12Predictions.map(p => p.predictions)
    const consensusResult = consensusEnsemble(models)
    
    finalPrediction = {
      predictions: consensusResult
    }
    strategy = 'consensus_ensemble_3_models'
  } else if (x12Predictions.length > 0) {
    // Fallback: use the highest confidence 1X2 model
    const bestX12 = x12Predictions.reduce((best, current) => {
    const currentMax = Math.max(current.predictions.home, current.predictions.draw, current.predictions.away)
    const bestMax = Math.max(best.predictions.home, best.predictions.draw, best.predictions.away)
    return currentMax > bestMax ? current : best
  })
    finalPrediction = bestX12
    strategy = `partial_1x2_${x12Predictions.length}_models`
  } else {
    // Fallback: use any available prediction
    finalPrediction = predictions.reduce((best, current) => {
      const currentMax = Math.max(current.predictions.home || 0, current.predictions.draw || 0, current.predictions.away || 0)
      const bestMax = Math.max(best.predictions.home || 0, best.predictions.draw || 0, best.predictions.away || 0)
      return currentMax > bestMax ? current : best
    })
    strategy = 'fallback_any_model'
  }

  // Calculate ensemble averages for metadata
  const homeAvg = predictions.reduce((sum, p) => sum + (p.predictions.home || 0), 0) / modelCount
  const drawAvg = predictions.reduce((sum, p) => sum + (p.predictions.draw || 0), 0) / modelCount
  const awayAvg = predictions.reduce((sum, p) => sum + (p.predictions.away || 0), 0) / modelCount

  // Calculate consensus
  const bestOutcome = Math.max(finalPrediction.predictions.home, finalPrediction.predictions.draw, finalPrediction.predictions.away) === finalPrediction.predictions.home ? 'home' :
                     Math.max(finalPrediction.predictions.home, finalPrediction.predictions.draw, finalPrediction.predictions.away) === finalPrediction.predictions.draw ? 'draw' : 'away'

  const consensusCount = predictions.filter(p => {
    const max = Math.max(p.predictions.home || 0, p.predictions.draw || 0, p.predictions.away || 0)
    return (max === (p.predictions.home || 0) && bestOutcome === 'home') ||
           (max === (p.predictions.draw || 0) && bestOutcome === 'draw') ||
           (max === (p.predictions.away || 0) && bestOutcome === 'away')
  }).length

  const consensus = consensusCount / modelCount

  // Calculate variance
  const homeVariance = predictions.reduce((sum, p) => sum + Math.pow((p.predictions.home || 0) - homeAvg, 2), 0) / modelCount
  const drawVariance = predictions.reduce((sum, p) => sum + Math.pow((p.predictions.draw || 0) - drawAvg, 2), 0) / modelCount
  const awayVariance = predictions.reduce((sum, p) => sum + Math.pow((p.predictions.away || 0) - awayAvg, 2), 0) / modelCount
  const avgVariance = (homeVariance + drawVariance + awayVariance) / 3

  const maxConfidence = Math.max(finalPrediction.predictions.home, finalPrediction.predictions.draw, finalPrediction.predictions.away)

  return {
    recommendedPrediction: finalPrediction,
    confidence: maxConfidence,
    consensus,
    variance: avgVariance,
    modelCount,
    strategy
  }
}

function calculateRecommendationScore(fixture: SportMonksFixture): Recommendation | null {
  try {
    // Enhanced prediction handling with multiple model analysis
    const validPredictions = []

    if (fixture.predictions && fixture.predictions.length > 0) {
      // Collect all valid predictions with proper data
      for (const prediction of fixture.predictions) {
        if (prediction.predictions &&
            typeof prediction.predictions.home === 'number' &&
            typeof prediction.predictions.draw === 'number' &&
            typeof prediction.predictions.away === 'number' &&
            prediction.predictions.home > 0 &&
            prediction.predictions.draw > 0 &&
            prediction.predictions.away > 0) {

          // Validate probabilities sum to reasonable range (90-110%)
          const total = prediction.predictions.home + prediction.predictions.draw + prediction.predictions.away
          if (total >= 90 && total <= 110) {
            validPredictions.push(prediction)
          }
        }
      }
    }

    if (validPredictions.length === 0) {
      return null // Skip fixtures without valid predictions
    }

    // Analyze prediction consistency and select best approach
    const analysis = analyzePredictions(validPredictions)

    // Use the best prediction based on our analysis
    const selectedPrediction = analysis.recommendedPrediction
    const predictions = selectedPrediction.predictions

    const probabilities = {
      home: predictions.home || 0,
      draw: predictions.draw || 0,
      away: predictions.away || 0
    }

    // Find the best outcome
    const outcomes = [
      { label: 'Home' as const, prob: probabilities.home },
      { label: 'Draw' as const, prob: probabilities.draw },
      { label: 'Away' as const, prob: probabilities.away }
    ]
    
    const best = outcomes.reduce((max, current) => 
      current.prob > max.prob ? current : max
    )

        // Apply minimum confidence threshold (55% - to show more matches)
        const MINIMUM_CONFIDENCE = 55 // Optimized threshold for maximum opportunities from all 27 leagues
    if (best.prob < MINIMUM_CONFIDENCE) {
      return null // Skip predictions below betting threshold
    }

    // Extract odds data and calculate EV
    const oddsData = extract1X2Odds(fixture)
    let predictedOdd: number | null = null
    let ev: number | null = null

    if (oddsData) {
      // Set the predicted odd based on the outcome
      if (best.label === 'Home') {
        predictedOdd = oddsData.home
      } else if (best.label === 'Draw') {
        predictedOdd = oddsData.draw
      } else if (best.label === 'Away') {
        predictedOdd = oddsData.away
      }

      // Calculate EV: (probability * odds) - 1
      if (predictedOdd && predictedOdd > 0) {
        ev = (best.prob / 100) * predictedOdd - 1
      }
    }

    // Filter out recommendations without odds or with negative EV - only show profitable bets
    if (oddsData === null || ev === null || ev <= 0) {
      return null // Skip recommendations without odds or negative EV
    }

    // Calculate ranking score: p_best + (ev > 0 ? min(ev, 0.20) : 0)
    const evContribution = ev && ev > 0 ? Math.min(ev, 0.20) : 0
    const score = best.prob + evContribution

    // Generate explanation with Phase 1 ensemble strategy info
    const strategyInfo = analysis.strategy === 'consensus_ensemble_3_models' ? ' using consensus of 3 AI models' :
                        analysis.strategy.startsWith('partial_1x2') ? ` using ${analysis.modelCount} AI models` :
                        ` using ${analysis.modelCount} prediction models`
    let oddsInfo = ''
    if (oddsData && predictedOdd) {
      oddsInfo = ` at ${predictedOdd} odds`
      if (ev && ev > 0) {
        oddsInfo += ` (+${Math.round(ev * 100)}% EV)`
      }
    }
    
    const explanation = `SmartBet AI predicts a ${best.label} win with ${Math.round(best.prob)}% confidence${strategyInfo}${oddsInfo}.`

        // Correctly map home/away teams using meta.location
        const homeTeam = fixture.participants.find(p => p.meta?.location === 'home')?.name || 'Home'
        const awayTeam = fixture.participants.find(p => p.meta?.location === 'away')?.name || 'Away'

    return {
      fixture_id: fixture.id,
          home_team: homeTeam,
          away_team: awayTeam,
      league: fixture.league.name,
      kickoff: fixture.starting_at,
      predicted_outcome: best.label,
      confidence: Math.round(best.prob),
          odds: predictedOdd,
      ev,
      score,
      explanation,
      probabilities,
          odds_data: oddsData ? {
            ...oddsData,
            predicted_odd: predictedOdd
          } : undefined,
      debug_info: {
        total_predictions: fixture.predictions?.length || 0,
        valid_predictions: validPredictions.length,
        strategy: analysis.strategy,
        consensus: Math.round(analysis.consensus * 100),
        variance: Math.round(analysis.variance),
        model_count: analysis.modelCount
      }
        } as Recommendation
  } catch (error) {
    console.error('Error calculating recommendation:', error)
    return null
  }
}

function isWithinNext14Days(dateString: string): boolean {
  const fixtureDate = new Date(dateString)
  const now = new Date()
  const fourteenDaysFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000)
  
  return fixtureDate >= now && fixtureDate <= fourteenDaysFromNow
}

export async function GET(request: NextRequest) {
  try {
    // Clean up expired cache entries
    cleanupCache()
    
    // Calculate date range for next 14 days
    const now = new Date()
    const fourteenDaysFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000)
    const startDate = now.toISOString().split('T')[0]
    const endDate = fourteenDaysFromNow.toISOString().split('T')[0]
    
    // Check cache first
    const cacheKey = getCacheKey('recommendations', { startDate, endDate })
    const cachedData = getFromCache(cacheKey)
    if (cachedData) {
      console.log('🎯 Cache HIT for recommendations')
      return NextResponse.json(cachedData)
    }
    
    console.log('🚀 Cache MISS - Fetching fixtures from all 27 leagues...')
    console.log('Date range:', startDate, 'to', endDate)
    console.log('Supported League IDs:', SUPPORTED_LEAGUE_IDS)

    // Fetch fixtures using smart batching and rate limiting
    let allFixtures: SportMonksFixture[] = []
    const leagueResults: { [key: number]: { name: string; count: number } } = {}
    
    // Check cache for each league first
    const uncachedLeagues: number[] = []
    
    for (const leagueId of SUPPORTED_LEAGUE_IDS) {
      const leagueCacheKey = getCacheKey(`fixtures:league:${leagueId}`, { startDate, endDate })
      const cachedLeagueData = getFromCache(leagueCacheKey)
      
      if (cachedLeagueData) {
        console.log(`🎯 Cache HIT for league ${leagueId}`)
        allFixtures.push(...cachedLeagueData.fixtures)
        leagueResults[leagueId] = cachedLeagueData.leagueInfo
      } else {
        uncachedLeagues.push(leagueId)
      }
    }
    
    // Batch fetch uncached leagues
    if (uncachedLeagues.length > 0) {
      console.log(`🚀 Cache MISS - Fetching ${uncachedLeagues.length} leagues with smart batching`)
      
      try {
        const batchResults = await apiClient.batchRequests(
          uncachedLeagues.map(leagueId => async () => {
            const url = `https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`
    const params = new URLSearchParams({
      api_token: SPORTMONKS_API_TOKEN,
              include: 'participants;league;metadata;predictions;odds',
              filters: `fixtureLeagues:${leagueId}`,
              per_page: '50',
              page: '1',
              timezone: 'Europe/Bucharest'
            })
            
            const response = await apiClient.request(`${url}?${params}`)
            const fixtures: SportMonksFixture[] = response.data || []
            
            if (fixtures.length > 0) {
              const leagueName = fixtures[0]?.league?.name || `League ${leagueId}`
              leagueResults[leagueId] = { name: leagueName, count: fixtures.length }
              console.log(`✅ League ${leagueId} (${leagueName}): ${fixtures.length} fixtures`)
              
              // Cache the league data
              const leagueCacheKey = getCacheKey(`fixtures:league:${leagueId}`, { startDate, endDate })
              setCache(leagueCacheKey, {
                fixtures,
                leagueInfo: { name: leagueName, count: fixtures.length }
              }, CACHE_DURATION.FIXTURES)
              
              return fixtures
            }
            
            return []
          }),
          3, // Batch size: 3 requests at a time
          1500 // 1.5 second delay between batches
        )
        
        // Flatten results
        allFixtures.push(...batchResults.flat())
        
      } catch (error) {
        console.error('❌ Batch fetching failed:', error)
        
        // Fallback to individual requests for failed leagues
        for (const leagueId of uncachedLeagues) {
          try {
            const url = `https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`
            const params = new URLSearchParams({
              api_token: SPORTMONKS_API_TOKEN,
              include: 'participants;league;metadata;predictions;odds',
              filters: `fixtureLeagues:${leagueId}`,
              per_page: '50',
              page: '1',
              timezone: 'Europe/Bucharest'
            })
            
            const response = await apiClient.request(`${url}?${params}`)
            const fixtures: SportMonksFixture[] = response.data || []
            
            if (fixtures.length > 0) {
              allFixtures.push(...fixtures)
              const leagueName = fixtures[0]?.league?.name || `League ${leagueId}`
              leagueResults[leagueId] = { name: leagueName, count: fixtures.length }
              console.log(`✅ Fallback: League ${leagueId} (${leagueName}): ${fixtures.length} fixtures`)
            }
          } catch (fallbackError) {
            console.error(`❌ Failed to fetch league ${leagueId}:`, fallbackError)
          }
        }
      }
    }

    console.log(`Found ${allFixtures.length} total fixtures from all leagues`)
    console.log('League breakdown:', leagueResults)

    // Process fixtures
    const recommendations: Recommendation[] = []
    const allPredictions: any[] = [] // For debugging
    const fixturesWithoutPredictions: any[] = [] // Track fixtures without predictions

    for (const fixture of allFixtures) {
      // All fixtures are already within the date range, no need to filter by date

      // Check if fixture is predictable
      if (fixture.metadata?.predictable === false) {
        continue
      }

      // Extract predictions - check if they exist in the fixture
      let matchWinnerPrediction = null

      console.log(`Processing fixture: ${fixture.participants?.[0]?.name} vs ${fixture.participants?.[1]?.name}`)
      console.log(`League: ${fixture.league?.name} (ID: ${fixture.league_id})`)
      console.log(`Predictions available: ${fixture.predictions?.length || 0}`)

      // The predictions come in an array, need to find ALL 1X2 predictions for ensemble
      // SportMonks uses type_ids 233, 237, 238 for 1X2 predictions
      const x12Predictions = []
      if (fixture.predictions && Array.isArray(fixture.predictions)) {
        for (const pred of fixture.predictions) {
          if (pred && pred.predictions &&
              typeof pred.predictions.home === 'number' &&
              typeof pred.predictions.draw === 'number' &&
              typeof pred.predictions.away === 'number' &&
              X12_TYPE_IDS.includes(pred.type_id)) {
            x12Predictions.push(pred)
            console.log(`Found 1X2 prediction (type_id: ${pred.type_id}):`, pred.predictions)
          }
        }
      }
      
      // Use ensemble if we have all 3 models, otherwise use first available
      if (x12Predictions.length === 3) {
        console.log(`Using consensus ensemble for ${fixture.participants?.[0]?.name} vs ${fixture.participants?.[1]?.name}`)
        matchWinnerPrediction = x12Predictions // Pass all 3 for ensemble
      } else if (x12Predictions.length > 0) {
        console.log(`Using ${x12Predictions.length} 1X2 models for ${fixture.participants?.[0]?.name} vs ${fixture.participants?.[1]?.name}`)
        matchWinnerPrediction = x12Predictions[0].predictions // Use first available
      }

      if (!matchWinnerPrediction) {
        fixturesWithoutPredictions.push({
          fixture_id: fixture.id,
          league: fixture.league.name,
          home_team: fixture.participants[0]?.name || 'Home',
          away_team: fixture.participants[1]?.name || 'Away',
          kickoff: fixture.starting_at,
          reason: 'No valid match winner predictions found in API response'
        })
        continue
      }

      // Create a fixture object with the prediction(s) for the recommendation function
      const fixtureWithPrediction = {
        ...fixture,
        predictions: Array.isArray(matchWinnerPrediction) ? matchWinnerPrediction : [{
          predictions: matchWinnerPrediction
        }]
      }

      const recommendation = calculateRecommendationScore(fixtureWithPrediction)
      if (recommendation) {
        recommendations.push(recommendation)
      }

      // Debug: collect all predictions regardless of threshold
      if (matchWinnerPrediction) {
        let maxProb = 0
        let probabilities = {}
        
        if (Array.isArray(matchWinnerPrediction)) {
          // Ensemble case - calculate from ensemble result
          const ensembleResult = consensusEnsemble(matchWinnerPrediction.map(p => p.predictions))
          maxProb = Math.max(ensembleResult.home, ensembleResult.draw, ensembleResult.away)
          probabilities = ensembleResult
        } else {
          // Single model case
          maxProb = Math.max(matchWinnerPrediction.home || 0, matchWinnerPrediction.draw || 0, matchWinnerPrediction.away || 0)
          probabilities = matchWinnerPrediction
        }
        
        allPredictions.push({
          fixture_id: fixture.id,
          league: fixture.league.name,
          home_team: fixture.participants[0]?.name || 'Home',
          away_team: fixture.participants[1]?.name || 'Away',
          kickoff: fixture.starting_at,
          max_confidence: maxProb,
          probabilities: probabilities
        })
      }
    }

        // Sort by confidence descending and take top 10 highest confidence predictions
    const topRecommendations = recommendations
      .sort((a, b) => b.confidence - a.confidence)
          .slice(0, 10)

    // Sort all predictions by confidence for debugging
    const sortedAllPredictions = allPredictions.sort((a, b) => b.max_confidence - a.max_confidence)

    // Generate user-friendly status message
    let statusMessage = 'success'
    let statusDetails = ''

    if (topRecommendations.length === 0) {
      if (fixturesWithoutPredictions.length > 0) {
        statusMessage = 'no_predictions_available'
        statusDetails = `${fixturesWithoutPredictions.length} fixtures found but no AI predictions available. This may indicate that the SportMonks predictions addon is not enabled for your account.`
      } else if (allFixtures.length === 0) {
        statusMessage = 'no_fixtures_found'
        statusDetails = 'No upcoming fixtures with predictions found in the next 14 days. This may be due to limited fixture coverage or predictions addon availability.'
      } else {
        statusMessage = 'no_high_confidence_predictions'
            statusDetails = `Found ${allPredictions.length} predictions but none met the ${55}% confidence threshold.`
      }
    }

    // Prepare final response data
    const responseData = {
      recommendations: topRecommendations,
      total: topRecommendations.length,
          confidence_threshold: 55,
          ensemble_method: 'consensus_3_models',
          ensemble_description: 'Phase 1: Consensus ensemble of 3 SportMonks AI models (type_ids: 233, 237, 238)',
      status: statusMessage,
      status_details: statusDetails,
      debug_info: {
          total_fixtures_found: allFixtures.length,
        total_with_predictions: allPredictions.length,
        fixtures_without_predictions: fixturesWithoutPredictions.length,
        highest_confidence: sortedAllPredictions.length > 0 ? sortedAllPredictions[0].max_confidence : 0,
        top_5_predictions: sortedAllPredictions.slice(0, 5).map(p => ({
          match: `${p.home_team} vs ${p.away_team}`,
          league: p.league,
          confidence: p.max_confidence,
          kickoff: p.kickoff
        })),
        fixtures_without_predictions: fixturesWithoutPredictions.slice(0, 5).map(f => ({
          match: `${f.home_team} vs ${f.away_team}`,
          league: f.league,
          kickoff: f.kickoff,
          reason: f.reason
        }))
      },
      lastUpdated: new Date().toISOString()
    }

    // Cache the final response
    setCache(cacheKey, responseData, CACHE_DURATION.FIXTURES)
    console.log('💾 Cached recommendations response')

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('Error fetching recommendations:', error)
    return NextResponse.json(
      { error: 'Failed to fetch recommendations' },
      { status: 500 }
    )
  }
}
