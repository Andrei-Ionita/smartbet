import { Metadata } from 'next'
import DisclaimerContent from './DisclaimerContent'

export const metadata: Metadata = {
  title: 'Disclaimer',
  description: 'Important disclaimer for BetGlitch. We are not a bookmaker and do not accept bets. Our signals are informational only and no output guarantees profit.',
}

export default function DisclaimerPage() {
  return <DisclaimerContent />
}
