import { Metadata } from 'next'
import ExploreContent from './ExploreContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Explore AI Football Predictions',
  description: 'Browse AI-powered football predictions across 27 European leagues. Get match analysis, value bets, and statistical insights for upcoming fixtures.',
  openGraph: {
    title: 'Explore AI Football Predictions | BetGlitch',
    description: 'Browse AI-powered football predictions across 27 European leagues. Match analysis, value bets, and statistical insights.',
    url: 'https://betglitch.com/explore',
  },
}

export default function ExplorePage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Explore Predictions', url: 'https://betglitch.com/explore' },
      ]} />
      <ExploreContent />
    </>
  )
}
