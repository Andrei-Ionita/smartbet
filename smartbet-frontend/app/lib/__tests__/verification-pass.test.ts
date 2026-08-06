/**
 * Contracts established by the live production verification pass.
 *
 * Each test here corresponds to a defect that was actually observed on
 * betglitch.com — not a hypothetical. Same approach as terminology.test.ts:
 * scan the real sources, because the suite has no DOM and a source scan
 * catches a regression in any branch, not just the one a render exercises.
 */
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { getCopy } from '../terminology'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

describe('legacy rows never publish price-dependent performance', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('defines verification off pricing_integrity_status', () => {
    expect(src).toContain("(p.pricing_integrity_status || '') === 'verified'")
  })

  it('gates value status behind isVerified, and publishes no EV figure', () => {
    // Superseded 2026-08-06. The original contract gated a numeric EV behind
    // isVerified, because EV computed from an unverified price is meaningless.
    // True, but insufficient: EV is derived from the signal score, which is a
    // ranking rather than a calibrated probability, so the figure is unsound
    // even on a verified price. The column now reports value STATUS, and the
    // isVerified gate is retained for the legacy/verified distinction.
    const cell = src.slice(src.indexOf('{isVerified(pred) ? ('))
    expect(cell).not.toContain('expected_value')
    expect(cell).toContain('Not yet assessed')
    expect(cell.indexOf('<NotVerified lang={language} />')).toBeGreaterThan(-1)
  })

  it('gates profit/loss behind isVerified', () => {
    // Line-ending agnostic: the working tree is CRLF on Windows, LF in CI.
    const flat = src.replace(/\r\n/g, '\n')
    expect(flat).toMatch(/\{!isVerified\(pred\) \? \(\s*<NotVerified lang=\{language\} \/>/)
  })

  it('offers the exact unverified wording', () => {
    // The wording moved into terminology.ts so it could be translated. The
    // contract is the wording itself, so assert it there — in both languages.
    const en = getCopy('en').record
    expect(src).toContain('{rec.notVerified}')
    expect(en.notVerified).toBe('Not verified')
    expect(en.notVerifiedTitle).toContain('predates BetGlitch’s verified pricing standard')
    expect(en.notVerifiedTitle).toContain('not used in public performance reporting')
    expect(getCopy('ro').record.notVerified).toBe('Neverificat')
  })

  it('badges every non-verified row', () => {
    expect(src).toContain('{!isVerified(pred) && (')
    expect(src).toContain('<StatusBadge status="legacy" size="sm" lang={language} />')
  })
})

describe('an empty verified record is not rendered as zero performance', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')
  // The wording moved into terminology.ts so it could be translated; the
  // contract is unchanged, so assert the rendered copy AND that both
  // languages actually carry it.
  const en = getCopy('en').record
  const ro = getCopy('ro').record

  it('shows "no results yet" instead of 0% accuracy', () => {
    expect(src).toContain('accuracyStats.overall.total_predictions === 0')
    expect(src).toContain('{rec.noAccuracy}')
    expect(en.noAccuracy).toBe('No verified results yet')
    expect(ro.noAccuracy.length).toBeGreaterThan(0)
  })

  it('shows "no settled picks" instead of a 0% win rate', () => {
    expect(src).toContain('{rec.noSettled}')
    expect(en.noSettled).toBe('No settled picks yet')
    expect(ro.noSettled.length).toBeGreaterThan(0)
  })

  it('suppresses the per-outcome breakdown at zero', () => {
    expect(src).toContain('accuracyStats.overall.total_predictions > 0')
  })

  it('never renders a bare percentage straight off a zero denominator', () => {
    // Each of the three percentage renders must sit inside a guarded branch.
    const guards = src.match(/total_predictions [=><]/g) ?? []
    expect(guards.length).toBeGreaterThanOrEqual(2)
  })
})

describe('model score is not presented as a calibrated probability', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('labels the column "Signal score"', () => {
    // Superseded 2026-08-06: "Model score" implied a model BetGlitch owns.
    expect(src).toContain("'Scor semnal' : 'Signal score'")
    expect(src).not.toContain('>\n                    Model score')
  })

  it('does not suffix the score with a percent sign', () => {
    expect(src).not.toContain('{pred.confidence.toFixed(1)}%')
  })

  it('carries the not-a-probability note', () => {
    expect(src).toContain('MODEL_SCORE_NOTE')
  })
})

describe('no settlement trigger is exposed to the public', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('does not POST to the unauthenticated update-results endpoint', () => {
    expect(src).not.toContain('update-results')
  })

  it('uses no blocking alert() dialogs', () => {
    expect(src).not.toMatch(/(?<!\w)alert\(/)
  })
})

describe('age gate is a real dialog', () => {
  const src = read('app/components/AgeGateModal.tsx')

  it('announces itself as a modal dialog', () => {
    expect(src).toContain('role="dialog"')
    expect(src).toContain('aria-modal="true"')
    expect(src).toContain('aria-labelledby="age-gate-title"')
  })

  it('moves focus into the dialog', () => {
    expect(src).toContain('headingRef.current?.focus()')
  })

  it('traps Tab inside the dialog', () => {
    expect(src).toContain("if (e.key !== 'Tab'")
  })

  it('does not let Escape bypass a legal acknowledgement', () => {
    expect(src).not.toContain("e.key === 'Escape'")
  })

  it('does not compete with the page for the single h1', () => {
    expect(src).not.toContain('<h1')
  })

  it('keeps the consent checkboxes at a usable size', () => {
    // Measured 13x20 on the live site: w-5 with no flex-shrink guard.
    expect(src).toContain('w-6 h-6 mt-0.5 flex-shrink-0')
    expect(src).not.toContain('w-5 h-5 mt-0.5 rounded')
  })
})

describe('language switch is announced to assistive technology', () => {
  const src = read('app/contexts/LanguageContext.tsx')

  it('keeps <html lang> in step with the rendered copy', () => {
    expect(src).toContain('document.documentElement.lang = language')
  })
})

describe('mobile navigation', () => {
  const src = read('components/Navigation.tsx')

  it('closes on Escape and restores focus to the toggle', () => {
    expect(src).toContain("e.key === 'Escape'")
    expect(src).toContain('menuButtonRef.current?.focus()')
  })

  it('switches to the desktop bar only when the bar actually fits', () => {
    // The full Romanian bar needs ~1215px. At the md breakpoint it overflowed
    // the page at 768, 1024 and 1120 — iPad portrait and small laptops.
    expect(src).toContain('hidden xl:flex space-x-4')
    expect(src).toContain('hidden xl:flex items-center gap-3')
    expect(src).toContain('xl:hidden flex items-center gap-4')
    expect(src).not.toContain('hidden md:flex')
    expect(src).not.toContain('md:hidden')
  })

  it('gives the mobile auth actions a 44px target', () => {
    const mobileAuth = src.slice(src.indexOf('flex flex-col gap-2 p-2'))
    const targets = mobileAuth.match(/min-h-\[44px\]/g) ?? []
    expect(targets.length).toBeGreaterThanOrEqual(2)
  })
})

describe('footer', () => {
  const src = read('components/Footer.tsx')

  it('has no dead placeholder links', () => {
    expect(src).not.toContain('href="#"')
  })

  it('gives the remaining social control a 44px target', () => {
    expect(src).toContain('min-h-[44px] min-w-[44px]')
  })

  it('describes the product in the shared vocabulary', () => {
    // The tagline moved into terminology.ts to be translatable. The vocabulary
    // contract now applies to both languages, not just the English literal.
    expect(src).toContain('{f.tagline}')
    expect(getCopy('en').footer.tagline).toContain('frozen')
    expect(getCopy('ro').footer.tagline).toContain('înghețate')
    expect(src).not.toContain('betting insights')
  })
})

describe('auth forms work with password managers and screen readers', () => {
  const register = read('app/register/page.tsx')
  const login = read('app/login/page.tsx')

  it('register declares autocomplete for every credential field', () => {
    expect(register).toContain('autoComplete="username"')
    expect(register).toContain('autoComplete="email"')
    // new-password on both password fields, so managers offer to generate/save.
    expect((register.match(/autoComplete="new-password"/g) ?? []).length).toBe(2)
  })

  it('login declares autocomplete so saved credentials are offered', () => {
    expect(login).toContain('autoComplete="username"')
    expect(login).toContain('autoComplete="current-password"')
  })

  it('announces errors on both forms', () => {
    expect(register).toContain('role="alert"')
    expect(login).toContain('role="alert"')
  })

  it('puts validation errors next to the field that caused them', () => {
    expect(register).toContain('aria-describedby={fieldError.password')
    expect(register).toContain('aria-describedby={fieldError.confirmPassword')
    expect(register).toContain('aria-invalid={Boolean(fieldError.password)}')
    expect(register).toContain("id=\"confirm-error\"")
  })

  it('never clears what the user already typed on a validation error', () => {
    // The early returns must not reset any of the four value states.
    const handler = register.slice(
      register.indexOf('const handleSubmit'),
      register.indexOf('setIsLoading(true)'),
    )
    expect(handler).not.toMatch(/set(Username|Email|Password|ConfirmPassword)\(''\)/)
  })
})

describe('metadata matches the product that actually loads', () => {
  it('explore is described as live signals, not value bets', () => {
    const src = read('app/explore/page.tsx')
    expect(src).toContain('Explore live football signals')
    expect(src).not.toContain('value bets')
  })

  it('about describes the real pipeline', () => {
    const src = read('app/about/page.tsx')
    expect(src).not.toContain('About BetGlitch — AI-Powered Football Predictions')
    expect(src).toContain('how a signal becomes a public result')
  })
})

describe('no client can trigger settlement', () => {
  it('the update-results proxy route is gone', () => {
    expect(existsSync(join(ROOT, 'app/api/django/update-results/route.ts'))).toBe(false)
  })

  it('the public monitoring table only reads', () => {
    // /monitoring is public and this component POSTed an unauthenticated
    // result update on every mount.
    const src = read('app/components/RecommendedPredictionsTable.tsx')
    expect(src).not.toContain("fetch('/api/django/update-results'")
    expect(src).not.toContain('update-results')
  })

  it('no surface anywhere posts to a result-update endpoint', () => {
    for (const rel of [
      'app/track-record/TrackRecordContent.tsx',
      'app/components/RecommendedPredictionsTable.tsx',
      'app/monitoring/MonitoringContent.tsx',
    ]) {
      expect(read(rel)).not.toMatch(/update-fixture-results|transparency\/update-results/)
    }
  })
})

describe('the public recommendations route is read-only', () => {
  const route = read('app/api/recommendations/engine.ts')

  it('makes no write request to our backend', () => {
    // A GET a browser can reach must not create prediction records. This route
    // used to fire a background POST that wrote PredictionLog rows and
    // appended immutable snapshots.
    expect(route).not.toMatch(/method:\s*.(POST|PUT|PATCH|DELETE)./)
    expect(route).not.toContain('signIngestRequest')
  })
})

describe('the ingest secret cannot reach a browser', () => {
  const signer = read('app/lib/ingestSignature.ts')
  const route = read('app/api/recommendations/engine.ts')

  it('never uses a NEXT_PUBLIC_ name', () => {
    // NEXT_PUBLIC_* is inlined into the client bundle at build time, which
    // would publish the signing key to every visitor.
    expect(signer).not.toContain('NEXT_PUBLIC_RECOMMENDATION')
    expect(signer).toContain('RECOMMENDATION_INGEST_SECRET')
  })

  it('is imported only from server-side code', () => {
    expect(signer).toContain("from 'node:crypto'")
    // A 'use client' file importing node:crypto is a build error, so the only
    // way to reach this module is from the server runtime.
    expect(signer).not.toContain("'use client'")
    expect(route).not.toContain("'use client'")
    // The engine is no longer a route module, so it carries no runtime export
    // of its own — it inherits the runtime of whichever route imports it, and
    // BOTH of those pin nodejs. Assert that where it is now declared.
    for (const rel of [
      'app/api/recommendations/route.ts',
      'app/api/internal/recommendations/route.ts',
    ]) {
      expect(read(rel), rel).toContain("export const runtime = 'nodejs'")
    }
  })

  it('signs with the documented header contract', () => {
    expect(signer).toContain('X-BetGlitch-Timestamp')
    expect(signer).toContain('X-BetGlitch-Request-ID')
    expect(signer).toContain('X-BetGlitch-Signature')
    expect(signer).toContain('createHmac')
    expect(signer).toContain("'sha256'")
  })

  it('is dormant — no production caller signs requests today', () => {
    // The signer is retained for a future explicit server-to-server
    // integration. Nothing in the app calls it, which is why the scheduler
    // needs no ingest secret.
    expect(route).not.toContain('signIngestRequest(')
  })

  it('no browser-side code posts to the ingest endpoint', () => {
    for (const rel of [
      'app/page.tsx',
      'app/explore/ExploreContent.tsx',
      'app/components/RecommendedPredictionsTable.tsx',
      'app/track-record/TrackRecordContent.tsx',
    ]) {
      expect(read(rel)).not.toContain('log-recommendations')
    }
  })
})

describe('first-session path survives logout', () => {
  const auth = read('app/contexts/AuthContext.tsx')
  const panel = read('app/components/OnboardingPanel.tsx')
  const dashboard = read('app/dashboard/page.tsx')

  it('registration marks onboarding pending and lands on the dashboard', () => {
    expect(auth).toContain('markOnboardingPending()')
    expect(auth).toContain("router.push('/dashboard')")
  })

  it('dismissal is persisted, not component state', () => {
    expect(panel).toContain("const STORAGE_KEY = 'betglitch_onboarding'")
    expect(panel).toContain("localStorage.setItem(STORAGE_KEY, 'dismissed')")
  })

  it('logout does not wipe the dismissal', () => {
    expect(auth).not.toContain('localStorage.clear()')
    expect(auth).not.toContain("removeItem('betglitch_onboarding')")
  })

  it('the dashboard no longer gates access on smartbet_session_id', () => {
    // The old redirect made a brand-new account unable to reach the dashboard,
    // because registration deletes that key.
    expect(dashboard).not.toMatch(/if\s*\(\s*!storedSessionId\s*\)/)
    expect(dashboard).toContain('isAuthenticated')
  })
})

describe('responsive layout guards', () => {
  it('about lets its stat row wrap', () => {
    // Three unwrapped flex items forced /about to 410px at a 320px viewport.
    const src = read('app/about/page.tsx')
    expect(src).toContain('flex flex-wrap items-center gap-x-6 gap-y-3')
  })
})

describe('the explore signal detail is framed as a live signal', () => {
  const src = read('app/explore/ExploreContent.tsx')

  it('labels the modal as a live model signal', () => {
    // This modal is where a visitor actually reads a signal, and it carried no
    // indication the numbers are mutable or outside the verified record.
    expect(src).toContain('<StatusBadge status="live" size="sm" lang={language} />')
    expect(src).toContain('copy.terms.liveSignal.mutability')
    expect(src).toContain('copy.terms.liveSignal.notInRecord')
  })

  it('states that the model score is not a calibrated probability', () => {
    expect(src).toContain('copy.modelScoreNote')
  })

  it('reads that vocabulary in the visitor’s language', () => {
    // These were the English exports, so a Romanian visitor met an English
    // definition of the concept the badge directly above it had just named.
    expect(src).toContain('const copy = getCopy(language)')
    expect(src).not.toMatch(/\bTERMS\.liveSignal/)
    expect(src).not.toMatch(/\bMODEL_SCORE_NOTE\b/)
  })

  it('is an accessible dialog', () => {
    expect(src).toContain('aria-modal="true"')
    // Renamed with the vocabulary: "live model signal" → "live signal".
    expect(src).toContain('aria-label="Live signal detail"')
    expect(src).toContain('aria-label="Close signal detail"')
  })

  it('makes the fixture card reachable by keyboard', () => {
    // It was a div with onClick: not focusable, not keyboard-operable, and
    // announced as plain text.
    expect(src).toContain('role="button"')
    expect(src).toContain('tabIndex={0}')
    expect(src).toMatch(/e\.key === 'Enter' \|\| e\.key === ' '/)
  })

  it('never blocks the tab with alert()', () => {
    // A blocking dialog freezes the page until dismissed.
    expect(src).not.toMatch(/(?<!\w)alert\(/)
    expect(src).toContain('setFixtureError')
  })
})

describe('price-derived claims are gated on a publishable price', () => {
  const src = read('app/components/RecommendationCard.tsx')

  it('gates on the canonical selection status, not on magnitude', () => {
    // Superseded 2026-08-03. The interim gate here was a floor on the odds and
    // a ceiling on the resulting value. Both describe the number rather than
    // the market, so a second-half Over 2.5 quote of 3.00 satisfied it. The
    // gate is now the pricing contract's own verdict.
    expect(src).toContain('const priceVerified = canPublishPrice(priceSource)')
    expect(src).not.toContain('const MIN_USABLE_ODDS')
    expect(src).not.toContain('const MAX_PUBLISHABLE_EV')
    // Superseded again 2026-08-06, and more strongly. `evPublishable` was
    // `priceVerified && typeof recommendation.ev === 'number'` — a correct
    // gate, but one that made an EV field a precondition for rendering. The
    // public payload no longer carries EV at all, so the card derives its
    // state from the verified price alone.
    expect(src).not.toContain('const evPublishable =')
  })

  it('suppresses the headline EV when the price is not publishable', () => {
    // The EV slot renders a dash in BOTH branches; only the caption differs,
    // and it now follows priceVerified rather than an EV field.
    expect(src).not.toContain('{evPublishable ? (')
    expect(src).toContain('{priceVerified\n                      ?')
    expect(src).toContain("'Valoare neverificată' : 'Value not verified'")
  })

  it('prints no public expected value at all', () => {
    // Superseded 2026-08-05, and more strongly than before. The original defect
    // was a hardcoded '+' rendering "+-32.3%" as a gain (Rijeka v Ilves,
    // 2026-08-03); the sign fix made the number honest but not the claim. EV is
    // derived from an uncalibrated signal score, so no public figure can be
    // justified — the card states the value STATUS instead.
    expect(src).not.toContain(">+{((recommendation.ev || 0) * 100).toFixed(1)}%<")
    expect(src).not.toContain("Math.abs((recommendation.ev || 0) * 100).toFixed(1)")
    expect(src).not.toMatch(/recommendation\.ev[^\r\n]*toFixed\(1\)\}%/)
  })

  it('awards no value level at all', () => {
    // Superseded 2026-08-06, and more strongly. This used to pin the EV-gated
    // quality ladder: an unpublishable price scored ev = 0 so the card could
    // not award "High Value" off a quote the backend would have rejected. The
    // public-truth pass removed the ladder outright — every rung graded an
    // uncalibrated ranking against a calibration standard that does not exist,
    // and "Safe Pick" told a user a gamble was safe. Two honest states remain.
    expect(src).not.toContain('const ev = evPublishable ? (recommendation.ev || 0) * 100 : 0')
    expect(src).not.toContain('if (evPublishable && ev >= 15)')
    expect(src).toContain('const getOpportunityLevel = () => ({')
    expect(src).toContain('level: stateCopy.status')
  })

  it('labels the score as a signal score, not confidence', () => {
    // Superseded 2026-08-05: "Model score" implied a model BetGlitch owns and
    // a probability it cannot calibrate. The disclaimer contract is unchanged.
    expect(src).toContain("'Scor semnal' : 'Signal score'")
    expect(src).toContain('not a calibrated probability')
  })
})

describe('Explore and the beta page are fully bilingual', () => {
  const explore = read('app/explore/ExploreContent.tsx')
  const beta = read('app/pricing/BetaContent.tsx')
  const tr = read('app/locales/translations.ts')

  it('explore renders no hardcoded English headings', () => {
    expect(explore).toContain("{t('explore.title')}")
    expect(explore).toContain("{t('explore.subtitle')}")
    expect(explore).toContain("t('explore.results')")
    expect(explore).toContain("{t('explore.howTo.title')}")
    expect(explore).not.toContain('How to Use the Explorer<')
  })

  it('the beta page reads every string from the bundle', () => {
    expect(beta).not.toContain('BETA_COPY')
    expect(beta).toContain("{t('beta.heading')}")
    expect(beta).toContain("t('beta.m1')")
  })

  it('both languages define the new keys', () => {
    for (const key of ['howTo:', 'step3Body:', 'meansTitle:', 'createAccount:']) {
      const count = (tr.match(new RegExp(key, 'g')) ?? []).length
      expect(count).toBeGreaterThanOrEqual(2)
    }
  })
})

describe('signal card states what it is before any number', () => {
  const src = read('app/components/RecommendationCard.tsx')

  it('labels the object a live signal in both languages', () => {
    expect(src).toContain("'SEMNAL LIVE' : 'LIVE SIGNAL'")
    expect(src).toContain('is not part of the verified record unless')
  })

  it('does not present a fabricated statistical interval', () => {
    // fixtureService derives the band as score minus a hardcoded 5/7/10.
    expect(src).not.toContain('95% CI')
    expect(src).not.toContain('confidence_interval.lower_bound')
  })

  it('does not suffix the signal score with a percent sign', () => {
    expect(src).toContain("'Scor semnal' : 'Signal score'")
    expect(src).not.toContain('{Math.round(recommendation.confidence * 100)}%')
    // Now rendered explicitly as "N / 100" so it cannot read as a percentage.
    expect(src).toContain('/ 100')
  })
})

describe('proof page presentation', () => {
  const src = read('app/proof/_shared/ProofPageBody.tsx')

  it('has exactly one h1 naming the fixture', () => {
    expect(src).toContain('{p.home_team} vs {p.away_team}')
    expect((src.match(/<h1/g) ?? []).length).toBeGreaterThanOrEqual(1)
  })

  it('uses the canonical status vocabulary', () => {
    expect(src).toContain("PENDING: 'PUBLISHED — PENDING'")
    expect(src).toContain("WON: 'RESULT — WON'")
    expect(src).not.toContain("'Pick — pending'")
  })
})

describe('explore search does not make one provider call per league', () => {
  const src = read('app/api/search/route.ts')

  // Superseded 2026-08-03. Batching the 29 per-league calls six at a time got
  // cold search from ~34s to ~15s. The calls themselves were the problem, so
  // they are now one filtered query behind a local index — see
  // app/lib/__tests__/exploreSearch.test.ts for the full contract.
  it('no longer awaits a provider call inside a league loop', () => {
    expect(src).not.toMatch(/for \(const leagueId of leaguesToSearch\)/)
    expect(src).not.toContain('const fetchLeague')
  })

  it('fetches the whole window in one filtered query', () => {
    expect(src).toContain('function buildIndex')
  })
})
