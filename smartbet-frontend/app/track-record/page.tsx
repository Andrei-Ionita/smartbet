import { Metadata } from 'next'
import TrackRecordContent from './TrackRecordContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

// The previous metadata promised a complete history of all predictions and a
// realized return figure. Neither is true: only published picks enter the
// record, and the record restarted at the pricing-integrity cutoff. Metadata
// must not claim a history the verified record does not contain.
export const metadata: Metadata = {
  title: 'Results — published picks locked before kickoff',
  description:
    'BetGlitch publishes and locks selected picks before kickoff, then keeps every settled result visible—win or lose.',
  openGraph: {
    title: 'Results — published picks locked before kickoff | BetGlitch',
    description:
      'Picks locked before kickoff, results published after full-time. Wins and losses both stay public.',
    url: 'https://betglitch.com/track-record',
  },
}

export default function TrackRecordPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Results', url: 'https://betglitch.com/track-record' },
      ]} />
      <TrackRecordContent />
    </>
  )
}
