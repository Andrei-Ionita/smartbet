/**
 * Contracts from the focused authenticated-journey cleanup.
 *
 * Two defects drove this: the onboarding panel sent cards 2 and 3 to the same
 * bare /track-record URL, so a third of the first-session guidance taught
 * nothing; and Romanian stopped at the navigation — the login form, the whole
 * global footer including its legal notice, and most of the verified-record
 * page stayed English.
 *
 * Source scans plus copy assertions, matching terminology.test.ts: no DOM here,
 * and a scan catches a regression in any branch rather than only a rendered one.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { getCopy } from '../terminology'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i

describe('onboarding actions have three distinct destinations', () => {
  for (const lang of ['en', 'ro'] as const) {
    const actions = getCopy(lang).onboarding.actions

    it(`offers three actions in ${lang}`, () => {
      expect(actions).toHaveLength(3)
    })

    it(`sends each ${lang} action somewhere different`, () => {
      // Cards 2 and 3 both pointed at bare /track-record, so "understand
      // published proof" and "follow the verified record" delivered an
      // identical screen.
      expect(new Set(actions.map((a) => a.href)).size).toBe(3)
    })

    it(`points the ${lang} actions at the anchored sections`, () => {
      const hrefs = actions.map((a) => a.href)
      expect(hrefs).toContain('/explore')
      // Superseded 2026-08-08: the concept is PUBLIC COMMITMENT; the old anchor
      // survives as an alias for links already in the wild.
      expect(hrefs).toContain('/track-record#published-picks')
      expect(hrefs).toContain('/track-record#results')
    })

    it(`carries no hardcoded claim identifier in ${lang}`, () => {
      // A published claim is a UUID and can settle or be superseded; onboarding
      // must never deep-link one.
      for (const a of actions) expect(a.href).not.toMatch(UUID)
    })
  }

  it('keeps the onboarding component free of hardcoded destinations', () => {
    const src = read('app/components/OnboardingPanel.tsx')
    expect(src).toContain('href={action.href}')
    expect(src).not.toMatch(/href="\/track-record/)
    expect(src).not.toMatch(UUID)
  })
})

describe('track-record carries both anchor targets', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('renders an element with each anchor id', () => {
    expect(src).toContain('id="public-commitments"')
    // The legacy anchor must survive as an alias — external links depend on it.
    expect(src).toContain('id="published-picks"')
    expect(src).toContain('id="verified-record"')
    expect(src).toContain('id="results"')
  })

  it('offsets both anchors so a sticky header cannot cover them', () => {
    const sections = src.match(/id="(?:published-picks|results)"[\s\S]{0,240}?>/g) ?? []
    expect(sections).toHaveLength(2)
    for (const section of sections) expect(section).toContain('scroll-mt-')
  })

  it('labels each section for assistive technology', () => {
    expect(src).toContain('aria-labelledby="published-picks-heading"')
    expect(src).toContain('aria-labelledby="results-heading"')
  })

  it('never counts a pending pick as a settled result', () => {
    // Superseded source: the list used to be derived with
    // `predictions.filter(isVerified)`. It now comes from the claims endpoint,
    // which marks each row's own eligibility.
    expect(src).not.toContain('const publishedPicks = predictions.filter(isVerified)')
    expect(src).toContain('claim.counts_towards_verified_record')
    expect(getCopy('en').record.publishedStates).toMatch(/pending picks do not count/i)
    expect(getCopy('ro').record.publishedStates).toMatch(/nu intră în totaluri/i)
  })

  it('says the aggregate measures only the current Gem strategy', () => {
    expect(getCopy('en').recordRedesign.currentBody).toMatch(/today's exact strategy version/i)
    expect(src).toContain('{redesign.currentBody}')
    expect(src).toContain('summarizeStrategyRecord(partitioned.current)')
  })

  it('keeps the zero state honest', () => {
    expect(src).toContain('{redesign.zeroHeading}')
    expect(src).toContain('{redesign.currentPicksEmpty}')
    expect(getCopy('en').recordRedesign.zeroBody).toMatch(/no current-generation gem/i)
  })

  it('jumps to the anchor after the client-side data has loaded', () => {
    // The page fetches its content client-side, so at the moment the browser
    // resolves the hash the target does not exist yet and the jump is lost.
    expect(src).toContain("window.addEventListener('hashchange', jumpToHash)")
    expect(src).toContain("document.getElementById(id)?.scrollIntoView")
    expect(src).toContain('window.setTimeout(jumpToHash, 100)')
  })

  it('cleans up every listener and timer it registered', () => {
    expect(src).toContain("window.removeEventListener('hashchange', jumpToHash)")
    expect(src).toContain('window.clearTimeout(timer)')
  })

  it('leaves no dangling anchor reference elsewhere in the app', () => {
    expect(read('app/components/EmptyState.tsx')).not.toContain('/track-record#pending')
  })
})

type Pair = [string, string]

const flatten = (value: unknown, path = ''): Pair[] => {
  if (typeof value === 'string') return [[path, value]]
  if (Array.isArray(value)) return value.flatMap((v, i) => flatten(v, `${path}[${i}]`))
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([k, v]) =>
      flatten(v, path ? `${path}.${k}` : k),
    )
  }
  return []
}

describe('Romanian covers the whole authenticated journey', () => {
  const en = getCopy('en') as Record<string, unknown>
  const ro = getCopy('ro') as Record<string, unknown>
  const blocks = ['auth', 'record', 'footer', 'dashboard']

  for (const block of blocks) {
    it(`defines every ${block} string in Romanian`, () => {
      const enPairs = flatten(en[block])
      const roPairs = flatten(ro[block])
      expect(roPairs.map(([k]) => k).sort()).toEqual(enPairs.map(([k]) => k).sort())
      for (const [key, value] of roPairs) {
        expect(value.length, `${block}.${key} is empty`).toBeGreaterThan(0)
      }
    })

    it(`does not leave ${block} sitting in English`, () => {
      const enMap = new Map(flatten(en[block]))
      // Short strings and proper nouns legitimately match across languages
      // ("Blog", "Email", "BetGlitch"); long prose must not.
      for (const [key, roValue] of flatten(ro[block])) {
        const enValue = enMap.get(key)
        if (!enValue || enValue.length < 12) continue
        expect(roValue, `${block}.${key} is still English`).not.toBe(enValue)
      }
    })
  }

  it('translates the login form, not just the nav around it', () => {
    const src = read('app/login/page.tsx')
    expect(src).toContain('{c.heading}')
    expect(src).toContain('placeholder={c.usernamePlaceholder}')
    expect(src).toContain('placeholder={c.passwordPlaceholder}')
    expect(src).toContain('{isLoading ? c.submitting : c.submit}')
    expect(src).not.toContain('Welcome Back')
    expect(src).not.toContain('Enter your password')
  })

  it('translates the register form including its validation messages', () => {
    const src = read('app/register/page.tsx')
    expect(src).toContain('a.passwordTooShort')
    expect(src).toContain('a.passwordMismatch')
    expect(src).not.toContain('Password must be at least 8 characters long')
    expect(src).not.toContain('Passwords do not match')
  })

  it('translates the global footer including the legal notice', () => {
    const src = read('components/Footer.tsx')
    expect(src).toContain('const f = getCopy(language).footer')
    expect(src).toContain('{f.noticeTitle}')
    expect(src).toContain('{f.ageNotice}')
    expect(src).not.toContain('Important Legal Notice')
    expect(src).not.toContain('All rights reserved')
  })

  it('translates the accessibility label on the footer mail control', () => {
    expect(read('components/Footer.tsx')).toContain('{f.emailSupport}')
    expect(getCopy('ro').footer.emailSupport).not.toBe(getCopy('en').footer.emailSupport)
  })

  it('translates the badge legend explanation', () => {
    const src = read('app/components/StatusBadge.tsx')
    expect(src).toContain('LEGEND_NOTE')
    expect(src).toContain("lang === 'ro' ? LEGEND_NOTE.ro : LEGEND_NOTE.en")
  })

  it('passes the visitor language to every EmptyState and StatusLegend', () => {
    for (const file of [
      'app/dashboard/page.tsx',
      'app/track-record/TrackRecordContent.tsx',
      'app/page.tsx',
    ]) {
      const src = read(file)
      for (const tag of src.match(/<(?:EmptyState|StatusLegend)[^>]*>/g) ?? []) {
        expect(tag, `${file}: ${tag}`).toContain('lang={language}')
      }
    }
  })
})

describe('English remains available and unchanged in meaning', () => {
  const en = getCopy('en')

  it('keeps the wording the pages previously shipped', () => {
    expect(en.auth.login.usernameLabel).toBe('Username or email')
    expect(en.footer.ageNotice).toContain('18 years or older')
    expect(en.footer.noticeOperatorStrong).toContain('NOT a betting operator')
    expect(en.record.scopeHeading).toBe('How these results work')
    expect(en.record.noAccuracy).toBe('No verified results yet')
  })

  it('defaults to English when no language is supplied', () => {
    expect(getCopy(undefined).auth.login.submit).toBe('Sign in')
    expect(getCopy('xx').footer.legal).toBe('Legal')
  })
})

describe('the cleanup introduces no payment surface', () => {
  const files = [
    'app/login/page.tsx',
    'app/register/page.tsx',
    'components/Footer.tsx',
    'app/track-record/TrackRecordContent.tsx',
    'app/components/OnboardingPanel.tsx',
    'app/dashboard/page.tsx',
  ]

  it('adds no checkout, upgrade or payment control', () => {
    for (const file of files) {
      const src = read(file)
      expect(src, file).not.toMatch(/\/api\/checkout/)
      expect(src, file).not.toMatch(/upgradeToPro/)
      expect(src, file).not.toMatch(/href="\/checkout/)
    }
  })

  it('keeps the single pricing link behind the commercial-mode flag', () => {
    const src = read('components/Footer.tsx')
    expect(src.match(/\/pricing/g) ?? []).toHaveLength(1)
    expect(src.slice(src.indexOf('PAYMENTS_ENABLED'))).toContain('/pricing')
  })
})

describe('logout leaves the onboarding dismissal alone', () => {
  const src = read('app/contexts/AuthContext.tsx')

  it('clears session keys only', () => {
    const start = src.indexOf('const logout')
    const logout = src.slice(start, start + 700)
    expect(logout).toContain('smartbet_access_token')
    expect(logout).toContain('smartbet_refresh_token')
    expect(logout).not.toContain('betglitch_onboarding')
  })

  it('marks onboarding pending on registration only', () => {
    expect(src.match(/markOnboardingPending\(\)/g) ?? []).toHaveLength(1)
  })
})

describe('#published-picks reads immutable claims, never the prediction feed', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('fetches the published-claims endpoint', () => {
    expect(src).toContain("fetch('/api/published-claims'")
    expect(read('app/api/published-claims/route.ts')).toContain('/api/proof/claims/')
    expect(src).toContain('setClaims(data.claims as PublishedClaimRow[])')
  })

  it('renders the section from the claims feed, not from predictions', () => {
    // The old implementation derived the list with
    // `predictions.filter(isVerified)`, which could show a prediction that was
    // never published and omit a claim that was.
    expect(src).not.toContain('predictions.filter(isVerified)')
    expect(src).toContain('partitioned.current.map((claim) => (')
    expect(src).toContain('partitioned.historical.map((claim) => (')
    expect(src).toContain('key={claim.claim_id}')
  })

  it('never falls back to predictions when the endpoint fails', () => {
    const loader = src
      .slice(src.indexOf('const loadClaims'), src.indexOf('const loadData'))
      // A comment may legitimately name the feed the code must not use.
      .replace(/\/\/[^\r\n]*/g, '')
    expect(loader).toContain('setClaims(null)')
    expect(loader).toContain('setClaimsError(true)')
    expect(loader).not.toContain('setPredictions')
    expect(loader).not.toContain('predictions.filter')
    expect(loader).not.toContain('transparency/recent')
  })

  it('distinguishes loading, empty and error as three separate states', () => {
    expect(src).toContain('claims === null')
    expect(src).toContain('{redesign.currentPicksEmpty}')
    expect(src).toContain('{rec.publishedError}')
    expect(src).toContain("role=\"alert\"")
    expect(src).toContain("role=\"status\"")
  })

  it('links each claim to its own proof page without hardcoding one', () => {
    expect(src).toContain('href={claim.proof_url}')
    expect(src).not.toMatch(UUID)
  })

  it('states per row whether it counts towards the verified record', () => {
    expect(src).toContain('claim.counts_towards_verified_record')
    expect(src).toContain('rec.publishedCountedIn')
    expect(src).toContain('rec.publishedNotCounted')
  })

  it('derives the badge from the recorded claim state', () => {
    expect(src).toContain('statusFromClaim(')
    expect(src).toContain('claim.claim_state')
    expect(src).toContain('claim.result?.status ?? null')
  })

  it('keeps the verified-record aggregate on the settled-only stats source', () => {
    // The aggregate still comes from the transparency dashboard, which counts
    // settled results only — pending claims cannot reach it.
    expect(src).not.toContain('/api/transparency/dashboard/')
    expect(src).toContain('partitionStrategyClaims(claims ?? [])')
    expect(src).toContain('summarizeStrategyRecord(partitioned.current)')
  })

  it('translates every published-claims state in both languages', () => {
    for (const key of [
      'publishedLoading', 'publishedError', 'publishedRetry', 'publishedProofLink',
      'publishedOddsLabel', 'publishedAtLabel', 'publishedNotCounted',
      'publishedCountedIn', 'publishedPriceAgeLabel', 'publishedVersionLabel',
      'publishedFreshLabel', 'publishedStaleLabel', 'publishedExcludedFromRecord',
      'publishedExcludedMissingPrice', 'publishedExcludedIntegrity',
      'publishedExcludedSuperseded', 'publishedExcludedVoid',
      'publishedExcludedCancelled', 'publishedExcludedGeneric',
      'reconciliationHeading', 'reconciliationBody',
      'reconciliationPublished', 'reconciliationPending',
      'reconciliationFinished', 'reconciliationExcludedNote',
    ] as const) {
      const en = getCopy('en').record[key]
      const ro = getCopy('ro').record[key]
      expect(en.length, `en ${key}`).toBeGreaterThan(0)
      expect(ro.length, `ro ${key}`).toBeGreaterThan(0)
      expect(ro, `${key} is still English`).not.toBe(en)
    }
  })

  it('introduces no payment surface', () => {
    expect(src).not.toMatch(/\/api\/checkout/)
    expect(src).not.toMatch(/upgradeToPro/)
  })
})
