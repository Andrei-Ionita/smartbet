import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// Simplified inline apiClient implementation
const apiClient = {
  async request(url: string) {
    const response = await fetch(url)
    return response.json()
  }
}

// Cache configuration
const CACHE_DURATION = {
  SEARCH: 5 * 60 * 1000, // 5 minutes - search results can change frequently
  FIXTURES: 15 * 60 * 1000 // 15 minutes - fixture data is more stable
}

// In-memory cache store
const cache = new Map<string, { data: any; timestamp: number; duration: number }>()

// Cache utility functions
function getCacheKey(endpoint: string, params: Record<string, any> = {}): string {
  const sortedParams = Object.keys(params).sort().reduce((result, key) => {
    result[key] = params[key]
    return result
  }, {} as Record<string, any>)
  return `${endpoint}:${JSON.stringify(sortedParams)}`
}

function getFromCache(key: string): any | null {
  const cached = cache.get(key)
  if (!cached) return null

  const now = Date.now()
  if (now - cached.timestamp > cached.duration) {
    cache.delete(key)
    return null
  }

  return cached.data
}

function setCache(key: string, data: any, duration: number): void {
  cache.set(key, {
    data,
    timestamp: Date.now(),
    duration
  })
}

// Helper function to get API token (will be called at request time, not build time)
function getApiToken(): string {
  const token = process.env.SPORTMONKS_API_TOKEN
  if (!token) {
    throw new Error('SPORTMONKS_API_TOKEN environment variable is not set')
  }
  return token
}

// All 27 leagues covered by subscription
const SUPPORTED_LEAGUE_IDS = [
  8,     // Premier League
  9,     // Championship
  24,    // FA Cup
  27,    // Carabao Cup
  72,    // Eredivisie
  82,    // Bundesliga
  181,   // Admiral Bundesliga
  208,   // Pro League
  244,   // 1. HNL
  271,   // Superliga
  301,   // Ligue 1
  384,   // Serie A
  387,   // Serie B
  390,   // Coppa Italia
  444,   // Eliteserien
  453,   // Ekstraklasa
  462,   // Liga Portugal
  486,   // Russian Premier League
  501,   // Premiership
  564,   // La Liga
  567,   // La Liga 2
  570,   // Copa Del Rey
  573,   // Allsvenskan
  591,   // Super League
  600,   // Super Lig
  609,   // Premier League (additional)
  1371,  // UEFA Europa League Play-offs
]

interface SearchResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  has_predictions: boolean
  has_odds: boolean
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q') || ''
    const league = searchParams.get('league') || ''
    const limit = parseInt(searchParams.get('limit') || '20')
    const mode = searchParams.get('mode') || 'search' // 'search' or 'browse'

    // Require either a search query OR a league selection
    if (!query.trim() && !league) {
      return NextResponse.json({
        results: [],
        total: 0,
        message: 'Please enter a search query or select a league'
      })
    }

    console.log(`🔍 Searching for: "${query}" - using real SportMonks data only`)

    // Only use real SportMonks data - no test data fallback
    const token = process.env.SPORTMONKS_API_TOKEN
    if (!token) {
      console.error('❌ SPORTMONKS_API_TOKEN not found in environment')
      return NextResponse.json({
        results: [],
        total: 0,
        query: query,
        league: league,
        message: 'API configuration error - no real data available'
      }, { status: 500 })
    }

    console.log('✅ Using real SportMonks data only - no test data')

    // Calculate date range for next 14 days
    const now = new Date()
    const fourteenDaysFromNow = new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000)
    const startDate = now.toISOString().split('T')[0]
    const endDate = fourteenDaysFromNow.toISOString().split('T')[0]

    console.log(`📅 Searching fixtures between ${startDate} and ${endDate}`)

    // Check cache first
    const cacheKey = getCacheKey('search', { query, league, startDate, endDate })
    const cachedResults = getFromCache(cacheKey)
    if (cachedResults) {
      console.log(`💾 Returning cached search results for "${query}"`)
      return NextResponse.json(cachedResults)
    }

    // Filter leagues if specific league requested
    const leaguesToSearch = league
      ? SUPPORTED_LEAGUE_IDS.filter(id => id === parseInt(league))
      : SUPPORTED_LEAGUE_IDS

    console.log(`🔍 Searching ${leaguesToSearch.length} leagues for "${query}"`)

    const allResults: SearchResult[] = []

    // Search leagues in order, stop early if we have enough results
    for (const leagueId of leaguesToSearch) {
      // Early termination if we already have plenty of results
      if (allResults.length >= limit * 2) {
        console.log(`⚡ Early termination - found ${allResults.length} results`)
        break
      }
      try {
        const url = `https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`
        const params = new URLSearchParams({
          api_token: token,
          include: 'participants;league;metadata;predictions;odds',
          filters: `fixtureLeagues:${leagueId}`,
          per_page: '50',
          page: '1',
          timezone: 'Europe/Bucharest'
        })

        const data = await apiClient.request(`${url}?${params}`)
        const fixtures = data.data || []

        // Filter fixtures by search query (only if query exists)
        const matchingFixtures = query.trim()
          ? fixtures.filter((fixture: any) => {
            const homeTeam = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name?.toLowerCase() || ''
            const awayTeam = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name?.toLowerCase() || ''
            const searchTerm = query.toLowerCase()

            return homeTeam.includes(searchTerm) || awayTeam.includes(searchTerm)
          })
          : fixtures // Browse mode: return all fixtures for the league

        // Convert to search results
        const results = matchingFixtures.map((fixture: any) => {
          const homeTeam = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name || 'Home'
          const awayTeam = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name || 'Away'

          return {
            fixture_id: fixture.id,
            home_team: homeTeam,
            away_team: awayTeam,
            league: fixture.league?.name || 'Unknown',
            kickoff: fixture.starting_at,
            has_predictions: (fixture.predictions?.length || 0) > 0,
            has_odds: (fixture.odds?.length || 0) > 0
          }
        })

        allResults.push(...results)

        if (results.length > 0) {
          console.log(`  ✅ League ${leagueId}: Found ${results.length} matching fixtures`)
        }

      } catch (error) {
        console.log(`  ❌ League ${leagueId}: ${error}`)
      }
    }

    // Sort by kickoff time (earliest first)
    allResults.sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime())

    const responseData = {
      results: allResults.slice(0, limit),
      total: allResults.length,
      query: query,
      league: league,
      mode: query.trim() ? 'search' : 'browse',
      message: allResults.length > 0
        ? query.trim()
          ? `Found ${allResults.length} fixtures matching "${query}"`
          : `Found ${allResults.length} upcoming fixtures`
        : query.trim()
          ? `No fixtures found matching "${query}" in the next 14 days`
          : `No upcoming fixtures found for this league`
    }

    // Cache the results for 5 minutes
    setCache(cacheKey, responseData, CACHE_DURATION.SEARCH)

    console.log(`✅ Returning ${responseData.results.length} fixtures (cached)`)
    return NextResponse.json(responseData)

  } catch (error) {
    console.error('Error in search API:', error)
    return NextResponse.json(
      { error: 'Failed to search fixtures' },
      { status: 500 }
    )
  }
}
