import { Metadata } from 'next'
import DisclaimerContent from './DisclaimerContent'

export const metadata: Metadata = {
  title: 'Disclaimer',
  description: 'Important disclaimer for BetGlitch. We are not a betting operator. Predictions are for informational purposes only.',
}

export default function DisclaimerPage() {
  return <DisclaimerContent />
}
