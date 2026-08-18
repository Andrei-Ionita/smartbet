/**
 * The public truth contract.
 *
 * BetGlitch's public copy repeatedly drifted ahead of what the product can
 * support: an "Edge vs Market" panel subtracting a price-implied probability
 * from an uncalibrated ranking, a blog post citing "83% accuracy" from a sample
 * later found to be priced off the wrong market, an About page claiming "we
 * build AI systems", legal text describing machine-learning algorithms nobody
 * here trained.
 *
 * These tests scan the shipped source of every public surface and fail on the
 * claim, not on the disclaimer. Wording may change freely; the claims may not
 * come back.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import {
  EXPLORE_LEAGUE_OPTIONS,
  SEARCHABLE_COMPETITION_COUNT,
  SIGNAL_COMPETITIONS,
  SIGNAL_COMPETITION_IDS,
  SIGNAL_COMPETITION_COUNT,
} from '../coverage'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

/**
 * Comments legitimately NAME the claim they removed — that is how the next
 * reader learns why it went. Only rendered code is scanned.
 */
const stripComments = (src: string) =>
  // Normalise line endings FIRST. The working tree is CRLF on Windows and LF
  // in CI; with a trailing '\r' left in place, `/\/\/.*$/` never matches —
  // '\r' is a line terminator, so `.*` stops short of it and `$` cannot
  // anchor. That silently left every `//` comment in every CRLF file in the
  // scan, which flagged the notes explaining a removal as the removal's own
  // violation.
  src
    .replace(/\r\n/g, '\n')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .map((line) => line.replace(/\/\/.*$/, ''))
    .join('\n')

/**
 * BANNED_CLAIMS in terminology.ts is a registry of phrases that must NOT ship.
 * It necessarily spells them out, so scanning it would flag the guard rail as
 * the violation.
 */
const stripBannedRegistry = (src: string) => {
  const start = src.indexOf('export const BANNED_CLAIMS')
  return start === -1 ? src : src.slice(0, start)
}

const scannable = (src: string) => stripBannedRegistry(stripComments(src))

/** Public product surfaces. Every file here reaches a visitor. */
const PUBLIC_SURFACES = [
  'app/layout.tsx',
  'app/page.tsx',
  'app/about/page.tsx',
  'app/blog/page.tsx',
  'app/blog/posts/how-betglitch-works.ts',
  'app/blog/posts/value-betting-explained.ts',
  'app/blog/posts/transparent-track-records.ts',
  'app/explore/ExploreContent.tsx',
  'app/explore/page.tsx',
  'app/track-record/TrackRecordContent.tsx',
  'app/prediction/[...slug]/PredictionContent.tsx',
  'app/components/RecommendationCard.tsx',
  'app/components/RecommendedPredictionsTable.tsx',
  'app/components/EmailCapture.tsx',
  // Added after production verification 2026-08-06: StatusBadge's accessible
  // hint still read "Live model signal" on every page that renders a badge,
  // and EmptyState carried "The model signal is still shown". Both shipped
  // because the surface list below was incomplete, not because the scan was
  // wrong — shared components are public surfaces too.
  'app/components/StatusBadge.tsx',
  'app/components/HomepageStrategyFits.tsx',
  'app/components/EmptyState.tsx',
  'app/components/BettingCalculatorModal.tsx',
  'app/proof/_shared/ProofPageBody.tsx',
  'components/Footer.tsx',
  'components/Navigation.tsx',
  'app/components/dashboard/PersonalizedRecommendations.tsx',
  'app/lib/terminology.ts',
  'app/locales/translations.ts',
  'app/terms/TermsContent.tsx',
  'app/terms/page.tsx',
  'app/privacy/PrivacyContent.tsx',
  'app/disclaimer/DisclaimerContent.tsx',
  'app/disclaimer/page.tsx',
  'app/responsible-gambling/ResponsibleGamblingContent.tsx',
  'app/bankroll/page.tsx',
  'app/monitoring/page.tsx',
  'app/pricing/page.tsx',
] as const

const SURFACES = PUBLIC_SURFACES.map((rel) => [rel, scannable(read(rel))] as const)

// ── Banned claims ──────────────────────────────────────────────────────────

/**
 * Each entry is [label, pattern]. Patterns match the CLAIM. A truthful
 * negation ("not a calibrated probability", "does not size stakes") must
 * survive, so anything phrased as a denial is excluded explicitly.
 */
const BANNED: ReadonlyArray<readonly [string, RegExp]> = [
  ['Edge vs Market', /edge vs\.? (market|piață)/i],
  ['AI-versus-market comparison', /\bAI:\s*\$?\{?[^}]*\}?%|market implied.*vs.*ai/i],
  ['LIVE MODEL SIGNAL', /live model signal/i],
  ['models rerun', /models? rerun|modelele rulează din nou/i],
  ['AI-generated predictions', /ai[- ]generated (predictions|football)|predicții generate de ai/i],
  ['AI-Powered Football Predictions', /ai[- ]powered (football|sports) (predictions|prediction)/i],
  ['AI Betting Insights', /ai betting insights/i],
  ['AI confidence', /ai confidence/i],
  ['profitable opportunity claim', /(identif\w*|find\w*|detect\w*)[^.]{0,40}profitable|profitable (sports betting|opportunit|play)/i],
  ['proven / verifiable edge', /(?<!not )(real,? verifiable edge|proven edge|demonstrated edge|mathematical edge)/i],
  ['Safe Bet / Safe Pick category', /safe (bet|pick)s?\b/i],
  ['Value Bet category', /\bvalue bets:/i],
  ['Speculative category', /speculative/i],
  // "no ensemble" / "There is no second model" are the corrections we
  // deliberately added; they must survive. Match the assertion, not the denial.
  // Matches PROSE only. `ensemble_info` is an inbound API field that the card
  // no longer reads and Explore only passes through — renaming a wire field is
  // a backend contract change, not a truth fix, so identifier-shaped hits are
  // excluded. Denials ("no ensemble") must also survive.
  [
    'ensemble / multi-model claim',
    /(?<!no )(multi-model|ensemble(?![_ ]info)\b)|all ai models|our models (see|assign|agree)|modele ai\b/i,
  ],
  ['proprietary-model claim', /proprietary (model|algorithm|ai|ml)/i],
  ['every prediction is published', /every (prediction|signal) (is |we |betglitch )?(is )?published|every prediction (ever )?made/i],
  ['free betting tips', /free (weekly )?(betting )?tips/i],
  ['machine-learning algorithm claim', /(we use|using|advanced) (advanced )?machine learning/i],
  ['we build AI systems', /we build ai/i],
  ['highest-confidence predictions', /highest[- ]confidence (prediction|pick)/i],
  // 'Model monitoring' handed visitors an internal engineering concept — and
  // a model BetGlitch does not own. The nav and page now say signal
  // monitoring / signal performance.
  ['Model monitoring label', /model monitoring|monitorizare model|model performance|performanță model/i],
  ['opportunity-assessment label', /opportunity assessment|evaluare oportunitate/i],
]

describe('banned public claims', () => {
  for (const [label, pattern] of BANNED) {
    it(`no surface contains: ${label}`, () => {
      const offenders = SURFACES
        .filter(([, src]) => pattern.test(src))
        .map(([rel]) => rel)
      expect(offenders, `${label} found in: ${offenders.join(', ')}`).toEqual([])
    })
  }
})

describe('no public numeric expected value', () => {
  /**
   * EV is computed from the signal score, which is a ranking. Any rendered
   * figure — however neutrally styled — reads as an assessment the product has
   * not made. Type declarations and gating booleans are fine; a RENDER is not.
   */
  it.each([
    'app/components/RecommendationCard.tsx',
    'app/components/RecommendedPredictionsTable.tsx',
    'app/components/dashboard/PersonalizedRecommendations.tsx',
    'app/track-record/TrackRecordContent.tsx',
    'app/explore/ExploreContent.tsx',
    'app/prediction/[...slug]/PredictionContent.tsx',
  ])('%s renders no EV percentage', (rel) => {
    const src = stripComments(read(rel))
    expect(src).not.toMatch(/\{[^}]*expected_value[^}]*toFixed\([^)]*\)\}\s*%/)
    expect(src).not.toMatch(/EV:?\s*\+?\{/)
    expect(src).not.toMatch(/\{[^}\r\n]*\bev\b[^}\r\n]*toFixed\([^)]*\)\}%/)
    expect(src).not.toMatch(/% EV/)
    expect(src).not.toMatch(/value edge/i)
  })
})

describe('no model-confidence percentage', () => {
  /**
   * `confidence * 100` followed by a '%' presents a relative ranking as the
   * chance of an outcome. The score renders as "N / 100" everywhere.
   */
  it.each([
    'app/components/RecommendationCard.tsx',
    'app/components/dashboard/PersonalizedRecommendations.tsx',
    'app/prediction/[...slug]/PredictionContent.tsx',
    'app/track-record/TrackRecordContent.tsx',
  ])('%s renders no confidence percentage', (rel) => {
    const src = stripComments(read(rel))
    expect(src).not.toMatch(/confidence \* 100\)\}%/)
    expect(src).not.toMatch(/confidence \* 100\)\.toFixed\(\d\)\}%/)
    expect(src).not.toMatch(/confidence\.toFixed\(\d\)\}%/)
    expect(src).not.toMatch(/(High|Good|Moderate|Lower) confidence \(\$\{/)
  })
})

describe('no signal-derived stake recommendation', () => {
  it.each([
    'app/components/RecommendationCard.tsx',
    'app/components/BettingCalculatorModal.tsx',
    'app/components/dashboard/PersonalizedRecommendations.tsx',
    'app/lib/terminology.ts',
  ])('%s recommends no stake off the signal score', (rel) => {
    const src = stripComments(read(rel))
    expect(src).not.toMatch(/recommended stake/i)
    expect(src).not.toMatch(/smaller stakes recommended/i)
    expect(src).not.toMatch(/calculateKelly\(\s*recommendation\.confidence/)
    expect(src).not.toMatch(/applies kelly staking/i)
  })

  it('the Kelly calculator still returns a zero stake', () => {
    // Confirming the earlier fix holds; not re-litigating it.
    const src = read('app/components/BettingCalculatorModal.tsx')
    expect(src).toContain('KELLY_STRATEGIES')
    expect(src).toContain('stake = 0')
  })
})

// ── Required truths ────────────────────────────────────────────────────────

describe('signal-score terminology and its explanation', () => {
  it('the card says Signal score in both languages', () => {
    const card = read('app/components/RecommendationCard.tsx')
    expect(card).toContain("'Scor semnal' : 'Signal score'")
    expect(card).not.toContain("'Scor model' : 'Model score'")
  })

  it('the relative-ranking explanation is stated in both languages', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain(
      'A signal score ranks BetGlitch’s relative preference among the available outcomes. It is not a calibrated probability.',
    )
    expect(copy).toContain(
      'Scorul de semnal clasifică preferința relativă a BetGlitch între rezultatele disponibile. Nu este o probabilitate calibrată.',
    )
  })

  it('the About page defines the score as a ranking, not a probability', () => {
    const src = read('app/about/page.tsx')
    expect(src).toContain('Signal score')
    expect(src).toMatch(/not a calibrated probability/i)
  })

  it('the proof page labels the frozen score as a signal score', () => {
    // Superseded 2026-08-08: the label names the moment the value was frozen.
    expect(read('app/proof/_shared/ProofPageBody.tsx')).toContain('label="Signal score when published"')
  })
})

describe('live signal versus published claim', () => {
  it('terminology keeps the two concepts separate and names the mutability of each', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain("label: 'Live signal'")
    expect(copy).toContain("label: 'Published pick'")
    expect(copy).toContain("label: 'Selecție publicată'")
    expect(copy).toMatch(/can change before kickoff/i)
    expect(copy).toMatch(/cannot be changed or deleted/i)
  })

  it('every blog post states that a live signal can change and a claim cannot', () => {
    for (const rel of [
      'app/blog/posts/how-betglitch-works.ts',
      'app/blog/posts/transparent-track-records.ts',
    ]) {
      const src = read(rel)
      expect(src, rel).toMatch(/live signals?[^.]{0,80}(can|may) change|it can change (at any time )?(before|until) kickoff/i)
      expect(src, rel).toMatch(/immutable|never changes|cannot be edited/i)
    }
  })
})

describe('verified price versus assessed value', () => {
  it('the card distinguishes a verified price from an assessed value', () => {
    const card = read('app/components/RecommendationCard.tsx')
    expect(card).toContain("'PREȚ DE PIAȚĂ VERIFICAT' : 'VERIFIED MARKET PRICE'")
    expect(card).toContain("'Neevaluată încă' : 'Not yet assessed'")
    expect(card).toContain("'Nu poate fi evaluată' : 'Cannot be assessed'")
  })

  it('a verified price never implies value on its own', () => {
    const card = read('app/components/RecommendationCard.tsx')
    expect(card).toContain(
      'The market price has been verified, but BetGlitch does not yet have sufficient calibration evidence to determine whether the price offers value.',
    )
  })
})

describe('pending Gems are excluded from performance', () => {
  it('the record copy says pending counts towards nothing', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toMatch(/Pending picks are not results/i)
    expect(copy).toMatch(/Pending picks do not count/i)
  })

  it('the blog states the same exclusion', () => {
    const src = read('app/blog/posts/transparent-track-records.ts')
    expect(src).toMatch(/pending Gems count towards nothing/i)
    expect(src).toMatch(/only settled current-strategy Gems count/i)
  })
})

describe('free public beta is stated', () => {
  it('the hero eyebrow says so in both languages', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain("eyebrow: 'FREE PUBLIC BETA'")
    expect(copy).toContain("eyebrow: 'BETA PUBLIC GRATUIT'")
  })

  it('the terms describe the service as a free public beta', () => {
    expect(read('app/terms/TermsContent.tsx')).toMatch(/free public beta/i)
  })
})

describe('gambling-risk statements survive', () => {
  it('the footer keeps its operator, risk and age notices', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toMatch(/NOT a betting operator, bookmaker, or gambling site/)
    expect(copy).toMatch(/possible loss of your entire stake/)
    expect(copy).toMatch(/18 years or older/)
  })

  it('the responsible-use line names the loss risk in both languages', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toMatch(/you can lose everything you stake/i)
    expect(copy).toMatch(/poți pierde tot ce mizezi/i)
  })

  it.each([
    'app/terms/TermsContent.tsx',
    'app/disclaimer/DisclaimerContent.tsx',
    'app/responsible-gambling/ResponsibleGamblingContent.tsx',
    'app/about/page.tsx',
  ])('%s states that BetGlitch is not a bookmaker and takes no bets', (rel) => {
    const src = read(rel)
    expect(src, rel).toMatch(/not\s+(a\s+)?(licensed as a\s+)?(betting operator|bookmaker)/i)
    expect(src, rel).toMatch(/do\s+not\s+accept\s+(any\s+)?bets|does\s+not\s+accept\s+bets/i)
  })

  it.each([
    'app/terms/TermsContent.tsx',
    'app/disclaimer/DisclaimerContent.tsx',
    'app/responsible-gambling/ResponsibleGamblingContent.tsx',
  ])('%s states that no output guarantees profit', (rel) => {
    expect(read(rel), rel).toMatch(/no\s+output\s+guarantees\s+profit|will\s+result\s+in\s+profit|guarantees?\s+profit/i)
  })

  it.each([
    'app/terms/TermsContent.tsx',
    'app/disclaimer/DisclaimerContent.tsx',
    'app/responsible-gambling/ResponsibleGamblingContent.tsx',
  ])('%s states that users may lose everything wagered', (rel) => {
    expect(read(rel), rel).toMatch(/lose all (the )?(money|of your money)|entire stake|lose some or all/i)
  })
})

describe('the product does not claim a model it does not have', () => {
  it('the About page says plainly what BetGlitch does not claim', () => {
    const src = read('app/about/page.tsx')
    expect(src).toMatch(/does not build, train or own a predictive model/i)
    expect(src).toMatch(/has not demonstrated predictive or pricing edge/i)
  })

  it('the how-it-works post says the provider owns the model', () => {
    const src = read('app/blog/posts/how-betglitch-works.ts')
    expect(src).toMatch(/we do not build, train or own a predictive model/i)
    expect(src).toMatch(/no second model and no averaging of opinions/i)
  })

  it('the value-betting post is labelled hypothetical wherever it does arithmetic', () => {
    const src = read('app/blog/posts/value-betting-explained.ts')
    // Once as a page-level banner, and again beside each worked example.
    expect(src.match(/hypothetical educational example/gi)?.length ?? 0)
      .toBeGreaterThanOrEqual(3)
    expect(src).toMatch(/does not calculate a kelly stake/i)
  })
})

// ── Coverage counts ────────────────────────────────────────────────────────

describe('one maintained source of truth for coverage counts', () => {
  it('no public page hardcodes a competition count', () => {
    for (const [rel, src] of SURFACES) {
      expect(src, `${rel} hardcodes a league/competition count`)
        .not.toMatch(/\b(27|30)\s*(European\s*)?(leagues|competitions|de ligi)\b/i)
    }
  })

  it('the counts are derived, and the two measures are distinct', () => {
    expect(SEARCHABLE_COMPETITION_COUNT).toBe(EXPLORE_LEAGUE_OPTIONS.length - 1)
    expect(SIGNAL_COMPETITION_COUNT).toBeLessThan(SEARCHABLE_COMPETITION_COUNT)
  })

  it('the pipeline consumes the maintained signal competition objects', () => {
    const route = read('app/api/recommendations/engine.ts')
    expect(route).toContain("import { SIGNAL_COMPETITIONS } from '@/app/lib/coverage'")
    expect(route).toContain('const keyLeagues = SIGNAL_COMPETITIONS')
    expect(SIGNAL_COMPETITIONS.map(({ id }) => id)).toEqual([...SIGNAL_COMPETITION_IDS])
  })

  it('every signal competition is also searchable', () => {
    const searchable = new Set(EXPLORE_LEAGUE_OPTIONS.map((l) => Number(l.id)))
    for (const id of SIGNAL_COMPETITION_IDS) {
      expect(searchable.has(id), `signal competition ${id} is not searchable`).toBe(true)
    }
  })
})

// ── Positioning ────────────────────────────────────────────────────────────

describe('consistent public positioning', () => {
  it('the homepage headline is the brand line, in both languages', () => {
    // Superseded 2026-08-07 by the brand pass: the line names the mission
    // (better decisions through better evidence), not the feature. It promises
    // evidence quality, never outcomes — which keeps it inside the truth
    // contract this suite enforces.
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain("headline: 'Every signal explained. Every published pick locked. Every result visible.'")
    expect(copy).toContain("headline: 'Fiecare semnal explicat. Fiecare selecție blocată. Fiecare rezultat vizibil.'")
  })

  it('the supporting copy names context, uncertainty, locked picks and results', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain('probabilities, prices, context and uncertainty')
    expect(copy).toContain('lock it before kickoff')
    expect(copy).toContain('keep the result visible')
  })

  it('does not promise fixture context the product does not deliver', () => {
    // The hero offered "the context behind each fixture" while the provider
    // returns "?????" for recent form on every live fixture, and there are no
    // lineups, injuries or matchup history. A reviewer called the analysis
    // "extremely thin" and was right — so the promise is withdrawn rather
    // than the shortfall papered over.
    const copy = read('app/lib/terminology.ts')
    expect(copy).not.toContain('the context behind each fixture')
    expect(copy).not.toContain('contextul din spatele fiecărui meci')
  })

  it('the manifesto is present and promises improvement, not predictions', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain('Evidence before confidence. Results before claims. Improvement by version.')
    expect(copy).toContain('We do not promise an edge or that every version will improve.')
  })

  it('the hero trust line commits to no guaranteed wins and no hidden losses', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain('Free public beta · No guaranteed wins · No hidden losses')
  })

  it('root metadata carries the brand line rather than an AI claim', () => {
    const src = read('app/layout.tsx')
    expect(src).toMatch(/published picks locked before kickoff/i)
    expect(src).toMatch(/every eligible result stays visible/i)
  })

  it('navigation and footer use signal vocabulary in both languages', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain("explore: 'Explore signals'")
    expect(copy).toContain("explore: 'Explorează semnalele'")
    expect(copy).toContain('Football decision intelligence across European competitions.')
  })

  it('the newsletter promises updates, not tips', () => {
    const src = read('app/components/EmailCapture.tsx')
    expect(src).toContain('Published-pick and result updates')
  })
})

describe('Romanian parity on changed shared surfaces', () => {
  /** A concept must not exist in one language only. */
  it.each([
    ['Live signal', "label: 'Live signal'", "label: 'Semnal live'"],
    ['Signal score (frozen field)', "'Signal score'", "'Scor semnal'"],
    ['hero eyebrow', "'FREE PUBLIC BETA'", "'BETA PUBLIC GRATUIT'"],
  ])('%s exists in both languages', (_label, en, ro) => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).toContain(en)
    expect(copy).toContain(ro)
  })

  it('no Romanian string still says model where the concept is a signal', () => {
    const copy = read('app/lib/terminology.ts')
    expect(copy).not.toMatch(/Semnale live ale modelului/)
    expect(copy).not.toMatch(/Scorul modelului/)
    expect(copy).not.toMatch(/Explorează predicțiile/)
  })
})
