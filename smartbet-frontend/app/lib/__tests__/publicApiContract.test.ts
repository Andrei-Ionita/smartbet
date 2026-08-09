/**
 * The public API response contract, enforced against a real serialized payload.
 *
 * WHY THIS EXISTS SEPARATELY FROM publicTruth.test.ts
 * ---------------------------------------------------
 * That suite greps source files. It passed for three consecutive releases while
 * production was still serving `value_zone.original_ev` on every recommendation
 * — because a source scan can only check the files someone remembered to list,
 * and it cannot see what a handler actually emits at runtime.
 *
 * This suite runs the real serializer over a realistic internal object and
 * walks the resulting JSON recursively: every key, and every string value, at
 * every depth. A field can only reach the public payload if someone added it to
 * the allowlist in publicRecommendation.ts, and if it survives this scan.
 *
 * The internal fixture below deliberately contains every field the pipeline
 * actually produces — including the ones that must not escape. A serializer
 * that spreads its input, or that someone "fixes" by spreading it later, fails
 * loudly here rather than in production.
 */
import { describe, expect, it } from 'vitest'

import {
  toPublicRecommendation,
  toPublicRecommendationList,
} from '../publicRecommendation'

/**
 * One internal recommendation exactly as app/api/recommendations/route.ts
 * builds it, values taken from the live 2026-08-06 production response.
 */
const INTERNAL_RECOMMENDATION = {
  fixture_id: 19428391,
  home_team: 'Cardiff City',
  away_team: 'Swindon Town',
  home_id: 3, away_id: 27, season_id: 23614,
  league: 'Carabao Cup',
  kickoff: '2026-08-12 18:45:00',
  predicted_outcome: 'Btts yes',
  confidence: 0.66,
  expected_value: 0.2,
  ev: 0.2,
  odds: 1.8,
  bookmaker: '888Sport',
  odds_provenance: {
    odds_market_id: 14, odds_market_name: 'Both Teams To Score',
    odds_bookmaker_id: 2, odds_bookmaker_name: '888Sport',
    odds_captured_at: '2026-08-06T07:10:00Z', odds_label: 'Yes',
    odds_bookmaker_count: 5,
  },
  probabilities: { home: 0.44, draw: 0.28, away: 0.28 },
  odds_data: { home: 2.1, draw: 3.4, away: 3.6, bookmaker: '888Sport' },
  teams_data: { home: { form: 'WWDLW' }, away: { form: 'LDWLL' } },
  explanation: 'Highest-ranked outcome: Both Teams To Score — Btts yes',
  best_market: {
    type: 'btts', name: 'BTTS', display_name: 'Both Teams To Score',
    predicted_outcome: 'Btts yes',
    probability: 0.66, probability_gap: 0.32,
    odds: 1.8, bookmaker: '888Sport',
    expected_value: 0.2,
    market_score: 0.41,
    original_probability: 0.62,
    original_ev: 0.4197520000000001,
    odds_provenance: {
      odds_market_id: 14, odds_market_name: 'Both Teams To Score',
      odds_bookmaker_id: 2, odds_bookmaker_name: '888Sport',
      odds_captured_at: '2026-08-06T07:10:00Z', odds_label: 'Yes',
    },
  },
  all_markets: [
    {
      type: 'btts', name: 'BTTS', predicted_outcome: 'Btts yes',
      probability: 0.66, odds: 1.8,
      expected_value: 0.2, market_score: 0.41, is_recommended: true,
    },
    {
      type: '1x2', name: 'Match Result', predicted_outcome: 'Home',
      probability: 0.44, odds: 2.1,
      expected_value: -0.076, market_score: 0.11, is_recommended: false,
    },
  ],
  enhancement_data: {
    value_zone: {
      zone: 'trap',
      warning: 'Extreme EV detected - likely odds error, proceed with caution',
      original_ev: 0.4197520000000001,
      adjusted_ev: 0.2,
    },
    adjustments_applied: true,
  },
  debug_info: {
    confidence_score: 0.62, probability_gap: 0.32, variance: 'Low',
    market_type: 'btts', markets_evaluated: 4, value_zone: 'trap',
  },
  revenue_vs_risk_score: 0.43,
  signal_quality: 'Strong',
  is_recommended: true,
  gem_rank: 1,
  strategy_evaluation: {
    eligible: true,
    rejectionReasons: [],
    fixturePredictable: true,
    leaguePerformance: {
      marketKey: 'fulltime_result', historicalLogLoss: 0.9,
      hitRatio: 0.61, predictability: 'high', predictivePower: 'up',
      currentLogLoss: 0.84,
    },
    valueBet: {
      active: true, outcome: 'home', fairOdds: 1.7,
      offeredOdds: 1.8, bookmaker: '888Sport', stake: null,
    },
    crossMarket: {
      correctScoreOutcome: 'home', correctScoreVector: { home: 0.6, draw: 0.22, away: 0.18 },
      doubleChanceSupportsSelection: true, leadingDoubleChance: '1x',
    },
    fairOddsBuffer: 1.8 / 1.7 - 1,
    relativePriceSpread: 0.06,
    priceAgeHours: 2,
  },
}

const serialized = toPublicRecommendation(INTERNAL_RECOMMENDATION)
const payload = {
  recommendations: toPublicRecommendationList([INTERNAL_RECOMMENDATION]),
  total: 1, leagues_covered: 27, fixtures_analyzed: 140,
  fixtures_with_predictions: 96,
  lastUpdated: '2026-08-06T08:00:00.000Z', message: 'Success',
}

/** Every key path in an object graph, at every depth. */
function allKeys(node: unknown, path = '', acc: string[] = []): string[] {
  if (Array.isArray(node)) {
    node.forEach((v, i) => allKeys(v, `${path}[${i}]`, acc))
  } else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
      acc.push(path ? `${path}.${k}` : k)
      allKeys(v, path ? `${path}.${k}` : k, acc)
    }
  }
  return acc
}

/** Every string VALUE in an object graph, at every depth. */
function allStrings(node: unknown, acc: string[] = []): string[] {
  if (Array.isArray(node)) node.forEach((v) => allStrings(v, acc))
  else if (node && typeof node === 'object') {
    Object.values(node as Record<string, unknown>).forEach((v) => allStrings(v, acc))
  } else if (typeof node === 'string') acc.push(node)
  return acc
}

const KEYS = allKeys(payload)
const STRINGS = allStrings(payload)

// ── Forbidden keys ─────────────────────────────────────────────────────────

/**
 * Matched against the LAST segment of each key path, so `odds_market_name`
 * cannot be caught by the `ev` rule while `expected_value` still is.
 */
const FORBIDDEN_KEY_RULES: ReadonlyArray<readonly [string, RegExp]> = [
  ['ev', /^ev$/i],
  ['expected_value', /expected_value/i],
  ['original_ev', /original_ev/i],
  ['adjusted_ev', /adjusted_ev/i],
  ['value_zone', /value_zone/i],
  ['betting_edge', /betting_edge|\bedge\b/i],
  ['trap', /trap/i],
  ['form_multiplier', /form_multiplier/i],
  ['shadow', /shadow/i],
  ['calibration', /calibrat/i],
  ['minimum_acceptable_odds', /minimum_acceptable_odds/i],
  ['fair_odds', /fair_odds/i],
  ['decision/BET status', /^(bet|no_bet|decision_status)$/i],
  ['market_score', /market_score/i],
  ['signal_quality', /signal_quality/i],
  ['revenue_vs_risk', /revenue_vs_risk/i],
  ['debug_info', /debug_info/i],
  ['enhancement_data', /enhancement_data/i],
  ['variance', /variance/i],
  ['confidence_score', /confidence_score/i],
  ['original_probability', /original_probability/i],
  ['confidence_threshold', /confidence_threshold/i],
  // True for every row in the top ten, so it carries no information a reader
  // could act on — while its name asserts an endorsement we do not make.
  ['is_recommended', /is_recommended/i],
]

describe('public payload carries no forbidden key', () => {
  const lastSegment = (k: string) => k.split('.').pop()!.replace(/\[\d+\]$/, '')

  for (const [label, rule] of FORBIDDEN_KEY_RULES) {
    it(`no key matches ${label}`, () => {
      const hits = KEYS.filter((k) => rule.test(lastSegment(k)))
      expect(hits, `forbidden key(s): ${hits.join(', ')}`).toEqual([])
    })
  }
})

// ── Forbidden strings ──────────────────────────────────────────────────────

/**
 * `profitable`, `proceed with caution` and the EV-detection wording came from
 * enhancement_data.value_zone.warning, which is exactly the message that must
 * never reach a reader: it infers a bookmaker pricing error from an
 * uncalibrated number.
 */
const FORBIDDEN_STRING_RULES: ReadonlyArray<readonly [string, RegExp]> = [
  ['expected value wording', /expected value/i],
  ['EV abbreviation', /\bEV\b/],
  ['proceed with caution', /proceed with caution/i],
  ['odds error', /odds error/i],
  ['trap/value zone', /\btrap\b|value zone/i],
  ['profitable', /profitab/i],
  ['betting edge', /\bedge\b/i],
  ['fair odds', /fair odds/i],
  ['minimum acceptable odds', /minimum acceptable odds/i],
  ['BET/NO_BET verdict', /\bNO_BET\b|\bPRICE_QUALIFIES\b/],
  ['calibration', /calibrat/i],
  ['shadow', /shadow/i],
  ['form multiplier', /form multiplier/i],
  // The explanation string used to read "Best bet: Match Result - Away",
  // which both told the reader to bet and called the selection best.
  ['best bet', /best bet/i],
  ['recommended wording', /\brecommend/i],
]

describe('public payload carries no forbidden string', () => {
  for (const [label, rule] of FORBIDDEN_STRING_RULES) {
    it(`no string value matches ${label}`, () => {
      const hits = STRINGS.filter((s) => rule.test(s))
      expect(hits, `forbidden string(s): ${JSON.stringify(hits)}`).toEqual([])
    })
  }

  it('the value-zone warning is gone verbatim', () => {
    expect(JSON.stringify(payload))
      .not.toContain('Extreme EV detected')
    expect(JSON.stringify(payload))
      .not.toContain('likely odds error, proceed with caution')
  })
})

// ── The allowlist actually allows what the UI needs ────────────────────────

describe('public payload keeps what the interface requires', () => {
  it('identifies the fixture and its teams', () => {
    expect(serialized.fixture_id).toBe(19428391)
    expect(serialized.home_team).toBe('Cardiff City')
    expect(serialized.away_team).toBe('Swindon Town')
    expect(serialized.league).toBe('Carabao Cup')
    expect(serialized.kickoff).toBe('2026-08-12 18:45:00')
  })

  it('carries the highest-ranked outcome and its raw signal score', () => {
    expect(serialized.predicted_outcome).toBe('Btts yes')
    expect(serialized.confidence).toBe(0.66)
    expect(serialized.best_market?.probability).toBe(0.66)
  })

  it('carries the price, bookmaker and full provenance', () => {
    expect(serialized.odds).toBe(1.8)
    expect(serialized.bookmaker).toBe('888Sport')
    expect(serialized.odds_provenance?.odds_market_name).toBe('Both Teams To Score')
    expect(serialized.odds_provenance?.odds_bookmaker_name).toBe('888Sport')
    expect(serialized.odds_provenance?.odds_captured_at).toBe('2026-08-06T07:10:00Z')
    expect(serialized.best_market?.odds_provenance?.odds_market_id).toBe(14)
  })

  it('keeps the probability gap, which is structural rather than a value claim', () => {
    expect(serialized.best_market?.probability_gap).toBe(0.32)
  })

  it('lists the markets considered, without their ranking scores', () => {
    expect(serialized.all_markets).toHaveLength(2)
    expect(serialized.all_markets[0]).toEqual({
      type: 'btts', name: 'BTTS', predicted_outcome: 'Btts yes',
      probability: 0.66, odds: 1.8,
    })
  })

  it('publishes an allowlisted, provider-backed Gem explanation', () => {
    expect(serialized.gem).toMatchObject({
      rank: 1,
      provider_baseline_price: 1.7,
      league_predictability: 'high',
      predictive_power: 'up',
      bookmakers_checked: 5,
      double_chance_supports: true,
    })
    expect(serialized.gem?.provider_implied_chance).toBeCloseTo(1 / 1.7)
    expect(serialized.gem?.verified_price_advantage).toBeCloseTo(1.8 / 1.7 - 1)
  })
})

// ── The serializer is an allowlist, not a denylist ─────────────────────────

describe('unknown internal fields cannot leak by default', () => {
  it('drops a field nobody added to the allowlist', () => {
    const withNewField = toPublicRecommendation({
      ...INTERNAL_RECOMMENDATION,
      some_future_internal_metric: 0.91,
      nested_future: { calibrated_probability: 0.7 },
    }) as unknown as Record<string, unknown>

    expect(withNewField.some_future_internal_metric).toBeUndefined()
    expect(withNewField.nested_future).toBeUndefined()
    expect(JSON.stringify(withNewField)).not.toContain('0.91')
  })

  it('drops new fields nested inside an allowlisted object', () => {
    const out = toPublicRecommendation({
      ...INTERNAL_RECOMMENDATION,
      best_market: {
        ...INTERNAL_RECOMMENDATION.best_market,
        future_edge_metric: 1.23,
      },
    })
    expect((out.best_market as unknown as Record<string, unknown>).future_edge_metric)
      .toBeUndefined()
  })

  it('survives a minimal object without throwing', () => {
    const out = toPublicRecommendation({
      fixture_id: 1, home_team: 'A', away_team: 'B', league: 'L',
      kickoff: 'k', predicted_outcome: 'Home', confidence: 0.5,
      explanation: 'x',
    })
    expect(out.best_market).toBeNull()
    expect(out.all_markets).toEqual([])
    expect(out.odds_provenance).toBeNull()
    expect(out.gem).toBeNull()
  })
})

// ── The route applies the boundary ─────────────────────────────────────────

describe('the route serializes before responding', () => {
  const src = (() => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { readFileSync } = require('node:fs')
    const { join } = require('node:path')
    return readFileSync(
      join(__dirname, '..', '..', 'api', 'recommendations', 'route.ts'), 'utf8',
    ) as string
  })()

  it('passes everything it returns through the serializer', () => {
    expect(src).toContain('toPublicRecommendationList(result.recommendations)')
    expect(src).toContain('featured_gems: publicGems')
  })

  /*
   * SUPERSEDED 2026-08-06, and strictly strengthened.
   *
   * These three used to pin the header-branch gate: one route decided between
   * the raw payload and the DTO by comparing `X-Internal-Auth` against
   * INTERNAL_API_SECRET, and the test verified the branch failed toward the
   * public payload.
   *
   * The branch is gone. The raw payload now lives behind a SEPARATE route
   * (/api/internal/recommendations) with its own fail-closed auth, so the
   * public handler has no code path to internal fields at all — a stronger
   * guarantee than a correctly-written condition, because there is no
   * condition left to get wrong. The gate's behaviour is covered by
   * routeSeparation.test.ts, which invokes both real handlers.
   */
  it('has no authentication branch of its own', () => {
    expect(src).not.toContain('INTERNAL_API_SECRET')
    expect(src).not.toContain('x-internal-auth')
    expect(src).not.toContain('isInternalConsumer')
  })

  it('cannot return the raw payload under any condition', () => {
    // The only thing it ever puts in `recommendations` is the serializer call.
    const returns = src.match(/recommendations:\s*[^\n,]+/g) ?? []
    expect(returns.length).toBeGreaterThan(0)
    for (const r of returns) {
      expect(r).toContain('toPublicRecommendationList')
    }
  })

  it('keeps confidence_threshold out of the public envelope', () => {
    expect(src).not.toContain('confidence_threshold')
  })

  it('declares an explicit cache policy', () => {
    expect(src).toContain('Cache-Control')
  })
})

describe('every translation key the card uses actually resolves', () => {
  /*
   * Removing the quality-ladder badge keys deleted `card.badges.recommended`
   * while three call sites still used it, so the live odds board rendered the
   * literal string "card.badges.recommended" next to a price. Nothing caught
   * it: the source scans look for claims, and a missing key is the absence of
   * one. Found by looking at the rendered page.
   *
   * A missing key is worse than a wrong string here — it leaks internal
   * identifiers into the UI — so it gets its own guard.
   */
  const { readFileSync } = require('node:fs')
  const { join } = require('node:path')
  const ROOT = join(__dirname, '..', '..', '..')

  const card = readFileSync(
    join(ROOT, 'app', 'components', 'RecommendationCard.tsx'), 'utf8',
  ) as string
  const translations = readFileSync(
    join(ROOT, 'app', 'locales', 'translations.ts'), 'utf8',
  ) as string

  const usedKeys = Array.from(
    new Set((card.match(/t\('([a-zA-Z0-9_.]+)'\)/g) || [])
      .map((m) => m.replace(/^t\('/, '').replace(/'\)$/, ''))),
  )

  it('finds translation keys to check', () => {
    expect(usedKeys.length).toBeGreaterThan(5)
  })

  it.each(usedKeys)('%s resolves in the translations module', (key) => {
    // Keys are dotted paths into a nested object literal; the leaf name is
    // what appears as an object property in the source.
    const leaf = key.split('.').pop()!
    // A leaf that cannot be a bare identifier — '1x2', 'over_under_2.5' —
    // must appear QUOTED in a JS object literal, so allow an optional quote
    // on either side. Without this the guard reported a missing key that was
    // present all along, the moment the card started resolving markets.1x2.
    const escaped = leaf.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    expect(
      new RegExp(`(^|[^\\w.])['"]?${escaped}['"]?\\s*:`, 'm').test(translations),
      `${key} is used by RecommendationCard but has no entry in translations.ts`,
    ).toBe(true)
  })
})

describe('ranking parity — serialization changes order and selection not at all', () => {
  /** A fixed captured payload, already ranked by the pipeline. */
  const RANKED = [
    { ...INTERNAL_RECOMMENDATION, fixture_id: 1, revenue_vs_risk_score: 0.91 },
    { ...INTERNAL_RECOMMENDATION, fixture_id: 2, revenue_vs_risk_score: 0.44 },
    { ...INTERNAL_RECOMMENDATION, fixture_id: 3, revenue_vs_risk_score: 0.12 },
  ]

  it('preserves order exactly', () => {
    const out = toPublicRecommendationList(RANKED)
    expect(out.map((r) => r.fixture_id)).toEqual([1, 2, 3])
  })

  it('preserves count — the serializer filters nothing', () => {
    expect(toPublicRecommendationList(RANKED)).toHaveLength(RANKED.length)
  })

  it('preserves the selected market on every row', () => {
    const out = toPublicRecommendationList(RANKED)
    for (const r of out) {
      expect(r.best_market?.type).toBe('btts')
      expect(r.predicted_outcome).toBe('Btts yes')
      expect(r.odds).toBe(1.8)
    }
  })

  it('does not mutate the internal objects it serializes', () => {
    const before = JSON.stringify(RANKED)
    toPublicRecommendationList(RANKED)
    // The ranking pipeline and the scheduler ingest read these same objects.
    expect(JSON.stringify(RANKED)).toBe(before)
    expect(RANKED[0].best_market.original_ev).toBe(0.4197520000000001)
    expect(RANKED[0].expected_value).toBe(0.2)
  })
})

describe('the card reads no EV field', () => {
  const card = (() => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { readFileSync } = require('node:fs')
    const { join } = require('node:path')
    const raw = readFileSync(
      join(__dirname, '..', '..', 'components', 'RecommendationCard.tsx'), 'utf8',
    ) as string
    // Comments name the fields they stopped reading; scan rendered code only.
    return raw
      .replace(/\r\n/g, '\n')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .split('\n')
      .map((l) => l.replace(/\/\/.*$/, ''))
      .join('\n')
  })()

  it.each([
    'recommendation.ev',
    'evPublishable',
    'expected_value',
    'enhancement_data',
    'value_zone',
    'debug_info',
    'signal_quality',
    'original_ev',
    'market_score',
  ])('does not reference %s', (field) => {
    expect(card).not.toContain(field)
  })

  it('derives state from the verified price alone', () => {
    expect(card).toContain(
      "const cardState: 'signal_only' | 'verified_price' =\n    priceVerified ? 'verified_price' : 'signal_only'",
    )
  })
})
