import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET() {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  try {
    const response = await fetch(`${api}/api/transparency/calibration/`, {
      cache: 'no-store',
    })
    const body = await response.json()
    return NextResponse.json(body, { status: response.status })
  } catch (error) {
    console.error('calibration evidence unavailable:', error)
    return NextResponse.json(
      { success: false, error: 'Calibration evidence is temporarily unavailable.' },
      { status: 503 },
    )
  }
}
