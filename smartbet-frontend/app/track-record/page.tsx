import { Metadata } from 'next'

import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import TrackRecordContent from './TrackRecordContent'

export const metadata: Metadata = {
  title: 'Current Gem strategy results',
  description:
    'See every Gem published by the current BetGlitch strategy and how each locked selection settled, win or lose.',
  alternates: { canonical: '/track-record' },
  openGraph: {
    title: 'Current Gem strategy results | BetGlitch',
    description:
      'One current strategy, one complete published record, with earlier methodologies kept separately.',
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
      <TrackRecordContent />
    </>
  )
}
