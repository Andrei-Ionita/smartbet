import { Metadata } from 'next'

import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import { PAYMENTS_ENABLED } from '@/app/lib/commercialMode'

import BetaContent from './BetaContent'
import PricingContent from './PricingContent'

/**
 * While payments are disabled this route serves the public-beta information
 * page. The pricing table is NOT reachable by any direct URL — the component is
 * preserved, dormant, and returns the moment the flag flips back.
 */
const betaMetadata: Metadata = {
  title: 'Public Beta — free access',
  description:
    'BetGlitch is currently in public beta. Access is free while we build and '
    + 'build the public results.',
  openGraph: {
    title: 'BetGlitch Public Beta — free access',
    description:
      'Free while we build the public results. Every published pick is locked '
      + 'before kickoff and remains visible after '
      + 'settlement—win or lose.',
    url: 'https://www.betglitch.com/pricing',
  },
}

const pricingMetadata: Metadata = {
  title: 'Pricing Plans',
  description: 'Choose your BetGlitch plan. Transparent football signals, published picks and public results. Start free, upgrade when ready.',
  openGraph: {
    title: 'Pricing Plans | BetGlitch',
    description: 'Transparent football signals, published picks and public results. Start free.',
    url: 'https://www.betglitch.com/pricing',
  },
}

export const metadata: Metadata = PAYMENTS_ENABLED ? pricingMetadata : betaMetadata

export default function PricingPage() {
  const label = PAYMENTS_ENABLED ? 'Pricing' : 'Public Beta'

  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://www.betglitch.com' },
        { name: label, url: 'https://www.betglitch.com/pricing' },
      ]} />
      {PAYMENTS_ENABLED ? <PricingContent /> : <BetaContent />}
    </>
  )
}
