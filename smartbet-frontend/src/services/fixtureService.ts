import { Recommendation } from '../types/recommendation'

// Robust apiClient implementation
const apiClient = {
    async request(url: string) {
        const controller = new AbortController()
        // 30 second timeout for external API calls
        const timeoutId = setTimeout(() => controller.abort(), 30000)
        try {
            const response = await fetch(url, { signal: controller.signal })
            clearTimeout(timeoutId)
            if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`)
            return response.json()
        } catch (e: any) {
            clearTimeout(timeoutId)
            console.error(`API Request failed: ${url} - ${e.message}`)
            throw e
        }
    }
}

function getApiToken(): string {
    const token = process.env.SPORTMONKS_API_TOKEN
    if (!token) {
        throw new Error('SPORTMONKS_API_TOKEN environment variable is not set')
    }
    return token
}

// Multi-market support types
export interface MarketPrediction {
    market_type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    type_id: number
    predicted_outcome: string
    probability: number
    probability_gap: number
    odds: number
    expected_value: number
    market_score: number
    bookmaker?: string
    raw_predictions: Record<string, number>
}

const MARKET_CONFIG: Record<string, { name: string; display_name: string }> = {
    '1x2': { name: '1X2', display_name: 'Match Result' },
    'btts': { name: 'BTTS', display_name: 'Both Teams to Score' },
    'over_under_2.5': { name: 'O/U 2.5', display_name: 'Over/Under 2.5 Goals' },
    'double_chance': { name: 'DC', display_name: 'Double Chance' }
}

function calculateMarketScore(probability_gap: number, expected_value: number, confidence: number): number {
    const normalizedGap = Math.min(probability_gap, 0.5) / 0.5
    const normalizedEV = Math.min(Math.max(expected_value, 0), 0.5) / 0.5
    return (normalizedGap * 0.4) + (normalizedEV * 0.3) + (confidence * 0.3)
}

export async function getFixtureDetails(fixtureId: string) {
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
        return null
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
            home: normalizeProbability(bestPred.predictions.home || 0) * 100, // Convert to percentage for consistency
            draw: normalizeProbability(bestPred.predictions.draw || 0) * 100,
            away: normalizeProbability(bestPred.predictions.away || 0) * 100
        }

        // Validate that probabilities sum to approximately 100%
        const total = predictionData.home + predictionData.draw + predictionData.away
        const tolerance = 5 // Allow 5% deviation

        if (Math.abs(total - 100) > tolerance) {
            // Normalize probabilities to sum to exactly 100%
            const factor = 100 / total
            predictionData.home *= factor
            predictionData.draw *= factor
            predictionData.away *= factor
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
        if (odd.bookmaker_id && data.meta?.bookmakers) {
            const bookmakerMeta = data.meta.bookmakers.find((bm: any) => bm.id === odd.bookmaker_id)
            if (bookmakerMeta) return bookmakerMeta.name
        }

        // Fallback: use a common bookmaker name based on ID patterns
        const bookmakerMap: { [key: number]: string } = {
            1: 'Bet365', 2: 'Betfair', 14: 'William Hill', 16: 'Paddy Power',
            26: 'Ladbrokes', 29: 'Coral', 32: 'Sky Bet', 35: 'Unibet',
            38: 'Betway', 64: '888Sport'
        }

        if (odd.bookmaker_id && bookmakerMap[odd.bookmaker_id]) {
            return bookmakerMap[odd.bookmaker_id]
        }

        // Final fallback
        return `Bookmaker ${odd.bookmaker_id || 'Unknown'}`
    }

    // ============= MULTI-MARKET PROCESSING =============
    // Process all market types for the All Markets display
    const allMarketsData: MarketPrediction[] = []
    const marketResults: MarketPrediction[] = []

    // Helper for normalizing probabilities
    const normalizeProbability = (value: number) => {
        if (!value || value <= 0) return 0
        if (value > 1) return value / 100
        return value
    }

    // --- 1X2 Market ---
    if (x12Predictions.length > 0 && predictionData) {
        const avgHome = predictionData.home / 100
        const avgDraw = predictionData.draw / 100
        const avgAway = predictionData.away / 100

        const probs = [avgHome, avgDraw, avgAway]
        const sortedProbs = [...probs].sort((a, b) => b - a)
        const maxProb = sortedProbs[0]
        const gap = sortedProbs[0] - sortedProbs[1]

        let outcome = 'Draw'
        if (maxProb === avgHome) outcome = 'Home'
        else if (maxProb === avgAway) outcome = 'Away'

        // Get 1X2 odds - Find MAX odds
        let oddsValue = 1
        let bookmakerName = undefined
        if (fixture.odds) {
            const x12Odds = fixture.odds.filter((odd: any) => odd.market_id === 1)

            let bestOddEntry = null
            let maxVal = -1

            for (const odd of x12Odds) {
                if (odd.label?.toLowerCase() === outcome.toLowerCase()) {
                    const val = parseFloat(odd.value) || 0
                    if (val > maxVal) {
                        maxVal = val
                        bestOddEntry = odd
                    }
                }
            }

            if (bestOddEntry) {
                oddsValue = maxVal
                bookmakerName = getBookmakerName(bestOddEntry)
            }
        }

        const ev = (maxProb * oddsValue) - 1
        const minGap = outcome === 'Draw' ? 0.15 : 0.12

        const marketData: MarketPrediction = {
            market_type: '1x2',
            type_id: x12Predictions[0].type_id,
            predicted_outcome: outcome,
            probability: maxProb,
            probability_gap: gap,
            odds: oddsValue,
            expected_value: ev,
            market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
            bookmaker: bookmakerName,
            raw_predictions: { home: avgHome, draw: avgDraw, away: avgAway }
        }

        allMarketsData.push(marketData)
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
        const outcome = yesProb > noProb ? 'BTTS Yes' : 'BTTS No'

        let oddsValue = 1
        let bookmakerName = undefined
        if (fixture.odds) {
            const bttsOdds = fixture.odds.filter((odd: any) =>
                odd.market_id === 28 || odd.name?.toLowerCase().includes('btts')
            )

            let bestOddEntry = null
            let maxVal = -1

            for (const odd of bttsOdds) {
                const label = odd.label?.toLowerCase()
                if ((outcome.includes('Yes') && label === 'yes') || (outcome.includes('No') && label === 'no')) {
                    const val = parseFloat(odd.value) || 0
                    if (val > maxVal) {
                        maxVal = val
                        bestOddEntry = odd
                    }
                }
            }

            if (bestOddEntry) {
                oddsValue = maxVal
                bookmakerName = getBookmakerName(bestOddEntry)
            }
        }

        const ev = (maxProb * oddsValue) - 1

        const marketData: MarketPrediction = {
            market_type: 'btts',
            type_id: 231,
            predicted_outcome: outcome,
            probability: maxProb,
            probability_gap: gap,
            odds: oddsValue,
            expected_value: ev,
            market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
            bookmaker: bookmakerName,
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
        const outcome = overProb > underProb ? 'Over 2.5' : 'Under 2.5'

        let oddsValue = 1
        let bookmakerName = undefined
        if (fixture.odds) {
            // First try market_id = 18 (Over/Under), then fallback to text matching
            const ouOdds = fixture.odds.filter((odd: any) => {
                // Check market_id first (18 = Over/Under in SportMonks)
                if (odd.market_id === 18) return true
                // Also look for 2.5 in name or label
                const nameMatch = odd.name?.toLowerCase().includes('2.5') ||
                    odd.label?.toLowerCase().includes('2.5') ||
                    odd.name?.toLowerCase().includes('over/under')
                return nameMatch
            })

            let bestOddEntry = null
            let maxVal = -1

            // STRICT matching: MUST contain "2.5" somewhere to be the right market
            for (const odd of ouOdds) {
                const label = odd.label?.toLowerCase() || ''
                const name = odd.name?.toLowerCase() || ''

                const has25 = label.includes('2.5') || name.includes('2.5')
                if (!has25) continue  // Skip if not 2.5 line

                let isMatch = false
                const val = parseFloat(odd.value)

                // Check for Over 2.5 specifically
                if (outcome.includes('Over') && label.includes('over')) {
                    // Reasonable Over 2.5 odds range: 1.30 - 3.50
                    if (val >= 1.30 && val <= 3.50) {
                        isMatch = true
                    }
                }
                // Check for Under 2.5 specifically  
                if (outcome.includes('Under') && label.includes('under')) {
                    // Reasonable Under 2.5 odds range: 1.30 - 3.50
                    if (val >= 1.30 && val <= 3.50) {
                        isMatch = true
                    }
                }

                if (isMatch && val > maxVal) {
                    maxVal = val
                    bestOddEntry = odd
                }
            }

            if (bestOddEntry) {
                oddsValue = maxVal
                bookmakerName = getBookmakerName(bestOddEntry)
            }
        }

        const ev = (maxProb * oddsValue) - 1

        const marketData: MarketPrediction = {
            market_type: 'over_under_2.5',
            type_id: 235,
            predicted_outcome: outcome,
            probability: maxProb,
            probability_gap: gap,
            odds: oddsValue,
            expected_value: ev,
            market_score: calculateMarketScore(gap, Math.max(ev, 0), maxProb),
            bookmaker: bookmakerName,
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

        let oddsValue = 1
        let bookmakerName = undefined
        if (fixture.odds) {
            const dcOdds = fixture.odds.filter((odd: any) => odd.market_id === 12)

            let bestOddEntry = null
            let maxVal = -1

            for (const odd of dcOdds) {
                const label = odd.label?.toLowerCase().replace(/\s/g, '')
                if (label === outcome.toLowerCase()) {
                    const val = parseFloat(odd.value) || 0
                    if (val > maxVal) {
                        maxVal = val
                        bestOddEntry = odd
                    }
                }
            }

            if (bestOddEntry) {
                oddsValue = maxVal
                bookmakerName = getBookmakerName(bestOddEntry)
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
            bookmaker: bookmakerName,
            raw_predictions: { '1X': homeOrDraw, 'X2': awayOrDraw, '12': homeOrAway }
        }

        allMarketsData.push(marketData)
        if (gap >= 0.10 && ev > 0) {
            marketResults.push(marketData)
        }
    }

    // Sort and select best market
    allMarketsData.sort((a, b) => b.market_score - a.market_score)
    marketResults.sort((a, b) => b.market_score - a.market_score)
    const bestMarket = marketResults[0] || allMarketsData[0]

    // Extract odds if available
    let oddsData = null
    if (fixture.odds && fixture.odds.length > 0) {
        const x12Odds = fixture.odds.filter((odd: any) => odd.market_id === 1)
        if (x12Odds.length > 0) {
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

            // Calculate EV for home (convert percentage to decimal for calculation)
            if (oddsData.home && predictionData.home > 0) {
                const probDecimal = predictionData.home / 100
                const rawEV = (probDecimal * oddsData.home) - 1
                evAnalysis.home = rawEV * 100
            }

            // Calculate EV for draw
            if (oddsData.draw && predictionData.draw > 0) {
                const probDecimal = predictionData.draw / 100
                const rawEV = (probDecimal * oddsData.draw) - 1
                evAnalysis.draw = rawEV * 100
            }

            // Calculate EV for away
            if (oddsData.away && predictionData.away > 0) {
                const probDecimal = predictionData.away / 100
                const rawEV = (probDecimal * oddsData.away) - 1
                evAnalysis.away = rawEV * 100
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

                // Safety check: cap unrealistic EV values
                if (evAnalysis.best_ev && evAnalysis.best_ev > 100) {
                    evAnalysis.best_ev = Math.min(evAnalysis.best_ev, 50)
                    // Also cap individual EVs
                    if (evAnalysis.home && evAnalysis.home > 100) evAnalysis.home = Math.min(evAnalysis.home, 50)
                    if (evAnalysis.draw && evAnalysis.draw > 100) evAnalysis.draw = Math.min(evAnalysis.draw, 50)
                    if (evAnalysis.away && evAnalysis.away > 100) evAnalysis.away = Math.min(evAnalysis.away, 50)
                }
            }
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
                source: 'AI',
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
            has_odds: fixture.odds && fixture.odds.length > 0,
            // Multi-market support for Explore section
            best_market: bestMarket ? {
                type: bestMarket.market_type,
                name: MARKET_CONFIG[bestMarket.market_type].name,
                display_name: MARKET_CONFIG[bestMarket.market_type].display_name,
                predicted_outcome: bestMarket.predicted_outcome,
                probability: bestMarket.probability,
                probability_gap: bestMarket.probability_gap,
                odds: bestMarket.odds,
                expected_value: bestMarket.expected_value,
                market_score: bestMarket.market_score,
                bookmaker: bestMarket.bookmaker
            } : undefined,
            all_markets: allMarketsData.map(m => ({
                type: m.market_type,
                name: MARKET_CONFIG[m.market_type].name,
                predicted_outcome: m.predicted_outcome,
                probability: m.probability,
                odds: m.odds,
                expected_value: m.expected_value,
                market_score: m.market_score,
                bookmaker: m.bookmaker,
                is_recommended: marketResults.some(r => r.market_type === m.market_type)
            }))
        },
        lastUpdated: new Date().toISOString()
    }

    // --- ENRICHMENT: Fetch Standings for Form Data ---
    try {
        if (fixture.season_id) {
            const standingsUrl = `https://api.sportmonks.com/v3/football/standings/seasons/${fixture.season_id}?api_token=${getApiToken()}&include=form`
            const standingsRes = await apiClient.request(standingsUrl)
            const standingsData = standingsRes.data || []

            let homeForm = null
            let awayForm = null

            const homeId = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.id
            const awayId = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.id

            if (homeId && awayId) {
                standingsData.forEach((standing: any) => {
                    if (standing.participant_id === homeId && standing.form) homeForm = standing.form
                    if (standing.participant_id === awayId && standing.form) awayForm = standing.form
                })

                if (homeForm || awayForm) {
                    // @ts-ignore
                    responseData.fixture.teams_data = {
                        home: { form: homeForm },
                        away: { form: awayForm }
                    }
                }
            }
        }
    } catch (err) {
        console.error('Error fetching standings:', err)
        // Non-fatal error, continue without form data
    }

    return responseData
}
