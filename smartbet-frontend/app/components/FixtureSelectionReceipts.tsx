'use client'

import Link from 'next/link'
import useSWR from 'swr'
import { ScrollText } from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'
import { PUBLIC_RESULTS_VISIBLE } from '../lib/publicResultsMode'

interface Receipt {
  selection_id: string
  receipt_url: string
  predicted_outcome: string
  market_type: string
  odds: number
  status: string
}

const fetcher = async (url: string) => {
  const response = await fetch(url)
  if (!response.ok) throw new Error(String(response.status))
  return response.json()
}

export default function FixtureSelectionReceipts({ fixtureId }: { fixtureId: number }) {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const { data } = useSWR(PUBLIC_RESULTS_VISIBLE ? `/api/results-selections?fixture_id=${fixtureId}` : null, fetcher, {
    revalidateOnFocus: true, refreshInterval: 120_000, errorRetryCount: 1,
  })
  const receipts: Receipt[] = Array.isArray(data?.selections) ? data.selections : []
  if (!PUBLIC_RESULTS_VISIBLE || !receipts.length) return null

  return (
    <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50 p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <ScrollText className="mt-0.5 h-5 w-5 text-blue-700" />
        <div className="min-w-0 flex-1">
          <h2 className="font-black text-blue-950">{ro ? 'Selecții publicate pentru acest meci' : 'Published selections for this fixture'}</h2>
          <p className="mt-1 text-sm leading-6 text-blue-900">{ro ? 'Aceste selecții și cote au fost blocate înainte de start și rămân în Results indiferent de rezultat.' : 'These selections and prices were frozen before kickoff and remain in Results regardless of the outcome.'}</p>
          <div className="mt-4 grid gap-2">
            {receipts.map(receipt => (
              <Link key={receipt.selection_id} href={receipt.receipt_url} className="flex min-h-11 flex-wrap items-center justify-between gap-2 rounded-xl border border-blue-200 bg-white px-4 py-2 text-sm hover:border-blue-400">
                <span className="font-black text-slate-950">{receipt.predicted_outcome} · {receipt.odds.toFixed(2)}</span>
                <span className="font-bold text-blue-700">{ro ? 'Deschide recipisa' : 'Inspect receipt'} →</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
