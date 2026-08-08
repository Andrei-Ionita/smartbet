import { extractIdFromSlug, generateSchemaLD } from '@/src/utils/seo-helpers'
import { getFixtureDetails } from '@/src/services/fixtureService'
import { notFound } from 'next/navigation'
import { Metadata } from 'next'
import PredictionContent from './PredictionContent'
import { Recommendation } from '@/src/types/recommendation'

interface PageProps {
    params: {
        slug: string[]
    }
}

// Function to fetch data - shared between page and metadata
async function getMatchData(slug: string[]) {
    const fixtureId = extractIdFromSlug(slug)
    if (!fixtureId) return null

    try {
        const data = await getFixtureDetails(fixtureId.toString())
        return data
    } catch (error) {
        console.error('Error fetching match data:', error)
        return null
    }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const data = await getMatchData(params.slug)

    if (!data || !data.fixture) {
        return {
            title: 'Match Prediction Not Found | BetGlitch',
            description: 'The requested match prediction could not be found.'
        }
    }

    const { home_team, away_team, league } = data.fixture

    // THE signal is the best market's selection, not the 1X2 leg.
    //
    // This generator (and the page mapper below) used to read the fixture's
    // 1X2 fields while the price and the "Best: BTTS" chip came from
    // best_market — so a BTTS-led fixture headlined "Home — 50" next to a
    // BTTS price. A reviewer read that as unreliable data, and they were
    // right to: one page was presenting two markets as one signal.
    const bestMarket = data.fixture.best_market
    const headlineOutcome = bestMarket?.predicted_outcome
        ?? data.fixture.predicted_outcome
    const headlineScore = Math.round(
        (bestMarket
            ? bestMarket.probability
            : data.fixture.prediction_confidence) * 100,
    )
    const marketName = bestMarket?.display_name ?? 'Match Result'

    const title = `${home_team} vs ${away_team} — signal, stats & odds | BetGlitch`
    const description = `BetGlitch's live signal for ${home_team} vs ${away_team} in ${league}. ${headlineOutcome} (${marketName}) is the highest-ranked outcome, signal score ${headlineScore} / 100 — a relative ranking, not a calibrated probability.`

    return {
        title,
        description,
        openGraph: {
            title,
            description,
            type: 'article',
            url: `https://betglitch.com/prediction/${params.slug.join('/')}`,
            section: 'Sports',
            tags: ['Football Signal', home_team, away_team, league]
        },
        twitter: {
            card: 'summary_large_image',
            title,
            description,
        }
    }
}

export default async function PredictionPage({ params }: PageProps) {
    const data = await getMatchData(params.slug)

    if (!data || !data.fixture) {
        notFound()
    }

    const { fixture } = data

    // Transform to Recommendation type.
    //
    // LEAD WITH THE BEST MARKET — the same rule the recommendations route
    // follows. The old mapper took `predicted_outcome`/`prediction_confidence`
    // from the fixture's 1X2 fields while odds/provenance came from
    // best_market, so this page could headline "Home — 50" for a fixture whose
    // actual signal was "BTTS Yes — 52". The Explorer and this page must never
    // disagree about what THE signal is.
    const outcome1x2 = fixture.predicted_outcome.charAt(0).toUpperCase() + fixture.predicted_outcome.slice(1)
    const outcome = fixture.best_market?.predicted_outcome ?? outcome1x2

    const recommendation: Recommendation = {
        ...fixture,
        predicted_outcome: outcome as Recommendation['predicted_outcome'],
        // best_market.probability is already 0-1; the legacy 1X2 fallback is a
        // percentage (e.g. 59.69) and keeps its normalization.
        confidence: fixture.best_market
            ? fixture.best_market.probability
            : (fixture.prediction_confidence > 1
                ? fixture.prediction_confidence / 100
                : fixture.prediction_confidence),
        // Price and its canonical status travel together. The card decides what
        // to render from `price_status` + provenance, never from the number.
        odds: fixture.best_market?.odds ?? null,
        price_status: fixture.best_market?.price_status,
        odds_provenance: fixture.best_market?.odds_provenance ?? null,
        odds_unavailable_reason: fixture.best_market?.odds_unavailable_reason,
        // Normalize EV: same normalization as confidence
        ev: (() => {
            const rawEv = fixture.best_market?.expected_value ?? fixture.ev_analysis?.best_ev ?? null;
            if (rawEv === null) return null;
            // If EV is greater than 1, it's likely in percentage format (e.g., 12.2 for 12.2%)
            // Convert to decimal (0.122)
            return rawEv > 1 ? rawEv / 100 : rawEv;
        })(),
        score: fixture.best_market?.market_score || 0, // Fallback
        explanation: `Live signal for ${fixture.home_team} vs ${fixture.away_team}: ${outcome} is the highest-ranked outcome.`,
        // market_indicators is dead weight the card no longer reads; nulled
        // rather than spread through from the fixture payload.
        market_indicators: undefined,
        odds_data: fixture.odds_data ? {
            ...fixture.odds_data,
            bookmaker: fixture.odds_data.bookmaker || 'Unknown'
        } : undefined,
    }

    const jsonLd = generateSchemaLD(fixture)

    return (
        <>
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
            />

            <div className="min-h-screen bg-gray-50 py-8 px-4">
                <PredictionContent
                    recommendation={recommendation}
                    leagueName={fixture.league}
                    homeTeam={fixture.home_team}
                    awayTeam={fixture.away_team}
                    kickoff={fixture.kickoff}
                    lastUpdated={new Date().toISOString()}
                />
            </div>
        </>
    )
}
