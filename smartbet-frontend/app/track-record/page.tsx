import { Metadata } from 'next'

import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import { PUBLIC_RESULTS_VISIBLE } from '@/app/lib/publicResultsMode'
import ResultsValidationContent from './ResultsValidationContent'
import UnifiedResultsContent from './UnifiedResultsContent'

export const metadata: Metadata = {
  title: PUBLIC_RESULTS_VISIBLE ? 'Results — homepage, strategies and Hidden Gems' : 'Results — engine validation in progress',
  description: PUBLIC_RESULTS_VISIBLE
    ? 'See every frozen BetGlitch homepage selection, named strategy and Hidden Gem, including pending selections, wins and losses.'
    : 'BetGlitch is validating its selection engine before beginning a new public performance record.',
  alternates: { canonical: '/track-record' },
  robots: PUBLIC_RESULTS_VISIBLE ? undefined : { index: false, follow: true },
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
      {PUBLIC_RESULTS_VISIBLE ? <UnifiedResultsContent /> : <ResultsValidationContent />}
    </>
  )
}
