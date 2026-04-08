import { Metadata } from 'next'
import PricingContent from './PricingContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Pricing Plans',
  description: 'Choose your BetGlitch plan. Get AI-powered football predictions, value bet alerts, and premium analytics tools. Start free, upgrade when ready.',
  openGraph: {
    title: 'Pricing Plans | BetGlitch',
    description: 'AI-powered football predictions and premium analytics. Start free.',
    url: 'https://betglitch.com/pricing',
  },
}

export default function PricingPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Pricing', url: 'https://betglitch.com/pricing' },
      ]} />
      <PricingContent />
    </>
  )
}
