import { Metadata } from 'next'
import BankrollContent from './BankrollContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Bankroll Management Calculator',
  description: 'Smart bankroll management tools for football betting. Calculate optimal stakes, track your betting balance, and manage risk with AI-powered insights.',
  openGraph: {
    title: 'Bankroll Management Calculator | BetGlitch',
    description: 'Smart bankroll management tools. Calculate optimal stakes and manage risk.',
    url: 'https://betglitch.com/bankroll',
  },
}

export default function BankrollPage() {
  return (
    <>
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Bankroll Management', url: 'https://betglitch.com/bankroll' },
      ]} />
      <BankrollContent />
    </>
  )
}
