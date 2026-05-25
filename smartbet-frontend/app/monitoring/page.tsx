import { Metadata } from 'next'
import MonitoringContent from './MonitoringContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Model Monitoring — AI Performance Dashboard',
  description: 'Real-time monitoring of BetGlitch AI prediction models. Track accuracy, calibration, and performance metrics across all leagues.',
  openGraph: {
    title: 'Model Monitoring — AI Performance Dashboard | BetGlitch',
    description: 'Real-time AI model performance monitoring. Track accuracy and calibration.',
    url: 'https://betglitch.com/monitoring',
  },
}

export default function MonitoringPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Model Monitoring', url: 'https://betglitch.com/monitoring' },
      ]} />
      <MonitoringContent />
    </>
  )
}
