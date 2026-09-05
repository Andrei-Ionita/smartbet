'use client'
import MarketSelections from '../components/MarketSelections'
import { useLanguage } from '../contexts/LanguageContext'
export default function MarketsContent() {
  const { language } = useLanguage()
  return <main className="mx-auto max-w-7xl px-4 py-10 sm:px-8"><p className="text-xs font-bold uppercase tracking-widest text-blue-700">BetGlitch</p><h1 className="mt-2 text-4xl font-black">{language === 'ro' ? 'Găsește piața care te interesează' : 'Find the market that interests you'}</h1><MarketSelections language={language} /></main>
}
