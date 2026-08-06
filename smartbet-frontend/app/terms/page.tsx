import { Metadata } from 'next'
import TermsContent from './TermsContent'

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'Terms of Service for BetGlitch. How our football market signals may be used, what they are not, and the risks of betting.',
}

export default function TermsPage() {
  return <TermsContent />
}
