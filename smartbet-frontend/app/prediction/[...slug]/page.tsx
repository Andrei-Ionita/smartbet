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
            title: 'Match Prediction Not Found | OddsMind',
            description: 'The requested match prediction could not be found.'
        }
    }

    const { home_team, away_team, league, prediction_confidence, predicted_outcome } = data.fixture
    const confidence = Math.round(prediction_confidence * 100)

    const title = `${home_team} vs ${away_team} Prediction, Stats & Odds | OddsMind`
    const description = `AI betting prediction for ${home_team} vs ${away_team} in ${league}. Our model predicts ${predicted_outcome} with ${confidence}% confidence. Get full stats and value analysis.`

    return {
        title,
        description,
        openGraph: {
            title,
            description,
            type: 'article',
            url: `https://oddsmind.io/prediction/${params.slug.join('/')}`,
            section: 'Sports',
            tags: ['Football Prediction', 'Betting Tips', home_team, away_team, league]
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

    // Transform to Recommendation type
    // Ensure predicted_outcome is capitalized to match Recommendation type
    const outcome = fixture.predicted_outcome.charAt(0).toUpperCase() + fixture.predicted_outcome.slice(1)

    const recommendation: Recommendation = {
        ...fixture,
        predicted_outcome: outcome as 'Home' | 'Draw' | 'Away',
        confidence: fixture.prediction_confidence,
        // Map odds from best market or odds_data
        odds: fixture.best_market?.odds ||
            (outcome === 'Home' ? fixture.odds_data?.home :
                outcome === 'Draw' ? fixture.odds_data?.draw :
                    fixture.odds_data?.away) || null,
        ev: fixture.best_market?.expected_value || fixture.ev_analysis?.best_ev || null,
        score: fixture.best_market?.market_score || 0, // Fallback
        explanation: `AI prediction for ${fixture.home_team} vs ${fixture.away_team} favoring ${outcome}.`,
        odds_data: fixture.odds_data ? {
            ...fixture.odds_data,
            bookmaker: fixture.odds_data.bookmaker || 'Unknown'
        } : undefined,
        market_indicators: fixture.market_indicators || undefined
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
                />
            </div>
        </>
    )
}
