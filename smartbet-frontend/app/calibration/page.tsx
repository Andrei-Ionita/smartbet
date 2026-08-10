import type { Metadata } from 'next'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import CalibrationContent from './CalibrationContent'

export const metadata: Metadata = {
  title: 'Probability calibration evidence',
  description:
    'See how BetGlitch probability vectors compare with confirmed football results, with a fixed pre-kickoff horizon, explicit sample limits and the underlying decision archive.',
  openGraph: {
    title: 'Probability calibration evidence | BetGlitch',
    description: 'Probability quality measured against confirmed results, including the evidence that is still too small to interpret.',
    url: 'https://betglitch.com/calibration',
  },
}

export default function CalibrationPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Calibration evidence', url: 'https://betglitch.com/calibration' },
      ]} />
      <CalibrationContent />
    </>
  )
}
