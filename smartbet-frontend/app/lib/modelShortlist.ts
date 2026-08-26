import type { OddsProvenance } from './oddsSelection'
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

export interface ModelShortlistInput {
  fixtureId: number
  homeTeam: string
  awayTeam: string
  league: string
  kickoff: string
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
  const selected = selectedOutcome(input.predictedOutcome)
  const requiredGap = selected === 'draw'
    ? MODEL_SHORTLIST_POLICY.minimumGap.draw
    : MODEL_SHORTLIST_POLICY.minimumGap.other
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

  const eligible =
    input.signalStrength >= MODEL_SHORTLIST_POLICY.confidenceFloor &&
    input.signalGap >= requiredGap &&
    evaluation.fixturePredictable === true &&
    evaluation.leaguePerformance.predictivePower !== 'down' &&
    bookmakers >= MODEL_SHORTLIST_POLICY.minimumBookmakers &&
    spread !== null && spread <= MODEL_SHORTLIST_POLICY.maximumRelativePriceSpread &&
    age !== null && age >= 0 && age <= MODEL_SHORTLIST_POLICY.maximumPriceAgeHours &&
    (supportingModels > 0 || explicitContradictions === 0)

  if (!eligible) return null

  const valueBet = evaluation.valueBet
  const valueSignalAligned = Boolean(
    valueBet?.active &&
    valueBet.outcome === selected &&
    valueBet.fairOdds && valueBet.fairOdds > 1 &&
    valueBet.offeredOdds && valueBet.offeredOdds > valueBet.fairOdds &&
    input.odds > valueBet.fairOdds &&
    evaluation.fairOddsBuffer !== null &&
    evaluation.fairOddsBuffer >= VALUE_STRATEGY_POLICY.minimumFairOddsBuffer
  )
  return {
    fixture_id: input.fixtureId,
    home_team: input.homeTeam,
    away_team: input.awayTeam,
    league: input.league,
    kickoff: input.kickoff,
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
    b.supporting_models - a.supporting_models ||
    b.signal_gap - a.signal_gap ||
    b.signal_strength - a.signal_strength ||
    b.bookmakers_checked - a.bookmakers_checked ||
    (a.relative_price_spread ?? Infinity) - (b.relative_price_spread ?? Infinity) ||
    a.fixture_id - b.fixture_id
  )
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
  const gemGapCategories = gemFailureCategories(
    candidate.strategy_evaluation.rejectionReasons,
  )
  const why = [
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
    why_not_gem: publicGemFailureLabels(gemGapCategories),
  }
}

export function toPublicModelShortlist(
  candidates: InternalModelShortlistCandidate[],
): PublicModelShortlistItem[] {
  return candidates.map(toPublicModelShortlistItem)
}
