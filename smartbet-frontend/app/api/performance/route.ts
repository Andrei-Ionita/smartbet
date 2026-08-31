import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/** Compatibility endpoint backed only by the immutable selection ledger. */
export async function GET() {
  const api = (process.env.DJANGO_API_URL
    || process.env.NEXT_PUBLIC_API_URL
    || 'https://api.betglitch.com').replace(/\/$/, '')

  try {
    const response = await fetch(`${api}/api/results/selections/`, {
      cache: 'no-store', signal: AbortSignal.timeout(8000),
    })
    if (!response.ok) throw new Error(`selection ledger ${response.status}`)
    const body = await response.json()
    const summary = body?.performance?.overall
    if (!summary || typeof summary.settled !== 'number') {
      throw new Error('selection ledger omitted performance summary')
    }
    return NextResponse.json({
      success: true,
      data: {
        overall: { ...summary, total_predictions: summary.settled },
        cohorts: body.performance,
      },
      source: 'immutable_public_selection_ledger',
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error('performance ledger unavailable:', error)
    return NextResponse.json({
      success: false,
      error: 'Public selection results are temporarily unavailable.',
      data: null,
    }, { status: 503 })
  }
}
