import { Metadata } from 'next'
import TrackRecordContent from './TrackRecordContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

// The previous metadata promised a complete history of all predictions and a
// realized return figure. Neither is true: only published picks enter the
// record, and the record restarted at the pricing-integrity cutoff. Metadata
// must not claim a history the verified record does not contain.
export const metadata: Metadata = {
  title: 'Verified record — public commitments and settled results',
  description:
    'BetGlitch commits selected signals to the public record before kickoff with their recorded odds and bookmaker, then publishes the result—win or lose. Only eligible settled commitments count towards this record.',
  openGraph: {
    title: 'Verified record — public commitments and settled results | BetGlitch',
    description:
      'Signals committed before kickoff, results published after full-time. Wins and losses both stay public.',
    url: 'https://betglitch.com/track-record',
  },
}

export default function TrackRecordPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Track Record', url: 'https://betglitch.com/track-record' },
      ]} />
      <TrackRecordContent />
    </>
  )
}
