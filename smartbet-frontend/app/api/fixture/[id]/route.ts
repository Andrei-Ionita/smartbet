import { NextRequest, NextResponse } from 'next/server'
import { getFixtureDetails } from '@/src/services/fixtureService'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const fixtureId = params.id

    if (!fixtureId) {
      return NextResponse.json(
        { error: 'Fixture ID is required' },
        { status: 400 }
      )
    }

    const data = await getFixtureDetails(fixtureId)

    if (!data) {
      return NextResponse.json(
        { error: 'Fixture not found' },
        { status: 404 }
      )
    }

    return NextResponse.json(data)

  } catch (error: any) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal Server Error' },
      { status: 500 }
    )
  }
}