import { Metadata } from 'next'
import MonitoringContent from './MonitoringContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Signal Monitoring — pipeline health',
  description: 'Operational monitoring of the BetGlitch signal pipeline. Track ingestion, settlement and coverage across covered competitions.',
  openGraph: {
    title: 'Signal Monitoring — pipeline health | BetGlitch',
    description: 'Operational monitoring of the BetGlitch signal pipeline.',
    url: 'https://betglitch.com/monitoring',
  },
}

export default function MonitoringPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Signal monitoring', url: 'https://betglitch.com/monitoring' },
      ]} />
      <MonitoringContent />
    </>
  )
}
