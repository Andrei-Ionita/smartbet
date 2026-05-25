import { Metadata } from 'next'
import ResponsibleGamblingContent from './ResponsibleGamblingContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Responsible Gambling',
  description: 'BetGlitch is committed to responsible gambling. Learn about our approach, self-exclusion tools, and find help resources for problem gambling.',
  openGraph: {
    title: 'Responsible Gambling | BetGlitch',
    description: 'Our commitment to responsible gambling. Resources and support for problem gambling.',
    url: 'https://betglitch.com/responsible-gambling',
  },
}

export default function ResponsibleGamblingPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Responsible Gambling', url: 'https://betglitch.com/responsible-gambling' },
      ]} />
      <ResponsibleGamblingContent />
    </>
  )
}
