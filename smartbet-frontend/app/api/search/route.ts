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
  486,   // Premier League (Romanian)
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

    if (!query.trim()) {
      return NextResponse.json({
        results: [],
        total: 0,
        message: 'Please enter a search query'
      })
    }

    // Check cache first
    const cacheKey = getCacheKey('search', { query, league, limit })
    const cachedData = getFromCache(cacheKey)
    if (cachedData) {
      console.log(`🎯 Cache HIT for search: "${query}"`)
      return NextResponse.json(cachedData)
    }

    console.log(`🚀 Cache MISS - Searching for: "${query}"`)

    // Calculate date range for next 3 days (minimal for fast search)
    const now = new Date()
    const threeDaysFromNow = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000)
    const startDate = now.toISOString().split('T')[0]
    const endDate = threeDaysFromNow.toISOString().split('T')[0]

    console.log(`Searching for: "${query}" in league: "${league}"`)

    // Search through all leagues or specific league (keeping all 27 leagues)
    const leaguesToSearch = league ? [parseInt(league)] : SUPPORTED_LEAGUE_IDS
    const allResults: SearchResult[] = []
    
    // Add timeout protection for search
    const searchStartTime = Date.now()
    const MAX_SEARCH_TIME = 8000 // 8 seconds max

    for (const leagueId of leaguesToSearch) {
      // Check if we're taking too long
      if (Date.now() - searchStartTime > MAX_SEARCH_TIME) {
        console.log(`Search timeout reached, stopping at league ${leagueId}`)
        break
      }
      try {
        const url = `https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`
        const params = new URLSearchParams({
          api_token: getApiToken(),
          include: 'participants;league;metadata;predictions;odds',
          filters: `fixtureLeagues:${leagueId}`,
          per_page: '50',
          page: '1',
          timezone: 'Europe/Bucharest'
        })

        const data = await apiClient.request(`${url}?${params}`)
        const fixtures = data.data || []

        // Filter fixtures by search query
        const matchingFixtures = fixtures.filter((fixture: any) => {
          // Correctly map home/away teams using meta.location
          const homeTeam = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name?.toLowerCase() || ''
          const awayTeam = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name?.toLowerCase() || ''
          const leagueName = fixture.league?.name?.toLowerCase() || ''
          const searchTerm = query.toLowerCase()

          return homeTeam.includes(searchTerm) || 
                 awayTeam.includes(searchTerm) || 
                 leagueName.includes(searchTerm) ||
                 `${homeTeam} vs ${awayTeam}`.includes(searchTerm)
        })

        // Convert to search results
        const results = matchingFixtures.map((fixture: any) => {
          // Correctly map home/away teams using meta.location
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

      } catch (error) {
        console.log(`Error searching league ${leagueId}: ${error}`)
      }
    }

    // Sort by relevance (exact team name matches first, then partial matches)
    const searchTerm = query.toLowerCase()
    const sortedResults = allResults.sort((a, b) => {
      const aHome = a.home_team.toLowerCase()
      const aAway = a.away_team.toLowerCase()
      const bHome = b.home_team.toLowerCase()
      const bAway = b.away_team.toLowerCase()

      // Exact team name matches
      const aExactMatch = aHome === searchTerm || aAway === searchTerm
      const bExactMatch = bHome === searchTerm || bAway === searchTerm

      if (aExactMatch && !bExactMatch) return -1
      if (!aExactMatch && bExactMatch) return 1

      // Team name starts with search term
      const aStartsWith = aHome.startsWith(searchTerm) || aAway.startsWith(searchTerm)
      const bStartsWith = bHome.startsWith(searchTerm) || bAway.startsWith(searchTerm)

      if (aStartsWith && !bStartsWith) return -1
      if (!aStartsWith && bStartsWith) return 1

      // Sort by kickoff time (soonest first)
      return new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime()
    })

    // Limit results
    const limitedResults = sortedResults.slice(0, limit)

    console.log(`Found ${limitedResults.length} matching fixtures`)

    // Prepare response data
    const responseData = {
      results: limitedResults,
      total: limitedResults.length,
      query: query,
      league: league,
      message: limitedResults.length > 0 
        ? `Found ${limitedResults.length} matching fixtures`
        : `No fixtures found matching "${query}"`
    }

    // Cache the response
    setCache(cacheKey, responseData, CACHE_DURATION.SEARCH)
    console.log(`💾 Cached search results for: "${query}"`)

    return NextResponse.json(responseData)

  } catch (error) {
    console.error('Error searching fixtures:', error)
    return NextResponse.json(
      { error: 'Failed to search fixtures' },
      { status: 500 }
    )
  }
}
