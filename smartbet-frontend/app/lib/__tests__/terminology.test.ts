/**
 * Public-copy contracts.
 *
 * These assert against the REAL page sources rather than a rendered snapshot.
 * The vitest suite runs without a DOM, and a source scan is the stronger guard
 * anyway: it catches an unsupported claim the moment someone types it, in any
 * branch of any conditional, whether or not a test happens to render it.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import {
  BANNED_CLAIMS, HERO, MODEL_SCORE_NOTE, RESPONSIBLE_USE, TERMS,
  WORKFLOW_STEPS, getCopy,
} from '../terminology'
import { statusFromClaim } from '../signalStatus'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

/** Every surface a first-time visitor can reach without an account. */
const PUBLIC_SOURCES = [
  'app/page.tsx',
  'app/about/page.tsx',
  'app/register/page.tsx',
  'app/explore/ExploreContent.tsx',
  'app/track-record/page.tsx',
  'app/pricing/BetaContent.tsx',
  'app/locales/translations.ts',
  'app/lib/terminology.ts',
]

describe('unsupported claims are absent from public copy', () => {
  for (const rel of PUBLIC_SOURCES) {
    it(`${rel} makes no unsupported claim`, () => {
      const src = read(rel).toLowerCase()
      for (const claim of BANNED_CLAIMS) {
        // terminology.ts legitimately contains the ban list itself.
        if (rel === 'app/lib/terminology.ts') continue
        expect(src, `"${claim}" must not appear in ${rel}`).not.toContain(claim)
      }
    })
  }

  it('the homepage never renders a zero percentage as performance', () => {
    const src = read('app/page.tsx')
    // A literal "0%" would read as break-even rather than "nothing settled yet".
    expect(src).not.toMatch(/['"`>]\s*\+?0%/)
    expect(src).toContain('hero.zeroState')
  })

  it('the homepage no longer ships the internal PRODUCTION league chips', () => {
    expect(read('app/page.tsx')).not.toContain('PRODUCTION')
  })
})

describe('the homepage answers the five-second question', () => {
  const src = read('app/page.tsx')

  it('uses the hero copy from the shared source, not its own wording', () => {
    for (const key of ['eyebrow', 'headline', 'supporting', 'primaryCta', 'secondaryCta']) {
      expect(src).toContain(`hero.${key}`)
    }
  })

  it('states what BetGlitch is, in one sentence', () => {
    // Superseded 2026-08-07 by the brand pass. "Verifiable football market
    // signals" named the feature; the brand line names the reason the feature
    // exists. The truth constraints are unchanged — the line promises better
    // evidence, not better outcomes.
    expect(HERO.headline).toBe('Every signal explained. Every published pick locked. Every result visible.')
  })

  it('offers one primary action and one secondary, not three peers', () => {
    // The old hero had Explore + Track Record + Learn More at equal weight.
    expect(src).not.toContain('landing.learnMore')
  })

  it('carries the responsible-use statement', () => {
    expect(src).toContain('responsibleUse')
    // Strengthened 2026-08-06: "does not place bets" was true but weak. The
    // line now names the bookmaker status and the loss risk explicitly.
    expect(RESPONSIBLE_USE).toContain('does not accept bets')
    expect(RESPONSIBLE_USE).toContain('not a bookmaker')
    expect(RESPONSIBLE_USE).toContain('you can lose everything you stake')
    expect(RESPONSIBLE_USE).toContain('18+')
  })
})

describe('terminology is defined once and used everywhere', () => {
  it('names exactly three public concepts', () => {
    expect(Object.keys(TERMS).sort()).toEqual([
      // Superseded 2026-08-08: publishedPick became publicCommitment.
      'liveSignal', 'publicCommitment', 'verifiedRecord',
    ])
  })

  it('states the boundary between a live signal and the verified record', () => {
    // Superseded 2026-08-08: the boundary sentence now ALSO denies the
    // recommendation reading, which was the bigger confusion.
    expect(TERMS.liveSignal.notInRecord).toContain('not a betting recommendation')
    expect(TERMS.liveSignal.notInRecord).toContain('only if BetGlitch formally commits it')
    expect(TERMS.liveSignal.definition).toContain('can change')
  })

  it('lists what publication freezes', () => {
    expect(TERMS.publicCommitment.frozenFields).toContain('Recorded odds')
    expect(TERMS.publicCommitment.frozenFields).toContain('Bookmaker')
  })

  it('scopes the verified record to eligible settled commitments only', () => {
    expect(TERMS.verifiedRecord.scope).toContain('Pending picks are shown separately')
    expect(TERMS.verifiedRecord.scope).toMatch(/void or cancelled/i)
  })

  it('does not describe a model score as a calibrated probability', () => {
    expect(MODEL_SCORE_NOTE).toContain('not a calibrated probability')
  })

  it('explains the workflow in five ordered stages, ending in evaluation', () => {
    // Superseded 2026-08-07. The Explore/Publish/Verify triad ended at the
    // result, presenting BetGlitch as a static prediction engine. Measure and
    // Improve are the brand's actual claim: the system is evaluated in public.
    expect(WORKFLOW_STEPS.map(s => s.title)).toEqual([
      'Analyse', 'Rank', 'Publish', 'Measure', 'Improve',
    ])
  })
})

describe('bilingual copy cannot drift', () => {
  const en = getCopy('en')
  const ro = getCopy('ro')

  const shape = (o: unknown): unknown =>
    Array.isArray(o)
      ? o.map(shape)
      : o && typeof o === 'object'
        ? Object.fromEntries(
            Object.entries(o as Record<string, unknown>)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([k, v]) => [k, shape(v)]),
          )
        : typeof o

  it('both languages expose an identical structure', () => {
    expect(shape(ro)).toEqual(shape(en))
  })

  it('falls back to English for an unknown language', () => {
    expect(getCopy('de')).toBe(en)
    expect(getCopy(undefined)).toBe(en)
  })

  it('translates the hero rather than leaving English in place', () => {
    expect(ro.hero.headline).not.toBe(en.hero.headline)
    expect(ro.hero.primaryCta).not.toBe(en.hero.primaryCta)
  })
})

describe('registration states its value proposition', () => {
  const src = read('app/register/page.tsx')
  const copy = getCopy('en')

  it('says what an account is for', () => {
    expect(src).toContain('register.heading')
    expect(src).toContain('register.supporting')
    expect(copy.register.supporting).toContain('bankroll')
    expect(copy.register.supporting).toContain('verified public record')
  })

  it('states that the beta is free and needs no payment method', () => {
    expect(copy.register.freeDuringBeta.toLowerCase()).toContain('free')
    expect(copy.register.noPayment.toLowerCase()).toContain('no payment method')
  })

  it('states the product is informational and does not place bets', () => {
    expect(copy.register.informational.toLowerCase()).toContain('does not place bets')
  })

  it('does not add an onboarding questionnaire before the form', () => {
    // Only the four original credential fields may exist.
    const inputs = src.match(/<input/g) ?? []
    expect(inputs.length).toBe(4)
  })
})

describe('post-registration destination', () => {
  const src = read('app/contexts/AuthContext.tsx')

  it('sends a new account to the dashboard, not the marketing homepage', () => {
    expect(src).toContain("markOnboardingPending()")
    expect(src).toContain("router.push('/dashboard')")
  })

  it('marks onboarding pending only at registration', () => {
    const register = src.slice(src.indexOf('const register'))
    expect(register).toContain('markOnboardingPending')
  })
})

describe('onboarding is shown once', () => {
  const src = read('app/components/OnboardingPanel.tsx')

  it('persists dismissal', () => {
    expect(src).toContain("localStorage.setItem(STORAGE_KEY, 'dismissed')")
  })

  it('renders only when explicitly pending, never by default', () => {
    expect(src).toContain('useState(false)')
    expect(src).toContain("=== 'pending'")
  })

  it('offers exactly the three first-session actions', () => {
    expect(getCopy('en').onboarding.actions.map(a => a.id))
      .toEqual(['explore', 'proof', 'record'])
  })

  it('leads with exploring live signals', () => {
    expect(getCopy('en').onboarding.actions[0].href).toBe('/explore')
  })
})

describe('live signals are visually distinct from published claims', () => {
  it('maps backend statuses onto the public badge vocabulary', () => {
    expect(statusFromClaim(null, 'won')).toBe('won')
    expect(statusFromClaim(null, 'lost')).toBe('lost')
    expect(statusFromClaim(null, 'void')).toBe('void')
    expect(statusFromClaim(null, 'cancelled')).toBe('cancelled')
    expect(statusFromClaim('pending', null)).toBe('published_pending')
    expect(statusFromClaim('legacy_unverified', null)).toBe('legacy')
    expect(statusFromClaim(null, null)).toBe('live')
  })

  it('treats a settled outcome as authoritative over the claim status', () => {
    expect(statusFromClaim('pending', 'won')).toBe('won')
  })

  it('encodes mutability in the border, not only in colour', () => {
    const src = read('app/components/StatusBadge.tsx')
    // Exactly one badge may be dashed: the mutable one.
    const dashed = src.match(/border-dashed/g) ?? []
    expect(dashed.length).toBe(1)
    expect(src).toMatch(/live:[\s\S]*?border-dashed/)
  })

  it('gives wins and losses identical prominence', () => {
    const src = read('app/components/StatusBadge.tsx')
    const won = src.match(/won:\s*\{[\s\S]*?className: '([^']+)'/)?.[1] ?? ''
    const lost = src.match(/lost:\s*\{[\s\S]*?className: '([^']+)'/)?.[1] ?? ''
    // Same structural treatment; only the hue differs.
    expect(won.replace(/emerald/g, 'X')).toBe(lost.replace(/rose/g, 'X'))
  })

  it('carries the status in text as well as colour', () => {
    const src = read('app/components/StatusBadge.tsx')
    for (const label of ['LIVE SIGNAL', 'LOCKED PICK — PENDING', 'RESULT — WON',
                         'RESULT — LOST', 'VOID', 'CANCELLED']) {
      expect(src).toContain(label)
    }
  })
})

describe('empty states are intentional', () => {
  const src = read('app/components/EmptyState.tsx')

  const REQUIRED = [
    'no_live_signals', 'no_search_results', 'no_pending_claims',
    'no_verified_results', 'no_league_fixtures', 'missing_odds',
    'provider_unavailable', 'first_dashboard',
  ]

  it('covers every required state', () => {
    for (const key of REQUIRED) expect(src).toContain(key)
  })

  it('distinguishes an expected empty screen from a failure', () => {
    expect(src).toContain("tone: 'expected'")
    expect(src).toContain("tone: 'problem'")
    expect(src).toContain("role={problem ? 'alert' : undefined}")
  })

  it('says the public results are being built, not that they are empty', () => {
    expect(src).toContain('The public results are being built')
    expect(src).toMatch(/win or lose/i)
  })

  it('explains why a price may be missing without hiding the signal', () => {
    expect(src).toContain('will not publish a priced claim without complete market provenance')
  })
})

describe('the verified record page does not promise a proven history', () => {
  const src = read('app/track-record/page.tsx')

  it('no longer claims every prediction ever made', () => {
    expect(src.toLowerCase()).not.toContain('every prediction')
    expect(src.toLowerCase()).not.toContain('real roi')
  })

  it('describes the published-pick universe in its metadata', () => {
    expect(src).toContain('Current Gem strategy results')
    expect(src).toContain('every Gem published by the current BetGlitch strategy')
  })
})

describe('the beta positioning is consistent', () => {
  it('uses one wording for the beta, in both languages', () => {
    expect(getCopy('en').beta.primary).toBe(
      'BetGlitch is currently in public beta. Access is free while we build and validate the verified public record.',
    )
    expect(getCopy('ro').beta.primary).toContain('beta public')
  })

  it('makes no pricing, launch-date or urgency promise', () => {
    for (const lang of ['en', 'ro'] as const) {
      const blob = JSON.stringify(getCopy(lang)).toLowerCase()
      for (const banned of ['coming soon', 'launch date', 'limited time',
                            'act now', 'discount', 'money-back', '€', 'în curând']) {
        expect(blob, `${banned} in ${lang}`).not.toContain(banned)
      }
    }
  })
})

describe('analytics stays minimal and non-sensitive', () => {
  const src = read('app/lib/analytics.ts')

  it('covers the required events', () => {
    for (const e of ['home_primary_cta', 'home_verified_record_cta',
                     'registration_started', 'registration_completed',
                     'first_login', 'onboarding_action', 'explore_search',
                     'fixture_opened', 'published_proof_opened',
                     'dashboard_visited', 'beta_page_viewed']) {
      expect(src).toContain(e)
    }
  })

  it('never records what a person searched for or intends to stake', () => {
    // The payload type is a closed set — widening it is a deliberate act.
    const props = src.slice(src.indexOf('type Props'), src.indexOf('type Win'))
    expect(props).toContain('surface?')
    expect(props).toContain('has_results?')
    expect(props).not.toMatch(/query|stake|bankroll|amount|selection/i)
  })

  it('adds no analytics dependency', () => {
    const pkg = JSON.parse(read('package.json'))
    const deps = { ...pkg.dependencies, ...pkg.devDependencies }
    for (const d of Object.keys(deps)) {
      expect(d).not.toMatch(/posthog|mixpanel|amplitude|segment/i)
    }
  })
})

describe('navigation', () => {
  const src = read('components/Navigation.tsx')

  it('exposes the verified record', () => {
    expect(src).toContain("href: '/track-record'")
  })

  it('closes the mobile menu with a close icon, not a logout icon', () => {
    expect(src).not.toContain('rotate-180')
    expect(src).toContain('<X className="h-6 w-6" />')
  })

  it('labels the mobile toggle for assistive technology', () => {
    expect(src).toContain('aria-label={isMenuOpen')
    expect(src).toContain('aria-controls="mobile-menu"')
  })

  it('keeps every commercial surface behind the flag', () => {
    const pricingRefs = src.match(/\/pricing/g) ?? []
    const guards = src.match(/PAYMENTS_ENABLED/g) ?? []
    expect(guards.length).toBeGreaterThanOrEqual(pricingRefs.length - 1)
  })
})
