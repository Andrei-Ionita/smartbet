import { Metadata } from 'next'
import ExploreContent from './ExploreContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Explore football odds, probabilities and fixture context',
  description:
    'Search any covered football fixture, compare provider probabilities with margin-removed market prices, inspect uncertainty and calculate your own fair odds.',
  openGraph: {
    title: 'Explore football decision intelligence | BetGlitch',
    description:
      'A decision workspace for any covered fixture: probabilities, verified odds, market context, uncertainty and your own fair price.',
    url: 'https://betglitch.com/explore',
  },
}

export default function ExplorePage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Explore fixtures', url: 'https://betglitch.com/explore' },
      ]} />
      <ExploreContent />
    </>
  )
}
