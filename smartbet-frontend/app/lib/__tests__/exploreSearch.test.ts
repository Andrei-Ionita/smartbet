/**
 * Explore search must be a fixture lookup, not a full data pull.
 *
 * The route issued one SportMonks request per supported league (29), each asking
 * for `participants;league;metadata;predictions;odds`. A single fixture carries
 * 900-2700 odds entries, so the search pulled prices and model output for every
 * fixture in every league — to render two boolean badges on the result cards.
 * Measured in production: warm 0.38s, cold 33.9-45.1s; still 14.1-18.0s after
 * the calls were batched six at a time.
 *
 * These tests hold the shape of the fix: one filtered provider query behind a
 * local index, no heavy relationships, and a client that cannot let a stale
 * response overwrite a newer one.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const read = (rel: string) => readFileSync(join(process.cwd(), rel), 'utf-8')

const route = read('app/api/search/route.ts')
const explore = read('app/explore/ExploreContent.tsx')

describe('the initial search asks the provider for almost nothing', () => {
  it('requests only the fields a result card renders', () => {
    expect(route).toContain("include: 'participants;league'")
  })

  it('never asks for model predictions', () => {
    expect(route).not.toMatch(/include:\s*'[^']*predictions/)
  })

  it('never asks for odds arrays', () => {
    expect(route).not.toMatch(/include:\s*'[^']*odds/)
  })

  it('does not walk the league list one query at a time', () => {
    // A comma-separated league filter answers the whole window in one query.
    expect(route).toContain('fixtureLeagues:${SUPPORTED_LEAGUE_IDS.join(\',\')}')
    expect(route).not.toMatch(/fixtureLeagues:\$\{leagueId\}/)
  })

  it('serves searches from a local index rather than the provider', () => {
    expect(route).toContain('function buildIndex')
    expect(route).toContain('INDEX_TTL_MS')
    expect(route).toContain('index.entries.filter')
  })

  it('shares one build between concurrent cold searches', () => {
    expect(route).toContain('let BUILDING')
  })

  it('serves a stale index while refreshing rather than blocking', () => {
    expect(route).toContain('INDEX_MAX_AGE_MS')
    expect(route).toContain('if (usable) return INDEX!')
  })

  it('bounds pagination so a provider bug cannot loop the route', () => {
    expect(route).toContain('MAX_PAGES')
  })

  it('applies a timeout to every provider call', () => {
    expect(route).toContain('REQUEST_TIMEOUT_MS')
    expect(route).toContain('AbortController')
  })
})

describe('badges no longer gate the result list', () => {
  it('the route emits no badge fields', () => {
    expect(route).not.toContain('has_predictions')
    expect(route).not.toContain('has_odds')
  })

  it('the result card renders without them', () => {
    expect(explore).not.toContain('has_predictions')
    expect(explore).not.toContain('has_odds')
  })

  it('predictions and prices load only when a fixture is opened', () => {
    expect(explore).toContain('const handleFixtureSelect')
    expect(explore).toContain('/api/fixture/${fixtureId}')
  })
})

describe('a slow earlier response cannot overwrite a newer search', () => {
  it('numbers every request and ignores superseded replies', () => {
    expect(explore).toContain('const requestSeq = useRef(0)')
    expect(explore).toContain('const seq = ++requestSeq.current')
    expect(explore).toContain('const isCurrent = () => seq === requestSeq.current')
    expect(explore).toContain('if (!isCurrent()) return')
  })

  it('aborts the in-flight request when a new one starts', () => {
    expect(explore).toContain('const inFlight = useRef<AbortController | null>(null)')
    expect(explore).toContain('inFlight.current?.abort()')
    expect(explore).toContain('{ signal: controller.signal }')
  })

  it('treats an abort as supersession, not as failure', () => {
    expect(explore).toContain("(error as Error)?.name === 'AbortError'")
  })

  it('cancels on unmount', () => {
    expect(explore).toContain('useEffect(() => () => inFlight.current?.abort(), [])')
  })
})

describe('no-result, timeout and provider error are distinct states', () => {
  it('the route labels each outcome', () => {
    for (const state of ["'empty'", "'timeout'", "'provider_error'", "'ok'", "'idle'"]) {
      expect(route).toContain(state)
    }
  })

  it('a timeout is reported as 504 and a provider failure as 502', () => {
    expect(route).toContain('status: aborted ? 504 : 502')
  })

  it('the client renders them separately', () => {
    expect(explore).toContain("type SearchState = 'idle' | 'loading' | 'ok' | 'empty' | 'timeout' | 'provider_error'")
    expect(explore).toContain("searchState === 'empty' ?")
    expect(explore).toContain("searchState === 'timeout' || searchState === 'provider_error'")
  })

  it('only a failure offers a retry', () => {
    expect(explore).toContain('<RetryButton onRetry={handleRetrySearch} />')
  })
})

describe('every search state exists in both languages', () => {
  const stateBlock = explore.slice(
    explore.indexOf('const searchStateMessage'),
    explore.indexOf('const searchStateMessage') + 1600,
  )

  it('the message helper branches on language', () => {
    expect(stateBlock).toContain("const ro = language === 'ro'")
  })

  it.each(['empty', 'timeout', 'provider_error'])('%s has a Romanian wording', (state) => {
    expect(stateBlock).toContain(`case '${state}':`)
  })

  it('carries the diacritics that mark real Romanian copy', () => {
    for (const phrase of ['Niciun meci', 'nu a răspuns la timp', 'nu este disponibilă momentan']) {
      expect(stateBlock).toContain(phrase)
    }
  })

  it('the failure heading is bilingual', () => {
    expect(explore).toContain("'Căutarea nu a reușit' : 'Search could not complete'")
  })
})

describe('public search stays read-only', () => {
  it('the route performs no write of any kind', () => {
    expect(route).not.toMatch(/\bmethod:\s*['"](POST|PUT|PATCH|DELETE)['"]/)
    expect(route).not.toContain('export async function POST')
    expect(route).not.toContain('export async function PUT')
    expect(route).not.toContain('export async function DELETE')
  })

  it('exposes only a GET handler', () => {
    const handlers = route.match(/export async function (GET|POST|PUT|PATCH|DELETE)/g) ?? []
    expect(handlers).toEqual(['export async function GET'])
  })

  it('reaches no BetGlitch write endpoint', () => {
    expect(route).not.toContain('log-recommendations')
    expect(route).not.toContain('mark-recommended')
    expect(route).not.toContain('update-results')
  })
})
