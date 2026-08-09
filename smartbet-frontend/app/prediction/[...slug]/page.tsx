import { extractIdFromSlug, generateSchemaLD } from '@/src/utils/seo-helpers'
import { getFixtureDetails } from '@/src/services/fixtureService'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import PredictionContent from './PredictionContent'

interface PageProps {
  params: { slug: string[] }
}

async function getMatchData(slug: string[]) {
  const fixtureId = extractIdFromSlug(slug)
  if (!fixtureId) return null
  try {
    return await getFixtureDetails(fixtureId.toString())
  } catch (error) {
    console.error('Error fetching fixture intelligence:', error)
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const data = await getMatchData(params.slug)
  if (!data?.fixture) {
    return {
      title: 'Fixture analysis not found',
      description: 'The requested fixture analysis could not be found.',
    }
  }

  const { home_team, away_team, league } = data.fixture
  const title = `${home_team} vs ${away_team} — odds, probabilities & context`
  const description = `Explore ${home_team} vs ${away_team} in ${league}: provider probabilities, verified market prices, margin-removed market views, uncertainty and a personal fair-odds calculator.`

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: 'article',
      url: `https://betglitch.com/prediction/${params.slug.join('/')}`,
      section: 'Sports',
      tags: ['Football Analysis', 'Football Odds', home_team, away_team, league],
    },
    twitter: { card: 'summary_large_image', title, description },
  }
}

export default async function PredictionPage({ params }: PageProps) {
  const data = await getMatchData(params.slug)
  if (!data?.fixture?.intelligence) notFound()

  const { fixture } = data
  const jsonLd = generateSchemaLD(fixture)

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <main className="min-h-screen bg-slate-50 px-4 py-8">
        <PredictionContent fixture={fixture} lastUpdated={data.lastUpdated} />
      </main>
    </>
  )
}
