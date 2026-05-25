import { Metadata } from 'next'
import PrivacyContent from './PrivacyContent'

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'BetGlitch Privacy Policy. Learn how we collect, use, and protect your personal information.',
}

export default function PrivacyPage() {
  return <PrivacyContent />
}
