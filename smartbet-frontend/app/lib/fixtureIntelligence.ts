import {
  canPublishPrice,
  type CanonicalPriceFields,
  type OddsProvenance,
  type OddsUnavailableReason,
  type ProductMarket,
} from './marketPricing'

export type IntelligenceMarketKey = ProductMarket

export interface IntelligenceOutcomeInput extends CanonicalPriceFields {
  key: string
  label: string
  provider_probability: number | null
  odds: number | null
  bookmaker: string | null
  odds_provenance?: OddsProvenance | null
  odds_unavailable_reason?: OddsUnavailableReason | string
}

export interface IntelligenceOutcome extends IntelligenceOutcomeInput {
  implied_probability: number | null
  market_probability: number | null
  provider_market_difference: number | null
  price_age_hours: number | null
  bookmaker_count: number | null
  price_min: number | null
  price_max: number | null
}

export interface IntelligenceMarketInput {
  key: IntelligenceMarketKey
  label: string
  /** Whether the listed outcomes form one mutually-exclusive price board. */
  probability_kind: 'distribution' | 'overlapping'
  outcomes: IntelligenceOutcomeInput[]
}

export interface IntelligenceMarket {
  key: IntelligenceMarketKey
  label: string
  probability_kind: 'distribution' | 'overlapping'
  outcomes: IntelligenceOutcome[]
  provider_leader: string | null
  market_leader: string | null
  leader_agreement: boolean | null
  price_board_complete: boolean
  bookmaker_margin: number | null
}

export interface FixtureIntelligence {
  generated_at: string
  model_source: 'provider'
  markets: IntelligenceMarket[]
  data_quality: {
    provider_markets_available: number
    complete_price_boards: number
    verified_prices: number
    total_prices: number
    freshest_price_age_hours: number | null
    limitations: IntelligenceLimitation[]
  }
}

export type IntelligenceLimitation =
  | 'provider_probabilities_incomplete'
  | 'verified_price_board_incomplete'
  | 'canonical_board_not_single_bookmaker'
  | 'reference_views_not_value_verdict'

const finiteProbability = (value: number | null | undefined): number | null =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
    ? value
    : null

const ageHours = (capturedAt: string | null | undefined, evaluatedAt: Date): number | null => {
  if (!capturedAt) return null
  const parsed = Date.parse(capturedAt.replace(' ', 'T') + (/z|[+-]\d\d:?\d\d$/i.test(capturedAt) ? '' : 'Z'))
  if (!Number.isFinite(parsed)) return null
  return Math.max(0, (evaluatedAt.getTime() - parsed) / 3_600_000)
}

const leader = (
  outcomes: IntelligenceOutcome[],
  field: 'provider_probability' | 'market_probability',
): string | null => {
  const available = outcomes.filter((outcome) => outcome[field] !== null)
  if (!available.length) return null
  return [...available].sort((a, b) => (b[field] ?? -1) - (a[field] ?? -1))[0].key
}

/**
 * Build one transparent market comparison.
 *
 * `market_probability` is a margin-removed view of a COMPLETE mutually
 * exclusive bookmaker board. It is not BetGlitch's probability and it is not
 * computed for Double Chance, whose overlapping outcomes do not form a
 * probability distribution.
 */
export function buildIntelligenceMarket(
  input: IntelligenceMarketInput,
  evaluatedAt = new Date(),
): IntelligenceMarket {
  const verified = input.outcomes.map((outcome) => canPublishPrice(outcome))
  const boardComplete = input.probability_kind === 'distribution' && verified.every(Boolean)
  const rawImplied = input.outcomes.map((outcome, index) =>
    verified[index] && outcome.odds && outcome.odds > 1 ? 1 / outcome.odds : null,
  )
  const impliedTotal = boardComplete
    ? rawImplied.reduce<number>((sum, value) => sum + (value ?? 0), 0)
    : null

  const outcomes: IntelligenceOutcome[] = input.outcomes.map((outcome, index) => {
    const provenance = outcome.odds_provenance
    const implied = rawImplied[index]
    const marketProbability =
      implied !== null && impliedTotal !== null && impliedTotal > 0
        ? implied / impliedTotal
        : null
    const providerProbability = finiteProbability(outcome.provider_probability)

    return {
      ...outcome,
      provider_probability: providerProbability,
      implied_probability: implied,
      market_probability: marketProbability,
      provider_market_difference:
        providerProbability !== null && marketProbability !== null
          ? providerProbability - marketProbability
          : null,
      price_age_hours: ageHours(provenance?.odds_captured_at, evaluatedAt),
      bookmaker_count: provenance?.odds_bookmaker_count ?? null,
      price_min: provenance?.odds_min ?? null,
      price_max: provenance?.odds_max ?? null,
    }
  })

  const providerLeader = leader(outcomes, 'provider_probability')
  const marketLeader = leader(outcomes, 'market_probability')

  return {
    key: input.key,
    label: input.label,
    probability_kind: input.probability_kind,
    outcomes,
    provider_leader: providerLeader,
    market_leader: marketLeader,
    leader_agreement:
      providerLeader !== null && marketLeader !== null
        ? providerLeader === marketLeader
        : null,
    price_board_complete: boardComplete,
    bookmaker_margin: impliedTotal !== null ? impliedTotal - 1 : null,
  }
}

export function buildFixtureIntelligence(
  inputs: IntelligenceMarketInput[],
  evaluatedAt = new Date(),
): FixtureIntelligence {
  const markets = inputs.map((input) => buildIntelligenceMarket(input, evaluatedAt))
  const outcomes = markets.flatMap((market) => market.outcomes)
  const verifiedOutcomes = outcomes.filter((outcome) => canPublishPrice(outcome))
  const ages = verifiedOutcomes
    .map((outcome) => outcome.price_age_hours)
    .filter((age): age is number => age !== null)

  const limitations: IntelligenceLimitation[] = []
  if (markets.some((market) => !market.outcomes.some((outcome) => outcome.provider_probability !== null))) {
    limitations.push('provider_probabilities_incomplete')
  }
  if (markets.some((market) => market.probability_kind === 'distribution' && !market.price_board_complete)) {
    limitations.push('verified_price_board_incomplete')
  }
  if (markets.some((market) => market.price_board_complete)) {
    limitations.push('canonical_board_not_single_bookmaker')
  }
  limitations.push('reference_views_not_value_verdict')

  return {
    generated_at: evaluatedAt.toISOString(),
    model_source: 'provider',
    markets,
    data_quality: {
      provider_markets_available: markets.filter((market) =>
        market.outcomes.some((outcome) => outcome.provider_probability !== null),
      ).length,
      complete_price_boards: markets.filter((market) => market.price_board_complete).length,
      verified_prices: verifiedOutcomes.length,
      total_prices: outcomes.length,
      freshest_price_age_hours: ages.length ? Math.min(...ages) : null,
      limitations,
    },
  }
}

export interface PersonalPriceResult {
  personal_probability: number
  personal_fair_odds: number
  offered_odds: number | null
  break_even_probability: number | null
  probability_cushion: number | null
  price_advantage: number | null
  assessment: 'above_personal_price' | 'below_personal_price' | 'no_price'
}

/** Pure calculator: the probability belongs to the user, never BetGlitch. */
export function calculatePersonalPrice(
  probabilityPercent: number,
  offeredOdds: number | null,
): PersonalPriceResult | null {
  if (!Number.isFinite(probabilityPercent) || probabilityPercent <= 0 || probabilityPercent >= 100) {
    return null
  }

  const probability = probabilityPercent / 100
  const fairOdds = 1 / probability
  const hasPrice = typeof offeredOdds === 'number' && Number.isFinite(offeredOdds) && offeredOdds > 1
  const breakEven = hasPrice ? 1 / offeredOdds : null
  const advantage = hasPrice ? offeredOdds / fairOdds - 1 : null

  return {
    personal_probability: probability,
    personal_fair_odds: fairOdds,
    offered_odds: hasPrice ? offeredOdds : null,
    break_even_probability: breakEven,
    probability_cushion: breakEven !== null ? probability - breakEven : null,
    price_advantage: advantage,
    assessment: !hasPrice
      ? 'no_price'
      : offeredOdds >= fairOdds
        ? 'above_personal_price'
        : 'below_personal_price',
  }
}

/** SportMonks form may arrive as a compact string or an ordered form record array. */
export function formatFixtureForm(value: unknown): string | null {
  const letters: string[] = []

  if (typeof value === 'string') {
    letters.push(...(value.toUpperCase().match(/[WDL]/g) ?? []))
  } else if (Array.isArray(value)) {
    for (const entry of value) {
      if (!entry || typeof entry !== 'object') continue
      const form = (entry as { form?: unknown }).form
      if (typeof form === 'string') letters.push(...(form.toUpperCase().match(/[WDL]/g) ?? []))
    }
  } else if (value && typeof value === 'object') {
    const form = (value as { form?: unknown }).form
    if (typeof form === 'string') letters.push(...(form.toUpperCase().match(/[WDL]/g) ?? []))
  }

  return letters.length ? letters.slice(-5).join(' ') : null
}
