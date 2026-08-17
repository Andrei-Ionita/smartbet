import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { STRATEGIES, STRATEGY_BY_SLUG } from '../../lib/strategyLibrary'
import StrategyDetailContent from './StrategyDetailContent'

export function generateStaticParams() {
  return STRATEGIES.map((strategy) => ({ slug: strategy.slug }))
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  const strategy = STRATEGY_BY_SLUG[params.slug]
  if (!strategy) return { title: 'Strategy not found' }
  const copy = strategy.copy.en
  return {
    title: `${copy.name} — mechanics, risks and evidence`,
    description: `${copy.summary} Learn settlement, break-even pricing, use cases, failure modes and BetGlitch's current evidence status.`,
    alternates: { canonical: `/strategies/${strategy.slug}` },
    openGraph: {
      title: `${copy.name}, explained | BetGlitch`,
      description: copy.summary,
      url: `https://www.betglitch.com/strategies/${strategy.slug}`,
    },
  }
}

export default function StrategyDetailPage({ params }: { params: { slug: string } }) {
  const strategy = STRATEGY_BY_SLUG[params.slug]
  if (!strategy) notFound()
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: `${strategy.copy.en.name}, explained`,
    description: strategy.copy.en.summary,
    author: { '@type': 'Organization', name: 'BetGlitch' },
    mainEntityOfPage: `https://www.betglitch.com/strategies/${strategy.slug}`,
  }
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      <StrategyDetailContent strategy={strategy} />
    </>
  )
}
