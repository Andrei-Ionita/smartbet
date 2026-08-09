import { Metadata } from 'next'
import MonitoringContent from './MonitoringContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Signal research — what the current score gets right and wrong',
  description: 'Public research evidence for the BetGlitch signal score, including coverage, score separation, weaknesses and every graded legacy call.',
  openGraph: {
    title: 'Signal research | BetGlitch',
    description: 'What the current BetGlitch signal score gets right, gets wrong and has not yet proved.',
    url: 'https://betglitch.com/monitoring',
  },
}

export default function MonitoringPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Signal research', url: 'https://betglitch.com/monitoring' },
      ]} />
      <MonitoringContent />
    </>
  )
}
