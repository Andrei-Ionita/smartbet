import { NextResponse } from 'next/server'
import { STRATEGIES } from '../../../lib/strategyLibrary'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(
  _request: Request,
  { params }: { params: { strategyKey: string } },
) {
  const known = STRATEGIES.some((strategy) => strategy.strategyKey === params.strategyKey)
  if (!known) {
    return NextResponse.json(
      { success: false, data: null, error: 'Unknown strategy.' },
      { status: 404 },
    )
  }

  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const strategyKey = encodeURIComponent(params.strategyKey)

  try {
    const response = await fetch(
      `${api}/api/transparency/strategies/${strategyKey}/current-fits/`,
      { cache: 'no-store', signal: AbortSignal.timeout(8000) },
    )
    if (!response.ok) throw new Error(`strategy fits API ${response.status}`)
    const body = await response.json()
    return NextResponse.json(body, {
      headers: { 'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=300' },
    })
  } catch (error) {
    console.error('strategy fits unavailable:', error)
    return NextResponse.json(
      { success: false, data: null, error: 'Current strategy fits are temporarily unavailable.' },
      { status: 503 },
    )
  }
}
