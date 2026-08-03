import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/**
 * Explore search — a local fixture index, not 29 provider round trips.
 *
 * WHAT THIS REPLACED
 * ------------------
 * The route used to issue ONE SportMonks request per supported league (29 of
 * them), each asking for `participants;league;metadata;predictions;odds` at
 * `per_page=50`. A single fixture's odds array runs to 900-2700 entries, so the
 * route pulled megabytes of prices and predictions across 29 calls in order to
 * populate two boolean badges ("AI predictions", "Real-time odds") on the result
 * cards. Nothing else on the result card used any of it.
 *
 * Measured in production: warm 0.38s, cold 33.9s / 34.1s / 37.8s / 45.1s.
 * Batching the 29 calls six at a time (2026-08-03) brought cold down to
 * 14.1-18.0s — still far outside anything a search box can justify.
 *
 * WHAT IT DOES NOW
 * ----------------
 * SportMonks accepts a comma-separated league filter, so the entire 14-day
 * window across every supported league is ONE query, paginated. Measured
 * 2026-08-03: 13 pages, 604 fixtures, 3.6s fetched serially — under 1.2s when
 * the pages after the first are fetched concurrently.
 *
 * That result set is held in a local index and searched in memory, so a query
 * costs zero provider calls while the index is fresh. Predictions and odds are
 * not requested at all here; they are loaded only when a user opens a fixture.
 */

const REQUEST_TIMEOUT_MS = 12000

async function fetchJson(url: string): Promise<any> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(url, { signal: controller.signal })
    if (!response.ok) throw new Error(`provider responded ${response.status}`)
    return await response.json()
  } finally {
    clearTimeout(timeout)
  }
}

function getApiToken(): string | null {
  return process.env.SPORTMONKS_API_TOKEN || null
}

// All leagues covered by subscription (domestic + European Club Tournaments addon)
const SUPPORTED_LEAGUE_IDS = [
  // European Club Tournaments
  2,     // UEFA Champions League
  5,     // UEFA Europa League
  2286,  // UEFA Europa Conference League
  // Domestic Leagues
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

const SEARCH_WINDOW_DAYS = 14
/** SportMonks caps this endpoint's page size at 50 regardless of what we ask. */
const PAGE_SIZE = 50
/** Pages after the first are fetched concurrently, in waves of this size. */
const PAGE_CONCURRENCY = 6
/** Hard stop so a provider pagination bug cannot loop us. */
const MAX_PAGES = 40

/** Fresh enough to serve directly. */
const INDEX_TTL_MS = 10 * 60 * 1000
/** Stale but still serveable while a refresh runs in the background. */
const INDEX_MAX_AGE_MS = 60 * 60 * 1000

interface IndexEntry {
  fixture_id: number
  home_team: string
  away_team: string
  /** Pre-lowercased so a keystroke does not re-lowercase 600 rows. */
  home_lower: string
  away_lower: string
  league_id: number | null
  league: string
  kickoff: string
}

interface FixtureIndex {
  entries: IndexEntry[]
  builtAt: number
  window: string
}

let INDEX: FixtureIndex | null = null
/** Single-flight: concurrent cold searches share one build, not one each. */
let BUILDING: Promise<FixtureIndex> | null = null

function windowDates() {
  const now = new Date()
  const end = new Date(now.getTime() + SEARCH_WINDOW_DAYS * 24 * 60 * 60 * 1000)
  return {
    start: now.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  }
}

function pageUrl(token: string, start: string, end: string, page: number): string {
  const params = new URLSearchParams({
    api_token: token,
    // Deliberately minimal. No predictions, no odds — the result card shows
    // teams, league and kickoff, and nothing else needs a provider relationship.
    include: 'participants;league',
    filters: `fixtureLeagues:${SUPPORTED_LEAGUE_IDS.join(',')}`,
    per_page: String(PAGE_SIZE),
    page: String(page),
    timezone: 'Europe/Bucharest',
  })
  return `https://api.sportmonks.com/v3/football/fixtures/between/${start}/${end}?${params}`
}

function toEntries(rows: any[]): IndexEntry[] {
  return rows.map((fixture: any) => {
    const home = fixture.participants?.find((p: any) => p.meta?.location === 'home')?.name || 'Home'
    const away = fixture.participants?.find((p: any) => p.meta?.location === 'away')?.name || 'Away'
    return {
      fixture_id: fixture.id,
      home_team: home,
      away_team: away,
      home_lower: home.toLowerCase(),
      away_lower: away.toLowerCase(),
      league_id: fixture.league?.id ?? fixture.league_id ?? null,
      league: fixture.league?.name || 'Unknown',
      kickoff: fixture.starting_at,
    }
  })
}

async function buildIndex(token: string): Promise<FixtureIndex> {
  const { start, end } = windowDates()
  const entries: IndexEntry[] = []

  const first = await fetchJson(pageUrl(token, start, end, 1))
  entries.push(...toEntries(first.data || []))

  let hasMore = !!first.pagination?.has_more
  let nextPage = 2

  // The provider reports has_more but not a page count, so pages are pulled in
  // concurrent waves until a wave reports the end.
  while (hasMore && nextPage <= MAX_PAGES) {
    const wave = []
    for (let i = 0; i < PAGE_CONCURRENCY && nextPage + i <= MAX_PAGES; i++) {
      wave.push(nextPage + i)
    }

    const results = await Promise.all(
      wave.map((page) => fetchJson(pageUrl(token, start, end, page)).catch(() => null)),
    )

    hasMore = false
    for (const result of results) {
      if (!result) continue
      entries.push(...toEntries(result.data || []))
      if (result.pagination?.has_more) hasMore = true
    }

    nextPage += wave.length
  }

  entries.sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime())

  return { entries, builtAt: Date.now(), window: `${start}:${end}` }
}

/**
 * Return an index, rebuilding only when there is nothing serveable.
 *
 * A stale-but-recent index is served immediately and refreshed in the
 * background, so only the very first search of a cold process ever waits.
 */
async function getIndex(token: string): Promise<FixtureIndex> {
  const { start, end } = windowDates()
  const currentWindow = `${start}:${end}`
  const age = INDEX ? Date.now() - INDEX.builtAt : Infinity
  const usable = INDEX && INDEX.window === currentWindow && age < INDEX_MAX_AGE_MS

  if (usable && age < INDEX_TTL_MS) return INDEX!

  if (!BUILDING) {
    BUILDING = buildIndex(token)
      .then((built) => {
        INDEX = built
        return built
      })
      .finally(() => {
        BUILDING = null
      })
  }

  // Serve the stale copy rather than making the user wait for the refresh.
  if (usable) return INDEX!
  return BUILDING
}

interface SearchResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
}

export async function GET(request: NextRequest) {
  const startedAt = Date.now()

  try {
    const { searchParams } = new URL(request.url)
    const query = (searchParams.get('q') || '').trim()
    const league = searchParams.get('league') || ''
    const limit = Math.min(Math.max(parseInt(searchParams.get('limit') || '20', 10) || 20, 1), 100)

    // Require either a search query OR a league selection
    if (!query && !league) {
      return NextResponse.json({
        results: [],
        total: 0,
        status: 'idle',
        message: 'Please enter a search query or select a league',
      })
    }

    const token = getApiToken()
    if (!token) {
      return NextResponse.json(
        {
          results: [],
          total: 0,
          status: 'provider_error',
          message: 'Fixture search is unavailable right now.',
        },
        { status: 503 },
      )
    }

    const index = await getIndex(token)

    const leagueId = league ? parseInt(league, 10) : null
    const needle = query.toLowerCase()

    const matches = index.entries.filter((entry) => {
      if (leagueId !== null && entry.league_id !== leagueId) return false
      if (!needle) return true
      return entry.home_lower.includes(needle) || entry.away_lower.includes(needle)
    })

    const results: SearchResult[] = matches.slice(0, limit).map((entry) => ({
      fixture_id: entry.fixture_id,
      home_team: entry.home_team,
      away_team: entry.away_team,
      league: entry.league,
      kickoff: entry.kickoff,
    }))

    return NextResponse.json({
      results,
      total: matches.length,
      query,
      league,
      mode: query ? 'search' : 'browse',
      status: matches.length > 0 ? 'ok' : 'empty',
      // Diagnostics for the latency work; no user data.
      timing_ms: Date.now() - startedAt,
      index_age_ms: Date.now() - index.builtAt,
      indexed_fixtures: index.entries.length,
      message:
        matches.length > 0
          ? query
            ? `Found ${matches.length} fixtures matching "${query}"`
            : `Found ${matches.length} upcoming fixtures`
          : query
            ? `No fixtures found matching "${query}" in the next ${SEARCH_WINDOW_DAYS} days`
            : 'No upcoming fixtures found for this league',
    })
  } catch (error) {
    const aborted = error instanceof Error && error.name === 'AbortError'
    console.error('Error in search API:', error)

    return NextResponse.json(
      {
        results: [],
        total: 0,
        status: aborted ? 'timeout' : 'provider_error',
        message: aborted
          ? 'The fixture provider did not respond in time.'
          : 'Fixture search is unavailable right now.',
      },
      { status: aborted ? 504 : 502 },
    )
  }
}
