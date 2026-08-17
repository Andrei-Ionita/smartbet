import { NextRequest, NextResponse } from 'next/server'
import { FixtureProviderTimeoutError, getFixtureDetails } from '@/src/services/fixtureService'

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

    return NextResponse.json(data, {
      headers: {
        // Fixture prices remain fresh while repeat opens avoid rebuilding the
        // same workspace on every click.
        'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=60',
      },
    })

  } catch (error: any) {
    console.error('API Error:', error)
    const timedOut = error instanceof FixtureProviderTimeoutError ||
      error?.name === 'FixtureProviderTimeoutError' ||
      error?.name === 'AbortError'
    return NextResponse.json(
      {
        error: timedOut
          ? 'The fixture data provider did not respond in time'
          : 'The fixture workspace is temporarily unavailable',
        status: timedOut ? 'timeout' : 'provider_error',
      },
      { status: timedOut ? 504 : 502 }
    )
  }
}
