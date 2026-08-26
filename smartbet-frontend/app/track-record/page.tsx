import { Metadata } from 'next'

import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import UnifiedResultsContent from './UnifiedResultsContent'

export const metadata: Metadata = {
  title: 'Results — homepage, strategies and Hidden Gems',
  description:
    'See every frozen BetGlitch homepage selection, named strategy and Hidden Gem, including pending selections, wins and losses.',
  alternates: { canonical: '/track-record' },
  openGraph: {
    title: 'Complete BetGlitch Results',
    description:
      'Separate, complete records for homepage selections, named strategies and Hidden Gems.',
    url: 'https://www.betglitch.com/track-record',
  },
}

export default function TrackRecordPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://www.betglitch.com' },
        { name: 'Results', url: 'https://www.betglitch.com/track-record' },
      ]} />
      <UnifiedResultsContent />
    </>
  )
}
