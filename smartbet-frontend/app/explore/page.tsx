import { Metadata } from 'next'
import ExploreContent from './ExploreContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

// Terminology-aligned. The page heading became "Explore live football signals"
// during the first-impression phase, but the metadata still used the old
// marketing vocabulary, so search results and link previews described a
// different product from the one that actually loads.
export const metadata: Metadata = {
  title: 'Explore live football signals',
  description:
    'Browse current live signals across the European competitions BetGlitch covers. Live signals can change before kickoff and are not part of the verified record unless BetGlitch publishes them as an immutable pick.',
  openGraph: {
    title: 'Explore live football signals | BetGlitch',
    description:
      'Current live signals across the European competitions BetGlitch covers. Live signals can change before kickoff; only public commitments can enter the verified record.',
    url: 'https://betglitch.com/explore',
  },
}

export default function ExplorePage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Explore signals', url: 'https://betglitch.com/explore' },
      ]} />
      <ExploreContent />
    </>
  )
}
