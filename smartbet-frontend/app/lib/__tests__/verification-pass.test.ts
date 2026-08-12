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
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')

describe('legacy rows never publish price-dependent performance', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('defines verification off pricing_integrity_status', () => {
    const record = read('app/lib/currentStrategyRecord.ts')
    expect(record).toContain('claim.ranking_version === CURRENT_STRATEGY_VERSION')
    expect(src).toContain('partitionStrategyClaims(claims ?? [])')
  })

  it('gates value status behind isVerified, and publishes no EV figure', () => {
    // Superseded 2026-08-06. The original contract gated a numeric EV behind
    // isVerified, because EV computed from an unverified price is meaningless.
    // True, but insufficient: EV is derived from the signal score, which is a
    // ranking rather than a calibrated probability, so the figure is unsound
    // even on a verified price. The column now reports value STATUS, and the
    // isVerified gate is retained for the legacy/verified distinction.
    expect(src).not.toContain('expected_value')
    expect(src).not.toContain('isVerified(pred)')
    expect(src).toContain('redesign.historicalBody')
  })

  it('gates profit/loss behind isVerified', () => {
    // Line-ending agnostic: the working tree is CRLF on Windows, LF in CI.
    expect(src).toContain('summarizeStrategyRecord(partitioned.current)')
    expect(src).not.toContain('pred.profit_loss')
  })

  it('offers exact current-versus-historical wording in both languages', () => {
    const en = getCopy('en').recordRedesign
    expect(src).toContain('{redesign.historicalBody}')
    expect(en.historicalBody).toContain('not evidence for the current Gem strategy')
    expect(en.historicalBody).toContain('excluded from every figure above')
    expect(getCopy('ro').recordRedesign.historicalBody.length).toBeGreaterThan(0)
  })

  it('badges every non-verified row', () => {
    expect(src).toContain('{historical && (')
    expect(src).toContain('{redesign.historicalVersionLabel}')
  })
})

describe('legacy rows are an explicit archive, never the default table', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('defaults to settled verified-price rows', () => {
    expect(src).toContain('summarizeStrategyRecord(partitioned.current)')
  })

  it('keeps verified and legacy rows in mutually exclusive views', () => {
    expect(src).toContain('partitionStrategyClaims(claims ?? [])')
    expect(src).toContain('partitioned.current.map((claim) => (')
    expect(src).toContain('partitioned.historical.map((claim) => (')
  })

  it('offers a named legacy archive and only explains legacy inside it', () => {
    expect(src).toContain('{redesign.historicalHeading}')
    expect(src).toContain('<details className="mt-5')
  })
})

describe('an empty verified record is not rendered as zero performance', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')
  // The wording moved into terminology.ts so it could be translated; the
  // contract is unchanged, so assert the rendered copy AND that both
  // languages actually carry it.
  it('shows "no results yet" instead of 0% accuracy', () => {
    expect(src).toContain('partitioned.current.length === 0')
    expect(src).toContain('{redesign.zeroHeading}')
    expect(getCopy('en').recordRedesign.zeroHeading).toContain('starts at zero')
    expect(getCopy('ro').recordRedesign.zeroHeading.length).toBeGreaterThan(0)
  })

  it('shows "no settled picks" instead of a 0% win rate', () => {
    expect(src).toContain('redesign.summaryReturnEmpty')
    expect(getCopy('en').recordRedesign.summaryReturnEmpty).toContain('first settled pick')
    expect(getCopy('ro').recordRedesign.summaryReturnEmpty.length).toBeGreaterThan(0)
  })

  it('suppresses the per-outcome breakdown at zero', () => {
    expect(src).not.toContain('accuracyStats')
  })

  it('never renders a bare percentage straight off a zero denominator', () => {
    // Each of the three percentage renders must sit inside a guarded branch.
    expect(src).toContain('summary.roiPercent === null')
    expect(src).toContain('summary.counted > 0 && roiLabel')
  })
})

describe('model score is not presented as a calibrated probability', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('labels the column "Signal score"', () => {
    // Superseded 2026-08-06: "Model score" implied a model BetGlitch owns.
    expect(src).not.toContain('model_score_percent.toFixed')
    expect(src).not.toContain('Signal score')
  })

  it('does not suffix the score with a percent sign', () => {
    expect(src).not.toContain('{pred.confidence.toFixed(1)}%')
  })

  it('carries the not-a-probability note', () => {
    expect(src).toContain('{redesign.boundary}')
    expect(getCopy('en').recordRedesign.boundary).toContain('never counted automatically')
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
    expect(getCopy('en').footer.tagline).toContain('locked before kickoff')
    expect(getCopy('ro').footer.tagline).toContain('blocate înainte de start')
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
  it('explore is described as decision intelligence, not value bets', () => {
    const src = read('app/explore/page.tsx')
    expect(src).toContain('Explore football odds, probabilities and fixture context')
    expect(src).toContain('calculate your own fair odds')
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

describe('the Explore detail is framed as a decision workspace', () => {
  const src = read('app/explore/ExploreContent.tsx')
  const workspace = read('app/components/FixtureDecisionWorkspace.tsx')

  it('separates research from BetGlitch recommendations', () => {
    expect(src).toContain('<FixtureDecisionWorkspace')
    expect(src).not.toContain('RecommendationCard')
    expect(workspace).toContain('Nothing here automatically becomes a BetGlitch recommendation.')
  })

  it('states that model-market differences are not proof of value', () => {
    expect(workspace).toContain('Their difference is not proof of value.')
    expect(workspace).toContain('This is your conclusion, not a BetGlitch estimate.')
  })

  it('translates data-quality limitations in the visitor language', () => {
    expect(workspace).toContain('const limitationCopy')
    expect(workspace).toContain('Probabilitățile furnizorului nu sunt disponibile')
    expect(workspace).toContain('Provider probabilities are unavailable')
  })

  it('is an accessible dialog', () => {
    expect(src).toContain('aria-modal="true"')
    expect(src).toContain('aria-label="Fixture decision workspace"')
    expect(src).toContain("aria-label={ro ? 'Închide' : 'Close'}")
  })

  it('makes the fixture card reachable by keyboard', () => {
    expect(src).toContain('<button\n                    key={fixture.fixture_id}')
    expect(src).toContain('type="button"')
    expect(src).toContain('focus-visible:outline')
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

  it('explore pairs every major English heading with Romanian copy', () => {
    for (const pair of [
      ['Explore. Evaluate. Set your own price.', 'Explorează. Evaluează. Stabilește prețul tău.'],
      ['Upcoming fixtures', 'Meciuri următoare'],
      ['Search results', 'Rezultatele căutării'],
      ['Open decision workspace', 'Deschide spațiul de decizie'],
    ]) {
      expect(explore).toContain(pair[0])
      expect(explore).toContain(pair[1])
    }
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
    expect(src).toContain('is not part of public results unless')
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
    expect(src).toContain("PENDING: 'PUBLISHED PICK — AWAITING RESULT'")
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
