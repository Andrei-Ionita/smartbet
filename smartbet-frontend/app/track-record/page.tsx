import { Metadata } from 'next'

import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import PortfolioResultsContent from './PortfolioResultsContent'

export const metadata: Metadata = {
  title: 'Results — market selections and homepage record',
  description: 'Every published selection from the current market engine, with frozen prices, pending results, wins and losses. Homepage selections reuse the same receipts.',
  alternates: { canonical: '/track-record' },
  openGraph: {
    title: 'Complete BetGlitch Results',
    description:
      'One record across markets, with a separately viewable homepage subset.',
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
      <PortfolioResultsContent />
    </>
  )
}
