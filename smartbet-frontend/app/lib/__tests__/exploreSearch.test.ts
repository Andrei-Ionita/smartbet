/**
 * Explore must remain a lightweight fixture finder. Heavy provider data is
 * loaded only after a visitor chooses a fixture, and is rendered as research
 * rather than silently converted into a BetGlitch recommendation.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import { foldForSearch } from '../textSearch'

const read = (rel: string) => readFileSync(join(process.cwd(), rel), 'utf-8')

const route = read('app/api/search/route.ts')
const explore = read('app/explore/ExploreContent.tsx')

describe('the initial search asks the provider for almost nothing', () => {
  it('requests only the fields a result card renders', () => {
    expect(route).toContain("include: 'participants;league'")
    expect(route).not.toMatch(/include:\s*'[^']*(predictions|odds)/)
  })

  it('uses one bounded, cached index rather than one query per league', () => {
    expect(route).toContain('fixtureLeagues:${SUPPORTED_LEAGUE_IDS.join(\',\')}')
    expect(route).not.toMatch(/fixtureLeagues:\$\{leagueId\}/)
    expect(route).toContain('function buildIndex')
    expect(route).toContain('INDEX_TTL_MS')
    expect(route).toContain('INDEX_MAX_AGE_MS')
    expect(route).toContain('MAX_PAGES')
    expect(route).toContain('REQUEST_TIMEOUT_MS')
  })

  it('shares cold builds and can serve stale data during refresh', () => {
    expect(route).toContain('let BUILDING')
    expect(route).toContain('if (usable) return INDEX!')
  })
})

describe('fixture intelligence loads only after selection', () => {
  it('search cards carry no prediction or odds payload', () => {
    expect(route).not.toContain('has_predictions')
    expect(route).not.toContain('has_odds')
    expect(explore).not.toContain('has_predictions')
    expect(explore).not.toContain('has_odds')
  })

  it('opens the heavy fixture endpoint on demand', () => {
    expect(explore).toContain('const openFixture')
    expect(explore).toContain('/api/fixture/${fixtureId}')
    expect(explore).toContain('data.fixture?.intelligence')
  })

  it('renders a decision workspace rather than a recommendation card', () => {
    expect(explore).toContain('FixtureDecisionWorkspace')
    expect(explore).not.toContain('RecommendationCard')
    expect(explore).toContain('Set your own price')
    expect(explore).toContain('Open decision workspace')
  })

  it('bounds, explains and lets the visitor cancel a slow fixture request', () => {
    expect(explore).toContain('FIXTURE_CLIENT_TIMEOUT_MS')
    expect(explore).toContain('const fixtureInFlight = useRef<AbortController | null>(null)')
    expect(explore).toContain("fetch(`/api/fixture/${fixtureId}`, { signal: controller.signal })")
    expect(explore).toContain('fixtureInFlight.current?.abort()')
    expect(explore).toContain('responding more slowly than usual')
    expect(explore).toContain("ro ? 'Anulează' : 'Cancel'")
    expect(explore).not.toContain('disabled={isLoadingFixture}')
  })
})

describe('fixture endpoint treats optional context as optional', () => {
  const service = read('src/services/fixtureService.ts')
  const fixtureRoute = read('app/api/fixture/[id]/route.ts')

  it('has separate hard limits for the core provider call and enrichments', () => {
    expect(service).toContain('FIXTURE_PROVIDER_TIMEOUT_MS = 14_000')
    expect(service).toContain('OPTIONAL_ENRICHMENT_TIMEOUT_MS = 2_500')
    expect(service).toContain('{ cache: \'no-store\', signal: controller.signal }')
    expect(service).toContain('apiClient.request(standingsUrl, OPTIONAL_ENRICHMENT_TIMEOUT_MS)')
  })

  it('returns a recoverable gateway timeout and briefly caches successful workspaces', () => {
    expect(fixtureRoute).toContain("status: timedOut ? 'timeout' : 'provider_error'")
    expect(fixtureRoute).toContain('{ status: timedOut ? 504 : 502 }')
    expect(fixtureRoute).toContain("'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=60'")
  })
})

describe('a slow earlier response cannot overwrite a newer search', () => {
  it('numbers requests and ignores superseded replies', () => {
    expect(explore).toContain('const requestSeq = useRef(0)')
    expect(explore).toContain('const seq = ++requestSeq.current')
    expect(explore).toContain('const isCurrent = () => seq === requestSeq.current')
    expect(explore).toContain('if (!isCurrent()) return')
  })

  it('aborts on replacement and unmount without showing a false error', () => {
    expect(explore).toContain('const inFlight = useRef<AbortController | null>(null)')
    expect(explore).toContain('inFlight.current?.abort()')
    expect(explore).toContain('{ signal: controller.signal }')
    expect(explore).toContain("(error as Error)?.name === 'AbortError'")
    expect(explore).toContain('useEffect(() => () => {')
    expect(explore).toContain('fixtureInFlight.current?.abort()')
  })
})

describe('search outcomes are distinct, bilingual and recoverable', () => {
  it('the route labels empty, timeout and provider failures', () => {
    for (const state of ["'empty'", "'timeout'", "'provider_error'", "'ok'", "'idle'"]) {
      expect(route).toContain(state)
    }
    expect(route).toContain('status: aborted ? 504 : 502')
  })

  it('the client separates empty from failed states and retries only failures', () => {
    expect(explore).toContain("searchState === 'empty'")
    expect(explore).toContain("searchState === 'timeout' || searchState === 'provider_error'")
    expect(explore).toContain('<RetryButton onRetry={performQuery} />')
  })

  it('contains real Romanian and English state copy', () => {
    for (const phrase of [
      'Niciun meci găsit',
      'nu a răspuns la timp',
      'nu este disponibilă momentan',
      'No fixtures found',
      'Search could not complete',
    ]) {
      expect(explore).toContain(phrase)
    }
  })
})

describe('public search stays read-only', () => {
  it('exports only GET and reaches no write endpoint', () => {
    const handlers = route.match(/export async function (GET|POST|PUT|PATCH|DELETE)/g) ?? []
    expect(handlers).toEqual(['export async function GET'])
    expect(route).not.toMatch(/\bmethod:\s*['"](POST|PUT|PATCH|DELETE)['"]/)
    expect(route).not.toMatch(/log-recommendations|mark-recommended|update-results/)
  })
})

describe('search is accent-insensitive', () => {
  it.each([
    ['Malmö FF', 'malmo ff'],
    ['Fenerbahçe', 'fenerbahce'],
    ['Beşiktaş', 'besiktas'],
    ['Bodø/Glimt', 'bodo/glimt'],
    ['Borussia Mönchengladbach', 'borussia monchengladbach'],
    ['Fußball', 'fussball'],
  ])('folds %s', (input, expected) => {
    expect(foldForSearch(input)).toBe(expected)
  })

  it('applies folding to indexed names and the query', () => {
    expect(route).toContain('home_lower: foldForSearch(home)')
    expect(route).toContain('away_lower: foldForSearch(away)')
    expect(route).toContain('const needle = foldForSearch(query)')
  })
})
