import { Metadata } from 'next'
import TrackRecordContent from './TrackRecordContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Track Record — Transparent AI Prediction Results',
  description: 'Full transparency: see every prediction BetGlitch has ever made. Real results, real ROI, no cherry-picking. Updated daily with 27 European leagues.',
  openGraph: {
    title: 'Track Record — Transparent AI Prediction Results | BetGlitch',
    description: 'Every prediction we have ever made, verified and public. Real results, real ROI, updated daily.',
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
