import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

import { PUBLIC_RESULTS_VISIBLE } from '@/app/lib/publicResultsMode'
import SelectionReceiptContent, { type PublicSelectionReceipt } from './SelectionReceiptContent'

const API_URL = (process.env.DJANGO_API_URL
  || process.env.NEXT_PUBLIC_API_URL
  || 'https://api.betglitch.com').replace(/\/$/, '')

async function getReceipt(selectionId: string): Promise<PublicSelectionReceipt | null> {
  if (!/^[0-9a-f-]{36}$/i.test(selectionId)) return null
  try {
    const response = await fetch(`${API_URL}/api/results/selections/${selectionId}/`, {
      cache: 'no-store', signal: AbortSignal.timeout(8000),
    })
    if (!response.ok) return null
    const body = await response.json()
    return body?.selection ?? null
  } catch {
    return null
  }
}

export async function generateMetadata(
  { params }: { params: { selectionId: string } },
): Promise<Metadata> {
  const selection = await getReceipt(params.selectionId)
  if (!selection) return { title: 'Selection receipt not found · BetGlitch' }
  const title = `${selection.home_team} vs ${selection.away_team} — public selection receipt`
  const description = `Published before kickoff: ${selection.predicted_outcome} at ${selection.odds.toFixed(2)}. Original terms remain permanently visible.`
  return {
    title, description,
    alternates: { canonical: selection.receipt_url },
    robots: PUBLIC_RESULTS_VISIBLE ? undefined : { index: false, follow: false },
    openGraph: { title, description, type: 'article', url: `https://www.betglitch.com${selection.receipt_url}` },
  }
}

export default async function PublicSelectionReceiptPage(
  { params }: { params: { selectionId: string } },
) {
  const selection = await getReceipt(params.selectionId)
  if (!selection) notFound()
  return <SelectionReceiptContent selection={selection} />
}
