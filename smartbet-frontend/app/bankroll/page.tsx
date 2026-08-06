import { Metadata } from 'next'
import BankrollContent from './BankrollContent'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Bankroll Management Calculator',
  description: 'Track your own betting balance and apply a fixed-percentage rule to a bankroll you set. BetGlitch does not size stakes from a signal score and does not tell you to bet.',
  openGraph: {
    title: 'Bankroll Management Calculator | BetGlitch',
    description: 'Track your own betting balance against a bankroll you set. BetGlitch does not size stakes for you.',
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
