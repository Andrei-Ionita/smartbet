import {
    expectedValue,
    priceMarket,
    type MarketPrice,
    type OddsProvenance,
    type OddsUnavailableReason,
    type ProductMarket,
} from '@/app/lib/marketPricing'
import {
    buildFixtureIntelligence,
    type IntelligenceMarketInput,
    type IntelligenceOutcomeInput,
} from '@/app/lib/fixtureIntelligence'

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
    market_type: ProductMarket
    type_id: number
    predicted_outcome: string
    /** Canonical outcome key passed to the selector (e.g. 'over', 'yes', '1X'). */
    canonical_outcome: string
    probability: number
    probability_gap: number
    /**
     * `null` when no canonical quote exists. Never 1, never 0, never a price
     * borrowed from a neighbouring market.
     */
    odds: number | null
    /** `null` whenever `odds` is null — EV is meaningless without a price. */
    expected_value: number | null
    market_score: number
    bookmaker?: string
    price_status: MarketPrice['status']
    odds_provenance: OddsProvenance | null
    odds_unavailable_reason?: OddsUnavailableReason
    raw_predictions: Record<string, number>
}

const MARKET_CONFIG: Record<ProductMarket, { name: string; display_name: string }> = {
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

/**
 * Score contribution of EV. An unavailable price contributes nothing — which is
 * numerically identical to the old placeholder path (`probability × 1 − 1` is
 * always negative and was clamped to 0), so market ordering is unchanged for
 * fixtures that never had a real quote.
 */
function scoreEV(ev: number | null): number {
    return ev === null ? 0 : Math.max(ev, 0)
}

/** Bookmaker name for display. Comes from provenance only — never guessed. */
function bookmakerLabel(price: MarketPrice): string | undefined {
    return price.status === 'verified' ? price.bookmaker.name ?? undefined : undefined
}

export async function getFixtureDetails(fixtureId: string) {
    // Fetch fixture from SportMonks
    const url = `https://api.sportmonks.com/v3/football/fixtures/${fixtureId}`
    const params_api = new URLSearchParams({
        api_token: getApiToken(),
        // `metadata` was requested but never read. `odds.bookmaker` is required:
        // without it provenance has no bookmaker name and every price would be
        // correctly classified unpublishable.
        include: 'participants;league;predictions;odds;odds.bookmaker',
        timezone: 'Europe/Bucharest'
    })

    const data = await apiClient.request(`${url}?${params_api}`)
    const fixture = data.data
    const evaluatedAt = new Date()

    if (!fixture) {
        return null
    }

    // Extract fixture data
    const homeTeam = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name || 'Home'
    const awayTeam = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name || 'Away'

    // Double Chance labels are team-named in real payloads ("Club Brugge or
    // Draw"), so the selector needs the participants to build its label set.
    const teamContext = { homeTeam, awayTeam }

    /**
     * ALL price selection on this path goes through here.
     *
     * Before 2026-08-03 this file carried its own market-ID constants, substring
     * matching and a maximum-across-bookmakers rule. It no longer decides
     * anything about market identity — `app/lib/oddsSelection.ts` owns that, and
     * `app/lib/marketPricing.ts` owns what a missing price means.
     */
    const price = (market: ProductMarket, outcome: string): MarketPrice =>
        priceMarket(fixture.odds, market, outcome, teamContext)

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

    /** Assemble one market entry from a probability view and a canonical price. */
    const buildMarket = (args: {
        market_type: ProductMarket
        type_id: number
        displayOutcome: string
        canonicalOutcome: string
        probability: number
        gap: number
        raw_predictions: Record<string, number>
    }): MarketPrediction => {
        const selected = price(args.market_type, args.canonicalOutcome)
        const ev = expectedValue(args.probability, selected)

        return {
            market_type: args.market_type,
            type_id: args.type_id,
            predicted_outcome: args.displayOutcome,
            canonical_outcome: args.canonicalOutcome,
            probability: args.probability,
            probability_gap: args.gap,
            odds: selected.status === 'verified' ? selected.odds : null,
            expected_value: ev,
            market_score: calculateMarketScore(args.gap, scoreEV(ev), args.probability),
            bookmaker: bookmakerLabel(selected),
            price_status: selected.status,
            odds_provenance: selected.status === 'verified' ? selected.provenance : null,
            odds_unavailable_reason:
                selected.status === 'unavailable' ? selected.unavailable_reason : undefined,
            raw_predictions: args.raw_predictions,
        }
    }

    /**
     * A market can only be *recommended* on the strength of a price we would
     * publish. With no canonical quote there is no EV, so it cannot qualify —
     * the same outcome the old `ev > 0` test produced for placeholder prices,
     * but now for the honest reason.
     */
    const qualifies = (m: MarketPrediction, minGap: number) =>
        m.expected_value !== null && m.expected_value > 0 && m.probability_gap >= minGap

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

        const marketData = buildMarket({
            market_type: '1x2',
            type_id: x12Predictions[0].type_id,
            displayOutcome: outcome,
            canonicalOutcome: outcome.toLowerCase(),
            probability: maxProb,
            gap,
            raw_predictions: { home: avgHome, draw: avgDraw, away: avgAway },
        })

        allMarketsData.push(marketData)
        if (qualifies(marketData, outcome === 'Draw' ? 0.15 : 0.12)) {
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
        const yesWins = yesProb > noProb

        const marketData = buildMarket({
            market_type: 'btts',
            type_id: 231,
            displayOutcome: yesWins ? 'BTTS Yes' : 'BTTS No',
            canonicalOutcome: yesWins ? 'yes' : 'no',
            probability: maxProb,
            gap,
            raw_predictions: { yes: yesProb, no: noProb },
        })

        allMarketsData.push(marketData)
        if (qualifies(marketData, 0.12)) {
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
        const overWins = overProb > underProb

        const marketData = buildMarket({
            market_type: 'over_under_2.5',
            type_id: 235,
            displayOutcome: overWins ? 'Over 2.5' : 'Under 2.5',
            canonicalOutcome: overWins ? 'over' : 'under',
            probability: maxProb,
            gap,
            raw_predictions: { over: overProb, under: underProb },
        })

        allMarketsData.push(marketData)
        if (qualifies(marketData, 0.12)) {
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

        const marketData = buildMarket({
            market_type: 'double_chance',
            type_id: 239,
            displayOutcome: outcome,
            canonicalOutcome: outcome,
            probability: maxProb,
            gap,
            raw_predictions: { '1X': homeOrDraw, 'X2': awayOrDraw, '12': homeOrAway },
        })

        allMarketsData.push(marketData)
        if (qualifies(marketData, 0.10)) {
            marketResults.push(marketData)
        }
    }

    // Sort and select best market
    allMarketsData.sort((a, b) => b.market_score - a.market_score)
    marketResults.sort((a, b) => b.market_score - a.market_score)
    const bestMarket = marketResults[0] || allMarketsData[0]

    // ============= 1X2 PRICE BOARD =============
    // The three-way board shown on the detail page. Each outcome is priced
    // independently through the canonical selector; an outcome without a
    // canonical quote stays null rather than borrowing another book's number.
    const boardPrices = {
        home: price('1x2', 'home'),
        draw: price('1x2', 'draw'),
        away: price('1x2', 'away'),
    }

    const boardOdds = (p: MarketPrice) => (p.status === 'verified' ? p.odds : null)
    const boardBook = (p: MarketPrice) => (p.status === 'verified' ? p.bookmaker.name : null)

    let oddsData: {
        home: number | null
        draw: number | null
        away: number | null
        bookmaker: string
        home_bookmaker: string | null
        draw_bookmaker: string | null
        away_bookmaker: string | null
        home_provenance: OddsProvenance | null
        draw_provenance: OddsProvenance | null
        away_provenance: OddsProvenance | null
        unavailable_reasons: Record<string, OddsUnavailableReason | undefined>
    } | null = null

    const anyBoardPrice =
        boardPrices.home.status === 'verified' ||
        boardPrices.draw.status === 'verified' ||
        boardPrices.away.status === 'verified'

    if (anyBoardPrice) {
        const namedBook =
            boardBook(boardPrices.home) || boardBook(boardPrices.draw) || boardBook(boardPrices.away)

        oddsData = {
            home: boardOdds(boardPrices.home),
            draw: boardOdds(boardPrices.draw),
            away: boardOdds(boardPrices.away),
            bookmaker: namedBook || 'Multiple bookmakers',
            home_bookmaker: boardBook(boardPrices.home),
            draw_bookmaker: boardBook(boardPrices.draw),
            away_bookmaker: boardBook(boardPrices.away),
            home_provenance:
                boardPrices.home.status === 'verified' ? boardPrices.home.provenance : null,
            draw_provenance:
                boardPrices.draw.status === 'verified' ? boardPrices.draw.provenance : null,
            away_provenance:
                boardPrices.away.status === 'verified' ? boardPrices.away.provenance : null,
            unavailable_reasons: {
                home: boardPrices.home.unavailable_reason,
                draw: boardPrices.draw.unavailable_reason,
                away: boardPrices.away.unavailable_reason,
            },
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

    if (predictionData) {
        // Determine predicted outcome (predictionData is now in percentage format)
        const probs = [predictionData.home, predictionData.draw, predictionData.away]
        const maxProb = Math.max(...probs)
        const maxIndex = probs.indexOf(maxProb)
        predictedOutcome = ['home', 'draw', 'away'][maxIndex] as 'home' | 'draw' | 'away'
        confidence = maxProb // Already a percentage

        // EV per outcome, expressed in percent. Only outcomes with a canonical
        // price get a number; the rest stay null and render nothing.
        const outcomeEV = (outcome: 'home' | 'draw' | 'away') => {
            const ev = expectedValue(predictionData![outcome] / 100, boardPrices[outcome])
            return ev === null ? null : ev * 100
        }

        evAnalysis.home = outcomeEV('home')
        evAnalysis.draw = outcomeEV('draw')
        evAnalysis.away = outcomeEV('away')

        const validEvs = ([
            { outcome: 'home' as const, ev: evAnalysis.home },
            { outcome: 'draw' as const, ev: evAnalysis.draw },
            { outcome: 'away' as const, ev: evAnalysis.away }
        ]).filter(v => v.ev !== null && v.ev > 0)

        if (validEvs.length > 0) {
            const bestBet = validEvs.reduce((max, current) => (current.ev! > max.ev!) ? current : max)
            evAnalysis.best_bet = bestBet.outcome
            evAnalysis.best_ev = bestBet.ev
        }

    }

    const serialiseMarket = (m: MarketPrediction) => ({
        type: m.market_type,
        name: MARKET_CONFIG[m.market_type].name,
        display_name: MARKET_CONFIG[m.market_type].display_name,
        predicted_outcome: m.predicted_outcome,
        canonical_outcome: m.canonical_outcome,
        probability: m.probability,
        probability_gap: m.probability_gap,
        odds: m.odds,
        expected_value: m.expected_value,
        market_score: m.market_score,
        bookmaker: m.bookmaker,
        price_status: m.price_status,
        odds_provenance: m.odds_provenance,
        odds_unavailable_reason: m.odds_unavailable_reason,
    })

    const probabilityVector = (market: ProductMarket): Record<string, number> =>
        allMarketsData.find((candidate) => candidate.market_type === market)?.raw_predictions ?? {}

    const intelligenceOutcome = (
        market: ProductMarket,
        key: string,
        label: string,
        providerProbability: number | null,
    ): IntelligenceOutcomeInput => {
        const selected = price(market, key)
        return {
            key,
            label,
            provider_probability: providerProbability,
            odds: selected.status === 'verified' ? selected.odds : null,
            bookmaker: selected.status === 'verified' ? selected.bookmaker.name : null,
            price_status: selected.status,
            odds_provenance: selected.status === 'verified' ? selected.provenance : null,
            odds_unavailable_reason:
                selected.status === 'unavailable' ? selected.unavailable_reason : undefined,
        }
    }

    const vector1x2 = probabilityVector('1x2')
    const vectorBtts = probabilityVector('btts')
    const vectorGoals = probabilityVector('over_under_2.5')
    const vectorDoubleChance = probabilityVector('double_chance')

    const intelligenceMarkets: IntelligenceMarketInput[] = [
        {
            key: '1x2',
            label: 'Match Result',
            probability_kind: 'distribution',
            outcomes: [
                intelligenceOutcome('1x2', 'home', 'Home', vector1x2.home ?? null),
                intelligenceOutcome('1x2', 'draw', 'Draw', vector1x2.draw ?? null),
                intelligenceOutcome('1x2', 'away', 'Away', vector1x2.away ?? null),
            ],
        },
        {
            key: 'btts',
            label: 'Both Teams to Score',
            probability_kind: 'distribution',
            outcomes: [
                intelligenceOutcome('btts', 'yes', 'Yes', vectorBtts.yes ?? null),
                intelligenceOutcome('btts', 'no', 'No', vectorBtts.no ?? null),
            ],
        },
        {
            key: 'over_under_2.5',
            label: 'Over/Under 2.5 Goals',
            probability_kind: 'distribution',
            outcomes: [
                intelligenceOutcome('over_under_2.5', 'over', 'Over 2.5', vectorGoals.over ?? null),
                intelligenceOutcome('over_under_2.5', 'under', 'Under 2.5', vectorGoals.under ?? null),
            ],
        },
        {
            key: 'double_chance',
            label: 'Double Chance',
            probability_kind: 'overlapping',
            outcomes: [
                intelligenceOutcome('double_chance', '1X', 'Home or Draw', vectorDoubleChance['1X'] ?? null),
                intelligenceOutcome('double_chance', 'X2', 'Draw or Away', vectorDoubleChance.X2 ?? null),
                intelligenceOutcome('double_chance', '12', 'Home or Away', vectorDoubleChance['12'] ?? null),
            ],
        },
    ]

    const intelligence = buildFixtureIntelligence(intelligenceMarkets, evaluatedAt)

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
            intelligence,
            has_predictions: x12Predictions.length > 0,
            has_odds: !!(fixture.odds && fixture.odds.length > 0),
            // Multi-market support for Explore section
            best_market: bestMarket ? serialiseMarket(bestMarket) : undefined,
            all_markets: allMarketsData.map(m => ({
                ...serialiseMarket(m),
                is_recommended: marketResults.some(r => r.market_type === m.market_type)
            }))
        },
        lastUpdated: evaluatedAt.toISOString()
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
