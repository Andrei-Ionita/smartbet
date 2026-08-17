import type { Metadata } from 'next'
import StrategiesContent from './StrategiesContent'

export const metadata: Metadata = {
  title: 'Football betting strategies — explained and tested',
  description: 'Understand football betting markets, settlement, break-even prices and failure modes. Follow which strategies BetGlitch is testing without treating hypotheses as guarantees.',
  alternates: { canonical: '/strategies' },
  openGraph: {
    title: 'Football betting strategies — explained and tested | BetGlitch',
    description: 'A practical strategy library with mechanics, risks, examples and transparent evidence status.',
    url: 'https://www.betglitch.com/strategies',
  },
}

export default function StrategiesPage() {
  return <StrategiesContent />
}
