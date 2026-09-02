import { ODDS_SELECTION_POLICY, type SportMonksOdd, type TeamContext } from './oddsSelection'

export interface AsianHandicapResearchCandidate {
  market_id: 6 | 104
  market_name: string
  side: 'home' | 'away'
  handicap: number
  label: string
  odds: number
  bookmaker: string
  bookmaker_count: number
  price_min: number
  price_max: number
  captured_at: string
  price_provenance: {
    market_id: 6 | 104
    odds_entry_id: number | null
    bookmaker_id: number | null
    bookmaker_name: string
    captured_at: string
    selection_policy: typeof ODDS_SELECTION_POLICY
  }
  model_mass: number
  expected_return_lower: number
  expected_return_upper: number
  robust_positive_edge: boolean
  selection_policy: typeof ODDS_SELECTION_POLICY
  validation_status: 'shadow'
}

const number = (value: unknown): number | null => {
  const parsed = typeof value === 'number' ? value : Number(String(value ?? '').trim())
  return Number.isFinite(parsed) ? parsed : null
}

const probability = (value: unknown): number | null => {
  const parsed = number(value)
  if (parsed === null || parsed < 0) return null
  const normalized = parsed > 1 ? parsed / 100 : parsed
  return normalized >= 0 && normalized <= 1 ? normalized : null
}

const norm = (value: unknown): string => String(value ?? '').toLowerCase().trim().replace(/\s+/g, ' ')

const sideFor = (odd: SportMonksOdd, ctx: TeamContext): 'home' | 'away' | null => {
  const values = [norm(odd.label), norm(odd.name)]
  const home = norm(ctx.homeTeam)
  const away = norm(ctx.awayTeam)
  if (values.some((value) => value === 'home' || value === '1' || (home && value === home))) return 'home'
  if (values.some((value) => value === 'away' || value === '2' || (away && value === away))) return 'away'
  return null
}

const handicapLegs = (line: number): number[] => {
  const quarter = Math.round(line * 4) / 4
  const doubled = Math.abs(quarter * 2)
  return Math.abs(doubled - Math.round(doubled)) < 1e-9
    ? [quarter]
    : [quarter - 0.25, quarter + 0.25]
}

const legProfit = (goalDifference: number, handicap: number, odds: number): number => {
  const adjusted = goalDifference + handicap
  if (adjusted > 0) return odds - 1
  if (adjusted < 0) return -1
  return 0
}

const profit = (goalDifference: number, handicap: number, odds: number): number => {
  const legs = handicapLegs(handicap)
  return legs.reduce((sum, leg) => sum + legProfit(goalDifference, leg, odds), 0) / legs.length
}

export type ScoreBucket =
  | { kind: 'exact'; home: number; away: number; probability: number }
  | { kind: 'home_other' | 'away_other' | 'draw_other'; probability: number }

export const scoreBuckets = (predictions: unknown): ScoreBucket[] => {
  const rows = Array.isArray(predictions) ? predictions : []
  const scores = rows.find((row: any) => row?.type_id === 240)?.predictions?.scores
  if (!scores || typeof scores !== 'object') return []
  const buckets: ScoreBucket[] = []
  for (const [label, raw] of Object.entries(scores)) {
    const p = probability(raw)
    if (p === null || p === 0) continue
    const exact = /^(\d+)-(\d+)$/.exec(label)
    if (exact) buckets.push({ kind: 'exact', home: Number(exact[1]), away: Number(exact[2]), probability: p })
    else if (label === 'Other_1') buckets.push({ kind: 'home_other', probability: p })
    else if (label === 'Other_2') buckets.push({ kind: 'away_other', probability: p })
    else if (label === 'Other_X') buckets.push({ kind: 'draw_other', probability: p })
  }
  return buckets
}

export const validatedScoreDistribution = (
  predictions: unknown,
): { buckets: ScoreBucket[]; rawMass: number } | null => {
  const raw = scoreBuckets(predictions)
  const rawMass = raw.reduce((sum, bucket) => sum + bucket.probability, 0)
  // A score vector is a probability distribution, not an arbitrary score.
  // v2 capped an overflowing mass only after using the unscaled buckets in EV,
  // which could manufacture a return larger than odds - 1. Reject materially
  // invalid vectors and explicitly normalise provider rounding only.
  if (!Number.isFinite(rawMass) || Math.abs(rawMass - 1) > 0.025) return null
  return {
    rawMass,
    buckets: raw.map(bucket => ({
      ...bucket,
      probability: bucket.probability / rawMass,
    })) as ScoreBucket[],
  }
}

const bucketProfitBounds = (
  bucket: ScoreBucket,
  side: 'home' | 'away',
  handicap: number,
  odds: number,
): [number, number] => {
  if (bucket.kind === 'exact') {
    const difference = side === 'home' ? bucket.home - bucket.away : bucket.away - bucket.home
    const settled = profit(difference, handicap, odds)
    return [settled, settled]
  }

  if (bucket.kind === 'draw_other') {
    const settled = profit(0, handicap, odds)
    return [settled, settled]
  }

  const selectedTeamWon =
    (bucket.kind === 'home_other' && side === 'home') ||
    (bucket.kind === 'away_other' && side === 'away')
  const possibleDifferences = selectedTeamWon
    ? [1, 2, 3, 4, 5, 8, 12]
    : [-1, -2, -3, -4, -5, -8, -12]
  const values = possibleDifferences.map((difference) => profit(difference, handicap, odds))
  return [Math.min(...values), Math.max(...values)]
}

interface Quote {
  price: number
  bookmakerId: number | null
  bookmaker: string
  capturedAt: string
  oddId: number | null
}

/**
 * Settlement-aware Asian handicap research. Unknown high-score buckets are
 * carried as lower/upper return bounds instead of being assigned an invented
 * winning margin. A candidate is "robust" only when even the lower bound is
 * positive; all output remains shadow evidence.
 */
export function buildAsianHandicapResearchCandidates(
  predictions: unknown,
  odds: SportMonksOdd[] | null | undefined,
  ctx: TeamContext = {},
): AsianHandicapResearchCandidate[] {
  const distribution = validatedScoreDistribution(predictions)
  if (!distribution) return []
  const { buckets, rawMass: modelMass } = distribution

  const groups = new Map<string, {
    marketId: 6 | 104
    marketName: string
    side: 'home' | 'away'
    handicap: number
    quotes: Quote[]
  }>()

  for (const odd of Array.isArray(odds) ? odds : []) {
    if (odd.market_id !== 6 && odd.market_id !== 104) continue
    if (odd.stopped === true || odd.suspended === true) continue
    const price = number(odd.value)
    const handicap = number(odd.handicap)
    const side = sideFor(odd, ctx)
    const bookmaker = String(odd.bookmaker?.name ?? '').trim()
    const capturedAt = String(odd.latest_bookmaker_update ?? '').trim()
    if (price === null || price <= 1 || handicap === null || !side || !bookmaker || !capturedAt) continue
    const key = `${odd.market_id}:${side}:${handicap}`
    if (!groups.has(key)) {
      groups.set(key, {
        marketId: odd.market_id,
        marketName: odd.market_description ?? (odd.market_id === 6 ? 'Asian Handicap' : 'Alternative Asian Handicap'),
        side,
        handicap,
        quotes: [],
      })
    }
    groups.get(key)!.quotes.push({
      price,
      bookmakerId: odd.bookmaker_id ?? null,
      bookmaker,
      capturedAt,
      oddId: odd.id ?? null,
    })
  }

  const candidates: AsianHandicapResearchCandidate[] = []
  for (const group of Array.from(groups.values())) {
    const latestByBook = new Map<string, Quote>()
    for (const quote of group.quotes) {
      const key = String(quote.bookmakerId ?? quote.bookmaker)
      const previous = latestByBook.get(key)
      if (!previous || quote.capturedAt > previous.capturedAt) latestByBook.set(key, quote)
    }
    const quotes = Array.from(latestByBook.values()).sort((a, b) =>
      a.price - b.price || (a.bookmakerId ?? 0) - (b.bookmakerId ?? 0) || (a.oddId ?? 0) - (b.oddId ?? 0))
    if (!quotes.length) continue
    const chosen = quotes[Math.floor((quotes.length - 1) / 2)]

    let lower = 0
    let upper = 0
    for (const bucket of buckets) {
      const [minProfit, maxProfit] = bucketProfitBounds(
        bucket,
        group.side,
        group.handicap,
        chosen.price,
      )
      lower += bucket.probability * minProfit
      upper += bucket.probability * maxProfit
    }
    // Validated buckets are normalised to exactly one. Unknown "Other"
    // buckets already contribute conservative settlement bounds above.

    candidates.push({
      market_id: group.marketId,
      market_name: group.marketName,
      side: group.side,
      handicap: group.handicap,
      label: `${group.side === 'home' ? ctx.homeTeam || 'Home' : ctx.awayTeam || 'Away'} ${group.handicap > 0 ? '+' : ''}${group.handicap}`,
      odds: chosen.price,
      bookmaker: chosen.bookmaker,
      bookmaker_count: quotes.length,
      price_min: quotes[0].price,
      price_max: quotes[quotes.length - 1].price,
      captured_at: chosen.capturedAt,
      price_provenance: {
        market_id: group.marketId,
        odds_entry_id: chosen.oddId,
        bookmaker_id: chosen.bookmakerId,
        bookmaker_name: chosen.bookmaker,
        captured_at: chosen.capturedAt,
        selection_policy: ODDS_SELECTION_POLICY,
      },
      model_mass: modelMass,
      expected_return_lower: lower,
      expected_return_upper: upper,
      robust_positive_edge: lower > 0.02,
      selection_policy: ODDS_SELECTION_POLICY,
      validation_status: 'shadow',
    })
  }

  return candidates.sort((a, b) =>
    b.expected_return_lower - a.expected_return_lower ||
    b.bookmaker_count - a.bookmaker_count ||
    Math.abs(a.handicap) - Math.abs(b.handicap))
}
