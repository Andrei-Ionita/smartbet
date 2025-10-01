import { NextRequest, NextResponse } from 'next/server'

// Only the 5 leagues we actually support with production models (correct SportMonks IDs)
const SUPPORTED_LEAGUE_IDS = [8, 564, 384, 82, 301] // English Premier League (8), La Liga (564), Serie A (384), German Bundesliga (82), Ligue 1 (301)

const SPORTMONKS_API_TOKEN = process.env.SPORTMONKS_API_TOKEN
if (!SPORTMONKS_API_TOKEN) {
  throw new Error('SPORTMONKS_API_TOKEN environment variable is not set')
}

interface SportMonksFixture {
  id: number
  name: string
  starting_at: string
  participants: Array<{ name: string }>
  predictions: Array<{
    type_id: number
    predictions: {
      home?: number
      draw?: number
      away?: number
      scores?: Record<string, number>
    }
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
}

interface PredictionAnalysis {
  recommendedPrediction: any
  confidence: number
  consensus: number
  variance: number
  modelCount: number
  strategy: string
}

// Analyze multiple predictions and determine the best approach
function analyzePredictions(predictions: any[]): PredictionAnalysis {
  const modelCount = predictions.length

  // Calculate ensemble averages
  const homeAvg = predictions.reduce((sum, p) => sum + p.predictions.home, 0) / modelCount
  const drawAvg = predictions.reduce((sum, p) => sum + p.predictions.draw, 0) / modelCount
  const awayAvg = predictions.reduce((sum, p) => sum + p.predictions.away, 0) / modelCount

  // Find prediction with highest confidence
  const bestPrediction = predictions.reduce((best, current) => {
    const currentMax = Math.max(current.predictions.home, current.predictions.draw, current.predictions.away)
    const bestMax = Math.max(best.predictions.home, best.predictions.draw, best.predictions.away)
    return currentMax > bestMax ? current : best
  })

  // Calculate consensus (how many models agree on the outcome)
  const bestOutcome = Math.max(bestPrediction.predictions.home, bestPrediction.predictions.draw, bestPrediction.predictions.away) === bestPrediction.predictions.home ? 'home' :
                     Math.max(bestPrediction.predictions.home, bestPrediction.predictions.draw, bestPrediction.predictions.away) === bestPrediction.predictions.draw ? 'draw' : 'away'

  const consensusCount = predictions.filter(p => {
    const max = Math.max(p.predictions.home, p.predictions.draw, p.predictions.away)
    return (max === p.predictions.home && bestOutcome === 'home') ||
           (max === p.predictions.draw && bestOutcome === 'draw') ||
           (max === p.predictions.away && bestOutcome === 'away')
  }).length

  const consensus = consensusCount / modelCount

  // Calculate variance (how spread out the predictions are)
  const homeVariance = predictions.reduce((sum, p) => sum + Math.pow(p.predictions.home - homeAvg, 2), 0) / modelCount
  const drawVariance = predictions.reduce((sum, p) => sum + Math.pow(p.predictions.draw - drawAvg, 2), 0) / modelCount
  const awayVariance = predictions.reduce((sum, p) => sum + Math.pow(p.predictions.away - awayAvg, 2), 0) / modelCount
  const avgVariance = (homeVariance + drawVariance + awayVariance) / 3

  // Determine strategy based on analysis
  let strategy = 'highest_confidence'
  let finalPrediction = bestPrediction

  // If we have good consensus (>60%) and low variance, use ensemble average
  if (consensus > 0.6 && avgVariance < 50) {
    strategy = 'ensemble_average'
    finalPrediction = {
      predictions: {
        home: homeAvg,
        draw: drawAvg,
        away: awayAvg
      }
    }
  }
  // If consensus is poor but we have many models, still use highest confidence
  else if (modelCount >= 3) {
    strategy = 'highest_confidence_with_consensus'
  }

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

    // Apply minimum confidence threshold (55% - optimized for SportMonks data)
    const MINIMUM_CONFIDENCE = 55
    if (best.prob < MINIMUM_CONFIDENCE) {
      return null // Skip predictions below betting threshold
    }

    // Calculate EV (if odds available - for now we'll set to null as SportMonks doesn't provide odds in predictions)
    const odds = null // SportMonks predictions don't include odds
    const ev = odds ? (best.prob * odds - 1) : null

    // Calculate ranking score: p_best + (ev > 0 ? min(ev, 0.20) : 0)
    const evContribution = ev && ev > 0 ? Math.min(ev, 0.20) : 0
    const score = best.prob + evContribution

    // Generate explanation with strategy info
    const strategyInfo = analysis.strategy === 'ensemble_average' ? ' (ensemble average)' :
                        analysis.strategy === 'highest_confidence_with_consensus' ? ' (high confidence)' : ''
    const explanation = `SportMonks AI predicts a ${best.label} win with ${Math.round(best.prob)}% confidence${strategyInfo}${odds ? ` and positive expected value at ${odds} odds` : ' based on multiple AI models'}.`

    return {
      fixture_id: fixture.id,
      home_team: fixture.participants[0]?.name || 'Home',
      away_team: fixture.participants[1]?.name || 'Away',
      league: fixture.league.name,
      kickoff: fixture.starting_at,
      predicted_outcome: best.label,
      confidence: Math.round(best.prob),
      odds,
      ev,
      score,
      explanation,
      probabilities,
      debug_info: {
        total_predictions: fixture.predictions?.length || 0,
        valid_predictions: validPredictions.length,
        strategy: analysis.strategy,
        consensus: Math.round(analysis.consensus * 100),
        variance: Math.round(analysis.variance),
        model_count: analysis.modelCount
      }
    }
  } catch (error) {
    console.error('Error calculating recommendation:', error)
    return null
  }
}

function isWithinNext7Days(dateString: string): boolean {
  const fixtureDate = new Date(dateString)
  const now = new Date()
  const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  
  return fixtureDate >= now && fixtureDate <= sevenDaysFromNow
}

export async function GET(request: NextRequest) {
  try {
    // Fetch upcoming fixtures with predictions
    const url = 'https://api.sportmonks.com/v3/football/fixtures/upcoming/markets/1'
    const params = new URLSearchParams({
      api_token: SPORTMONKS_API_TOKEN,
      include: 'participants;league;metadata;predictions',
      filters: `fixtureLeagues:${SUPPORTED_LEAGUE_IDS.join(',')}`,
      per_page: '50'
    })

    const response = await fetch(`${url}?${params}`, {
      headers: {
        'Accept': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`SportMonks API error: ${response.status}`)
    }

    const data = await response.json()
    const fixtures: SportMonksFixture[] = data.data || []

    // Process fixtures
    const recommendations: Recommendation[] = []
    const allPredictions: any[] = [] // For debugging
    
    for (const fixture of fixtures) {
      // Filter by supported leagues and next 7 days
      if (!SUPPORTED_LEAGUE_IDS.includes(fixture.league_id) || 
          !isWithinNext7Days(fixture.starting_at)) {
        continue
      }

      // Check if fixture is predictable
      if (fixture.metadata?.predictable === false) {
        continue
      }

      const recommendation = calculateRecommendationScore(fixture)
      if (recommendation) {
        recommendations.push(recommendation)
      }

      // Debug: collect all predictions regardless of threshold
      const predictions = fixture.predictions?.[0]?.predictions
      if (predictions && (predictions.home || predictions.draw || predictions.away)) {
        const maxProb = Math.max(predictions.home || 0, predictions.draw || 0, predictions.away || 0)
        allPredictions.push({
          fixture_id: fixture.id,
          league: fixture.league.name,
          home_team: fixture.participants[0]?.name || 'Home',
          away_team: fixture.participants[1]?.name || 'Away',
          kickoff: fixture.starting_at,
          max_confidence: maxProb,
          probabilities: predictions
        })
      }
    }

    // Sort by confidence descending and take top 5 highest confidence predictions
    const topRecommendations = recommendations
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5)

    // Sort all predictions by confidence for debugging
    const sortedAllPredictions = allPredictions.sort((a, b) => b.max_confidence - a.max_confidence)

    return NextResponse.json({
      recommendations: topRecommendations,
      total: topRecommendations.length,
      confidence_threshold: 55, // Only shows predictions with ≥55% confidence (optimized threshold)
      debug_info: {
        total_fixtures_found: fixtures.length,
        total_with_predictions: allPredictions.length,
        highest_confidence: sortedAllPredictions.length > 0 ? sortedAllPredictions[0].max_confidence : 0,
        top_5_predictions: sortedAllPredictions.slice(0, 5).map(p => ({
          match: `${p.home_team} vs ${p.away_team}`,
          league: p.league,
          confidence: p.max_confidence,
          kickoff: p.kickoff
        }))
      },
      lastUpdated: new Date().toISOString()
    })

  } catch (error) {
    console.error('Error fetching recommendations:', error)
    return NextResponse.json(
      { error: 'Failed to fetch recommendations' },
      { status: 500 }
    )
  }
}
