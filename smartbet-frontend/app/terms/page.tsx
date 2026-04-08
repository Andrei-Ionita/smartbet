import { Metadata } from 'next'
import TermsContent from './TermsContent'

export const metadata: Metadata = {
  title: 'Terms of Service',
  description: 'Terms of Service for BetGlitch. Read our terms regarding the use of AI-powered football prediction services.',
}

export default function TermsPage() {
  return <TermsContent />
}
