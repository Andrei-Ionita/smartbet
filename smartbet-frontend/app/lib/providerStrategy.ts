import type { OddsProvenance, ProductMarket } from './oddsSelection'

/**
 * A deliberately narrow betting-eligibility policy.
 *
 * SportMonks already publishes two things the old ranking ignored:
 *   1. a per-league, per-market report card over recent matches; and
 *   2. a dedicated value-bet model with an active flag and fair odd.
 *
 * The old engine instead treated an uncalibrated ranking score as a probability,
 * derived its own EV from it, and called the top ten rows recommendations.  This
 * module does not manufacture another probability.  A public betting candidate
 * must be supported by the provider's own value model, its own league report
 * card, and a fresh, broadly quoted canonical price.
 */

export const VALUE_STRATEGY_POLICY = {
  generation: 3,
  eligibleMarkets: ['1x2'] as const,
  requirePredictableFixture: true,
  leaguePredictability: ['good', 'high'] as const,
  rejectedPredictivePower: ['down'] as const,
  requireActiveAlignedValueBet: true,
  requireCorrectScoreAgreement: true,
  requireDoubleChanceSupport: true,
  minimumFairOddsBuffer: 0.02,
  minimumBookmakers: 3,
  maximumRelativePriceSpread: 0.15,
  maximumPriceAgeHours: 12,
  maximumSelections: 3,
} as const

export type FixturePredictability = true | false | null

const asBoolean = (value: unknown): boolean | null => {
  if (value === true || value === false) return value
  if (typeof value === 'string') {
    const v = value.trim().toLowerCase()
    if (v === 'true' || v === '1' || v === 'yes') return true
    if (v === 'false' || v === '0' || v === 'no') return false
  }
  if (value === 1) return true
  if (value === 0) return false
  return null
}

/** SportMonks metadata can be a relation array or a flattened object. */
export function fixturePredictability(metadata: unknown): FixturePredictability {
  const queue: unknown[] = [metadata]
  const seen = new Set<unknown>()

  while (queue.length) {
    const item = queue.shift()
    if (!item || seen.has(item)) continue
    seen.add(item)

    if (Array.isArray(item)) {
      queue.push(...item)
      continue
    }
    if (typeof item !== 'object') continue

    const obj = item as Record<string, unknown>
    if (Object.prototype.hasOwnProperty.call(obj, 'predictable')) {
      const parsed = asBoolean(obj.predictable)
      if (parsed !== null) return parsed
    }

    // Known relation wrappers. Avoid recursively walking arbitrary payloads:
    // metadata may grow large and only these containers can hold the flag.
    for (const key of ['values', 'value', 'data', 'metadata']) {
      if (obj[key] !== undefined) queue.push(obj[key])
    }
  }
  return null
}

const finite = (value: unknown): number | null => {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : null
}

export interface NativeValueBet {
  active: boolean
  outcome: 'home' | 'draw' | 'away' | null
  fairOdds: number | null
  offeredOdds: number | null
  bookmaker: string | null
  stake: number | null
}

export interface CrossMarketConsensus {
  correctScoreOutcome: 'home' | 'draw' | 'away' | null
  correctScoreVector: Record<'home' | 'draw' | 'away', number> | null
  doubleChanceSupportsSelection: boolean | null
  leadingDoubleChance: '1x' | 'x2' | '12' | null
}

const valueOutcome = (value: unknown): NativeValueBet['outcome'] => {
  switch (String(value ?? '').trim().toLowerCase()) {
    case '1':
    case 'home':
      return 'home'
    case 'x':
    case 'draw':
      return 'draw'
    case '2':
    case 'away':
      return 'away'
    default:
      return null
  }
}

/** Find the provider's VALUEBET object; presence alone is not evidence. */
export function nativeValueBet(predictions: unknown): NativeValueBet | null {
  if (!Array.isArray(predictions)) return null

  const candidates = predictions.filter((row) => {
    if (!row || typeof row !== 'object') return false
    const r = row as Record<string, any>
    const developerName = String(r.type?.developer_name ?? '').toUpperCase()
    return r.type_id === 33 || developerName === 'VALUEBET'
  })

  if (!candidates.length) return null
  // Prefer a currently active record if the provider returns historical and
  // current rows together. Deterministic fallback to the first row.
  const selected = candidates.find((row: any) => asBoolean(row.predictions?.is_value) === true)
    ?? candidates[0]
  const payload = (selected as any).predictions ?? {}

  return {
    active: asBoolean(payload.is_value) === true,
    outcome: valueOutcome(payload.bet),
    fairOdds: finite(payload.fair_odd),
    offeredOdds: finite(payload.odd),
    bookmaker: payload.bookmaker ? String(payload.bookmaker) : null,
    stake: finite(payload.stake),
  }
}

/**
 * Derive a second 1X2 opinion from the provider's correct-score distribution
 * and check that its dedicated double-chance model does not exclude the pick.
 * These are consistency checks, not extra probabilities manufactured by us.
 */
export function crossMarketConsensus(
  predictions: unknown,
  predictedOutcome: string,
): CrossMarketConsensus {
  const empty: CrossMarketConsensus = {
    correctScoreOutcome: null,
    correctScoreVector: null,
    doubleChanceSupportsSelection: null,
    leadingDoubleChance: null,
  }
  if (!Array.isArray(predictions)) return empty

  const correctScore = predictions.find((row: any) =>
    row?.type_id === 240 ||
    String(row?.type?.developer_name ?? '').toUpperCase() === 'CORRECT_SCORE_PROBABILITY')
  const scores = correctScore?.predictions?.scores
  let scoreOutcome: CrossMarketConsensus['correctScoreOutcome'] = null
  let scoreVector: CrossMarketConsensus['correctScoreVector'] = null

  if (scores && typeof scores === 'object') {
    const totals = { home: 0, draw: 0, away: 0 }
    for (const [label, raw] of Object.entries(scores)) {
      const amount = finite(raw)
      if (amount === null || amount < 0) continue
      const match = /^(\d+)-(\d+)$/.exec(label)
      if (match) {
        const home = Number(match[1])
        const away = Number(match[2])
        totals[home > away ? 'home' : home < away ? 'away' : 'draw'] += amount
      } else if (label === 'Other_1') totals.home += amount
      else if (label === 'Other_2') totals.away += amount
      else if (label === 'Other_X') totals.draw += amount
    }
    const sum = totals.home + totals.draw + totals.away
    if (sum > 0) {
      scoreVector = {
        home: totals.home / sum,
        draw: totals.draw / sum,
        away: totals.away / sum,
      }
      scoreOutcome = (Object.entries(scoreVector) as Array<
        ['home' | 'draw' | 'away', number]
      >).sort((a, b) => b[1] - a[1])[0][0]
    }
  }

  const dc = predictions.find((row: any) =>
    row?.type_id === 239 ||
    String(row?.type?.developer_name ?? '').toUpperCase() === 'DOUBLE_CHANCE_PROBABILITY')
  const dcPayload = dc?.predictions
  let leadingDoubleChance: CrossMarketConsensus['leadingDoubleChance'] = null
  let supports: boolean | null = null
  if (dcPayload && typeof dcPayload === 'object') {
    const legs: Array<[CrossMarketConsensus['leadingDoubleChance'], number]> = [
      ['1x', finite(dcPayload.draw_home) ?? -1],
      ['x2', finite(dcPayload.draw_away) ?? -1],
      ['12', finite(dcPayload.home_away) ?? -1],
    ]
    const leading = legs.sort((a, b) => b[1] - a[1])[0]
    if (leading[0] && leading[1] >= 0) {
      leadingDoubleChance = leading[0]
      const members: Record<'1x' | 'x2' | '12', string[]> = {
        '1x': ['home', 'draw'], x2: ['draw', 'away'], '12': ['home', 'away'],
      }
      supports = members[leadingDoubleChance].includes(predictedOutcome.toLowerCase())
    }
  }

  return {
    correctScoreOutcome: scoreOutcome,
    correctScoreVector: scoreVector,
    doubleChanceSupportsSelection: supports,
    leadingDoubleChance,
  }
}

export interface LeagueMarketPerformance {
  marketKey: string
  historicalLogLoss: number | null
  hitRatio: number | null
  predictability: string | null
  predictivePower: string | null
  currentLogLoss: number | null
}

const PERFORMANCE_MARKET_KEY: Record<ProductMarket, string> = {
  '1x2': 'fulltime_result',
  btts: 'both_teams_to_score',
  'over_under_2.5': 'over_under_2_5',
  // SportMonks does not publish an independent double-chance report card.
  double_chance: 'fulltime_result',
}

const metricName = (row: Record<string, any>): string => {
  const named = String(row.type?.developer_name ?? '').toUpperCase()
  if (named) return named
  const byId: Record<number, string> = {
    241: 'HISTORICAL_LOG_LOSS',
    242: 'MODEL_HIT_RATIO',
    243: 'MODEL_PREDICTABILITY',
    244: 'MODEL_PREDICTIVE_POWER',
    245: 'MODELS_LOG_LOSS',
  }
  return byId[Number(row.type_id)] ?? ''
}

export function leagueMarketPerformance(
  payload: unknown,
  market: ProductMarket,
): LeagueMarketPerformance {
  const rows = Array.isArray(payload)
    ? payload
    : Array.isArray((payload as any)?.data)
      ? (payload as any).data
      : []
  const marketKey = PERFORMANCE_MARKET_KEY[market]
  const values = new Map<string, unknown>()

  for (const raw of rows) {
    if (!raw || typeof raw !== 'object') continue
    const row = raw as Record<string, any>
    const name = metricName(row)
    if (name) values.set(name, row.data?.[marketKey])
  }

  const text = (v: unknown): string | null =>
    typeof v === 'string' && v.trim() ? v.trim().toLowerCase() : null

  return {
    marketKey,
    historicalLogLoss: finite(values.get('HISTORICAL_LOG_LOSS')),
    hitRatio: finite(values.get('MODEL_HIT_RATIO')),
    predictability: text(values.get('MODEL_PREDICTABILITY')),
    predictivePower: text(values.get('MODEL_PREDICTIVE_POWER')),
    currentLogLoss: finite(values.get('MODELS_LOG_LOSS')),
  }
}

const parseProviderDate = (value: string | null | undefined): number | null => {
  if (!value) return null
  const hasZone = /(?:z|[+-]\d\d:?\d\d)$/i.test(value.trim())
  const normalized = value.trim().replace(' ', 'T') + (hasZone ? '' : 'Z')
  const timestamp = Date.parse(normalized)
  return Number.isFinite(timestamp) ? timestamp : null
}

export interface StrategyEvaluation {
  eligible: boolean
  rejectionReasons: string[]
  fixturePredictable: FixturePredictability
  leaguePerformance: LeagueMarketPerformance
  valueBet: NativeValueBet | null
  crossMarket: CrossMarketConsensus
  fairOddsBuffer: number | null
  relativePriceSpread: number | null
  priceAgeHours: number | null
}

/**
 * Auditable inputs for the Gem ordering. These are deliberately derived from
 * the provider's fair price and our verified canonical quote; the engine does
 * not reinterpret its own ranking score as a probability.
 */
export interface GemMetrics {
  providerImpliedProbability: number | null
  providerBaselineOdds: number | null
  verifiedOdds: number | null
  verifiedPriceAdvantage: number | null
  probabilityPayoutBalance: number | null
}

export function gemMetrics(evaluation: StrategyEvaluation): GemMetrics {
  const baseline = evaluation.valueBet?.fairOdds ?? null
  const advantage = evaluation.fairOddsBuffer
  if (!baseline || baseline <= 1 || advantage === null || !Number.isFinite(advantage)) {
    return {
      providerImpliedProbability: null,
      providerBaselineOdds: baseline,
      verifiedOdds: null,
      verifiedPriceAdvantage: advantage,
      probabilityPayoutBalance: null,
    }
  }

  const probability = 1 / baseline
  const verifiedOdds = baseline * (1 + advantage)
  const netPayout = verifiedOdds - 1
  const balance = netPayout > 0
    ? (probability * verifiedOdds - 1) / netPayout
    : null

  return {
    providerImpliedProbability: probability,
    providerBaselineOdds: baseline,
    verifiedOdds,
    verifiedPriceAdvantage: advantage,
    probabilityPayoutBalance: balance !== null && Number.isFinite(balance) ? balance : null,
  }
}

export interface StrategyInput {
  market: ProductMarket
  predictedOutcome: string
  metadata: unknown
  predictions: unknown
  leaguePerformancePayload: unknown
  odds: number
  oddsProvenance: OddsProvenance
  evaluatedAt?: Date
}

export function evaluateValueStrategy(input: StrategyInput): StrategyEvaluation {
  const reasons: string[] = []
  const predictable = fixturePredictability(input.metadata)
  const performance = leagueMarketPerformance(input.leaguePerformancePayload, input.market)
  const valueBet = nativeValueBet(input.predictions)
  const crossMarket = crossMarketConsensus(input.predictions, input.predictedOutcome)

  if (input.market !== '1x2') reasons.push('market_not_value_strategy')
  if (predictable !== true) reasons.push(
    predictable === false ? 'fixture_not_predictable' : 'fixture_predictability_missing',
  )

  if (!VALUE_STRATEGY_POLICY.leaguePredictability.includes(performance.predictability as any)) {
    reasons.push(performance.predictability
      ? 'league_predictability_below_good'
      : 'league_predictability_missing')
  }
  if (!performance.predictivePower) reasons.push('league_predictive_power_missing')
  else if (VALUE_STRATEGY_POLICY.rejectedPredictivePower.includes(performance.predictivePower as any)) {
    reasons.push('league_predictive_power_down')
  }

  const selected = input.predictedOutcome.trim().toLowerCase()
  if (!valueBet) reasons.push('provider_value_bet_missing')
  else {
    if (!valueBet.active) reasons.push('provider_value_bet_inactive')
    if (!valueBet.outcome || valueBet.outcome !== selected) {
      reasons.push('provider_value_bet_not_aligned')
    }
    if (!valueBet.fairOdds || valueBet.fairOdds <= 1) reasons.push('provider_fair_odds_missing')
    if (!valueBet.offeredOdds || !valueBet.fairOdds || valueBet.offeredOdds <= valueBet.fairOdds) {
      reasons.push('provider_value_price_not_above_fair')
    }
  }

  if (!crossMarket.correctScoreOutcome) reasons.push('correct_score_consensus_missing')
  else if (crossMarket.correctScoreOutcome !== selected) {
    reasons.push('correct_score_consensus_not_aligned')
  }
  if (crossMarket.doubleChanceSupportsSelection === null) {
    reasons.push('double_chance_consensus_missing')
  } else if (!crossMarket.doubleChanceSupportsSelection) {
    reasons.push('double_chance_consensus_not_aligned')
  }

  const fairOddsBuffer = valueBet?.fairOdds && valueBet.fairOdds > 1
    ? input.odds / valueBet.fairOdds - 1
    : null
  if (fairOddsBuffer === null || fairOddsBuffer < VALUE_STRATEGY_POLICY.minimumFairOddsBuffer) {
    reasons.push('canonical_price_buffer_too_small')
  }

  const p = input.oddsProvenance
  if ((p.odds_bookmaker_count ?? 0) < VALUE_STRATEGY_POLICY.minimumBookmakers) {
    reasons.push('insufficient_bookmaker_coverage')
  }
  const relativePriceSpread = input.odds > 0
    ? (p.odds_max - p.odds_min) / input.odds
    : null
  if (relativePriceSpread === null || !Number.isFinite(relativePriceSpread)
      || relativePriceSpread > VALUE_STRATEGY_POLICY.maximumRelativePriceSpread) {
    reasons.push('price_dispersion_too_wide')
  }

  const captured = parseProviderDate(p.odds_captured_at)
  const now = (input.evaluatedAt ?? new Date()).getTime()
  const priceAgeHours = captured === null ? null : (now - captured) / 3_600_000
  if (priceAgeHours === null || priceAgeHours < 0
      || priceAgeHours > VALUE_STRATEGY_POLICY.maximumPriceAgeHours) {
    reasons.push('price_stale_or_timestamp_missing')
  }

  return {
    eligible: reasons.length === 0,
    rejectionReasons: reasons,
    fixturePredictable: predictable,
    leaguePerformance: performance,
    valueBet,
    crossMarket,
    fairOddsBuffer,
    relativePriceSpread,
    priceAgeHours,
  }
}

/**
 * Rank only candidates that already passed every eligibility gate. The first
 * term is the Kelly growth fraction without turning it into a stake: it
 * rewards a useful price advantage while penalising payout-dependent longshot
 * risk. Remaining provider quality and market-consensus fields break ties.
 */
export function compareGemStrategy(
  a: StrategyEvaluation,
  b: StrategyEvaluation,
): number {
  const predictabilityRank: Record<string, number> = { high: 2, good: 1 }
  const powerRank: Record<string, number> = { up: 2, unchanged: 1 }
  const by = (left: number | null, right: number | null, descending = true) => {
    const l = left ?? Number.NEGATIVE_INFINITY
    const r = right ?? Number.NEGATIVE_INFINITY
    return descending ? r - l : l - r
  }

  return (
    by(gemMetrics(a).probabilityPayoutBalance, gemMetrics(b).probabilityPayoutBalance) ||
    by(predictabilityRank[a.leaguePerformance.predictability ?? ''] ?? 0,
      predictabilityRank[b.leaguePerformance.predictability ?? ''] ?? 0) ||
    by(powerRank[a.leaguePerformance.predictivePower ?? ''] ?? 0,
      powerRank[b.leaguePerformance.predictivePower ?? ''] ?? 0) ||
    by(a.fairOddsBuffer, b.fairOddsBuffer) ||
    by(gemMetrics(a).providerImpliedProbability, gemMetrics(b).providerImpliedProbability) ||
    by(a.leaguePerformance.hitRatio, b.leaguePerformance.hitRatio) ||
    by(a.relativePriceSpread, b.relativePriceSpread, false)
  )
}

/** Backwards-compatible name for internal callers while Generation 3 rolls out. */
export const compareValueStrategy = compareGemStrategy
