import type { OddsProvenance, ProductMarket } from './oddsSelection'
import {
  VALUE_STRATEGY_POLICY,
  type StrategyEvaluation,
} from './providerStrategy'

export const MODEL_SHORTLIST_POLICY = {
  maximumSelections: 6,
  maximumPerDecisionLane: 3,
  confidenceFloor: 0.55,
  minimumGap: { draw: 0.10, other: 0.08 },
  minimumBookmakers: 2,
  maximumRelativePriceSpread: 0.20,
  maximumPriceAgeHours: 12,
} as const

/**
 * Market-specific gates for the research portfolio. These decide what deserves
 * investigation; they do not promote a market into the verified Gem strategy
 * or reinterpret an uncalibrated model score as expected value.
 *
 * First-team-to-score and half-time markets are intentionally absent: they can
 * be priced, but the current result feed cannot settle them deterministically.
 */
export const PORTFOLIO_MARKET_POLICY: Partial<Record<ProductMarket, {
  minimumConfidence: number
  minimumGap: number
  minimumOdds: number
  maximumOdds: number
}>> = {
  '1x2': { minimumConfidence: 0.55, minimumGap: 0.08, minimumOdds: 1.45, maximumOdds: 5 },
  btts: { minimumConfidence: 0.56, minimumGap: 0.12, minimumOdds: 1.45, maximumOdds: 3.5 },
  'over_under_1.5': { minimumConfidence: 0.60, minimumGap: 0.15, minimumOdds: 1.45, maximumOdds: 3.5 },
  'over_under_2.5': { minimumConfidence: 0.56, minimumGap: 0.12, minimumOdds: 1.45, maximumOdds: 4 },
  'over_under_3.5': { minimumConfidence: 0.58, minimumGap: 0.15, minimumOdds: 1.45, maximumOdds: 4.5 },
  double_chance: { minimumConfidence: 0.66, minimumGap: 0.10, minimumOdds: 1.35, maximumOdds: 3 },
  correct_score: { minimumConfidence: 0.16, minimumGap: 0.02, minimumOdds: 4, maximumOdds: 20 },
}

export interface ModelShortlistInput {
  fixtureId: number
  homeTeam: string
  awayTeam: string
  league: string
  kickoff: string
  marketType: ProductMarket
  predictedOutcome: string
  signalStrength: number
  signalGap: number
  odds: number
  oddsProvenance: OddsProvenance
  strategyEvaluation: StrategyEvaluation
}

export interface InternalModelShortlistCandidate {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market_type: ProductMarket
  leading_selection: string
  signal_strength: number
  signal_gap: number
  verified_price: number
  bookmaker: string | null
  bookmakers_checked: number
  price_age_hours: number | null
  relative_price_spread: number | null
  supporting_models: number
  explicit_contradictions: number
  value_signal_aligned: boolean
  portfolio_score: number
  /** Internal-only canonical price evidence used by the publication worker. */
  odds_provenance: OddsProvenance
  strategy_evaluation: StrategyEvaluation
}

export interface PublicModelShortlistItem {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market_type: ProductMarket
  leading_selection: string
  signal_strength: number
  signal_gap: number
  verified_price: number
  bookmaker: string | null
  bookmakers_checked: number
  price_age_hours: number | null
  supporting_models: number
  gem_gap_categories: string[]
  why_shortlisted: string[]
  why_not_gem: string[]
}

const selectedOutcome = (value: string) => value.trim().toLowerCase()

export function buildModelShortlistCandidate(
  input: ModelShortlistInput,
): InternalModelShortlistCandidate | null {
  const evaluation = input.strategyEvaluation
  const marketPolicy = PORTFOLIO_MARKET_POLICY[input.marketType]
  if (!marketPolicy) return null
  const selected = selectedOutcome(input.predictedOutcome)
  const requiredGap = input.marketType === '1x2' && selected === 'draw'
    ? Math.max(marketPolicy.minimumGap, MODEL_SHORTLIST_POLICY.minimumGap.draw)
    : marketPolicy.minimumGap
  const bookmakers = input.oddsProvenance.odds_bookmaker_count ?? 0
  const spread = evaluation.relativePriceSpread
  const age = evaluation.priceAgeHours
  const scoreSupports = evaluation.crossMarket.correctScoreOutcome !== null &&
    evaluation.crossMarket.correctScoreOutcome === selected
  const doubleChanceSupports =
    evaluation.crossMarket.doubleChanceSupportsSelection === true
  const scoreContradicts = evaluation.crossMarket.correctScoreOutcome !== null &&
    evaluation.crossMarket.correctScoreOutcome !== selected
  const doubleChanceContradicts =
    evaluation.crossMarket.doubleChanceSupportsSelection === false
  const supportingModels = Number(scoreSupports) + Number(doubleChanceSupports)
  const explicitContradictions = Number(scoreContradicts) + Number(doubleChanceContradicts)

  const isFulltimeResult = input.marketType === '1x2'
  const eligible =
    input.signalStrength >= marketPolicy.minimumConfidence &&
    input.signalGap >= requiredGap &&
    input.odds >= marketPolicy.minimumOdds &&
    input.odds <= marketPolicy.maximumOdds &&
    evaluation.fixturePredictable === true &&
    evaluation.leaguePerformance.predictivePower !== 'down' &&
    bookmakers >= MODEL_SHORTLIST_POLICY.minimumBookmakers &&
    spread !== null && spread <= MODEL_SHORTLIST_POLICY.maximumRelativePriceSpread &&
    age !== null && age >= 0 && age <= MODEL_SHORTLIST_POLICY.maximumPriceAgeHours &&
    (!isFulltimeResult || supportingModels > 0 || explicitContradictions === 0)

  if (!eligible) return null

  const valueBet = evaluation.valueBet
  const valueSignalAligned = isFulltimeResult && Boolean(
    valueBet?.active &&
    valueBet.outcome === selected &&
    valueBet.fairOdds && valueBet.fairOdds > 1 &&
    valueBet.offeredOdds && valueBet.offeredOdds > valueBet.fairOdds &&
    input.odds > valueBet.fairOdds &&
    evaluation.fairOddsBuffer !== null &&
    evaluation.fairOddsBuffer >= VALUE_STRATEGY_POLICY.minimumFairOddsBuffer
  )
  const confidenceLift = Math.max(0, input.signalStrength - marketPolicy.minimumConfidence)
  const gapLift = Math.max(0, input.signalGap - requiredGap)
  const coverageScore = Math.min(bookmakers / 10, 1)
  const spreadScore = spread === null
    ? 0
    : Math.max(0, 1 - spread / MODEL_SHORTLIST_POLICY.maximumRelativePriceSpread)
  const portfolioScore = confidenceLift * 2.5 + gapLift * 3 + coverageScore * 0.20 + spreadScore * 0.15
  return {
    fixture_id: input.fixtureId,
    home_team: input.homeTeam,
    away_team: input.awayTeam,
    league: input.league,
    kickoff: input.kickoff,
    market_type: input.marketType,
    leading_selection: input.predictedOutcome,
    signal_strength: input.signalStrength,
    signal_gap: input.signalGap,
    verified_price: input.odds,
    bookmaker: input.oddsProvenance.odds_bookmaker_name ?? null,
    bookmakers_checked: bookmakers,
    price_age_hours: age,
    relative_price_spread: spread,
    supporting_models: supportingModels,
    explicit_contradictions: explicitContradictions,
    // This is deliberately stronger than "a VALUEBET row exists". The
    // dedicated price model must be active and aligned, both its quoted offer
    // and our canonical multi-bookmaker quote must clear its baseline, and the
    // canonical gap must reach the registered minimum. Clear favourites with
    // no price disagreement belong in the strong-signal lane instead.
    value_signal_aligned: valueSignalAligned,
    portfolio_score: portfolioScore,
    odds_provenance: input.oddsProvenance,
    strategy_evaluation: evaluation,
  }
}

export function compareModelShortlist(
  a: InternalModelShortlistCandidate,
  b: InternalModelShortlistCandidate,
): number {
  return (
    Number(b.value_signal_aligned) - Number(a.value_signal_aligned) ||
    b.portfolio_score - a.portfolio_score ||
    b.supporting_models - a.supporting_models ||
    b.signal_gap - a.signal_gap ||
    b.signal_strength - a.signal_strength ||
    b.bookmakers_checked - a.bookmakers_checked ||
    (a.relative_price_spread ?? Infinity) - (b.relative_price_spread ?? Infinity) ||
    a.fixture_id - b.fixture_id
  )
}

/** Keep the board genuinely multi-market instead of allowing one abundant
 * lane to occupy every slot. A second pass fills any remaining capacity. */
export function selectDiversifiedModelShortlist(
  candidates: InternalModelShortlistCandidate[],
  maximum: number = MODEL_SHORTLIST_POLICY.maximumSelections,
  maximumPerMarket = 2,
): InternalModelShortlistCandidate[] {
  const ranked = [...candidates].sort(compareModelShortlist)
  const selected: InternalModelShortlistCandidate[] = []
  const marketCounts = new Map<ProductMarket, number>()
  const fixtureIds = new Set<number>()

  for (const candidate of ranked) {
    if (selected.length >= maximum) break
    if (fixtureIds.has(candidate.fixture_id)) continue
    if ((marketCounts.get(candidate.market_type) ?? 0) >= maximumPerMarket) continue
    selected.push(candidate)
    fixtureIds.add(candidate.fixture_id)
    marketCounts.set(candidate.market_type, (marketCounts.get(candidate.market_type) ?? 0) + 1)
  }
  for (const candidate of ranked) {
    if (selected.length >= maximum) break
    if (fixtureIds.has(candidate.fixture_id)) continue
    selected.push(candidate)
    fixtureIds.add(candidate.fixture_id)
  }
  return selected
}

const gemFailureCategories = (reasons: string[]): string[] => {
  const categories: string[] = []
  if (reasons.some(reason => reason.startsWith('fixture_') || reason.startsWith('league_'))) {
    categories.push('reliability')
  }
  if (reasons.some(reason => reason.startsWith('provider_') || reason.startsWith('canonical_'))) {
    categories.push('model_price')
  }
  if (reasons.some(reason => reason.startsWith('cross_market_'))) {
    categories.push('support_models')
  }
  if (reasons.some(reason =>
    reason === 'insufficient_bookmaker_coverage' || reason.startsWith('price_'))) {
    categories.push('price_quality')
  }
  return categories.length ? categories : ['other']
}

const publicGemFailureLabels = (categories: string[]): string[] => {
  const labels: string[] = []
  if (categories.includes('reliability')) {
    labels.push('A stricter Gem reliability check was not satisfied.')
  }
  if (categories.includes('model_price')) {
    labels.push('The complete model-versus-price test did not qualify.')
  }
  if (categories.includes('support_models')) {
    labels.push('Both supporting market models explicitly disagreed.')
  }
  if (categories.includes('price_quality')) {
    labels.push('A stricter Gem price-quality check was not satisfied.')
  }
  return labels.length ? labels : ['It did not pass every Gem qualification gate.']
}

export function toPublicModelShortlistItem(
  candidate: InternalModelShortlistCandidate,
): PublicModelShortlistItem {
  // Snapshots produced before the multi-market schema were 1X2-only and do
  // not contain this field. Preserve their meaning while the hourly cache rolls.
  const marketType = candidate.market_type ?? '1x2'
  const gemGapCategories = marketType === '1x2'
    ? gemFailureCategories(candidate.strategy_evaluation.rejectionReasons)
    : ['market_validation']
  const why = [
    `${marketType.replace(/_/g, ' ')} is the strongest eligible market for this fixture.`,
    `The leading outcome is ${Math.round(candidate.signal_gap * 100)} points clear of the next outcome.`,
    `The displayed price was checked across ${candidate.bookmakers_checked} bookmakers.`,
  ]
  if (candidate.supporting_models > 0) {
    why.push(`${candidate.supporting_models} supporting market model${candidate.supporting_models === 1 ? '' : 's'} agree${candidate.supporting_models === 1 ? 's' : ''}.`)
  } else {
    why.push('No supporting market model explicitly contradicts the leading outcome.')
  }

  return {
    fixture_id: candidate.fixture_id,
    home_team: candidate.home_team,
    away_team: candidate.away_team,
    league: candidate.league,
    kickoff: candidate.kickoff,
    market_type: marketType,
    leading_selection: candidate.leading_selection,
    signal_strength: candidate.signal_strength,
    signal_gap: candidate.signal_gap,
    verified_price: candidate.verified_price,
    bookmaker: candidate.bookmaker,
    bookmakers_checked: candidate.bookmakers_checked,
    price_age_hours: candidate.price_age_hours,
    supporting_models: candidate.supporting_models,
    gem_gap_categories: gemGapCategories,
    why_shortlisted: why,
    why_not_gem: marketType === '1x2'
      ? publicGemFailureLabels(gemGapCategories)
      : ['This market lane remains under forward validation and is not a verified Gem.'],
  }
}

export function toPublicModelShortlist(
  candidates: InternalModelShortlistCandidate[],
): PublicModelShortlistItem[] {
  return candidates.map(toPublicModelShortlistItem)
}
