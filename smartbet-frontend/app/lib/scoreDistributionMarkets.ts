import { validatedScoreDistribution, type ScoreBucket } from './asianHandicapResearch'
import { ODDS_SELECTION_POLICY, type SportMonksOdd, type TeamContext } from './oddsSelection'

export interface ScoreDistributionMarketCandidate {
  strategy_key: 'asian-goal-line-score-distribution' | 'team-total-score-distribution'
  strategy_version: 'v3'
  market: 'asian_goal_line' | 'team_total_goals'
  market_id: 7 | 86 | 105
  market_name: string
  side: 'over' | 'under' | 'home_over' | 'home_under' | 'away_over' | 'away_under'
  handicap: number
  label: string
  odds: number
  bookmaker: string
  bookmaker_count: number
  price_min: number
  price_max: number
  captured_at: string
  price_provenance: {
    market_id: 7 | 86 | 105
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
  validation_status: 'shadow'
}

interface Quote {
  price: number
  bookmakerId: number | null
  bookmaker: string
  capturedAt: string
  oddId: number | null
}

const finite = (value: unknown): number | null => {
  const parsed = typeof value === 'number' ? value : Number(String(value ?? '').trim())
  return Number.isFinite(parsed) ? parsed : null
}

const norm = (value: unknown): string => String(value ?? '').trim().toLowerCase()

const lineFrom = (value: unknown): number | null => {
  const cleaned = String(value ?? '').trim().replace(/^(over|under)\s+/i, '')
  const parts = cleaned.split(',').map((part) => Number(part.trim()))
  if (!parts.length || parts.length > 2 || parts.some((part) => !Number.isFinite(part))) return null
  if (parts.length === 2 && Math.abs(parts[0] - parts[1]) !== 0.5) return null
  const line = parts.reduce((sum, part) => sum + part, 0) / parts.length
  return Math.round(line * 4) / 4
}

const lineLegs = (line: number): number[] => {
  const quarter = Math.round(line * 4) / 4
  return Math.abs(quarter * 2 - Math.round(quarter * 2)) < 1e-9
    ? [quarter]
    : [quarter - 0.25, quarter + 0.25]
}

const totalProfit = (goals: number, side: 'over' | 'under', line: number, odds: number): number => {
  const values = lineLegs(line).map((leg) => {
    const difference = side === 'over' ? goals - leg : leg - goals
    return difference > 0 ? odds - 1 : difference < 0 ? -1 : 0
  })
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

const totalPossibilities = (bucket: ScoreBucket): number[] => {
  if (bucket.kind === 'exact') return [bucket.home + bucket.away]
  if (bucket.kind === 'draw_other') return [8, 10, 12, 16, 20]
  return [4, 5, 6, 7, 8, 10, 12, 16, 20]
}

const teamGoalPossibilities = (bucket: ScoreBucket, team: 'home' | 'away'): number[] => {
  if (bucket.kind === 'exact') return [team === 'home' ? bucket.home : bucket.away]
  if (bucket.kind === 'draw_other') return [4, 5, 6, 8, 10, 12]
  const selectedWinner =
    (bucket.kind === 'home_other' && team === 'home') ||
    (bucket.kind === 'away_other' && team === 'away')
  return selectedWinner
    ? [4, 5, 6, 8, 10, 12]
    : [0, 1, 2, 3, 4, 6, 8, 10, 11]
}

const quoteGroups = (
  odds: SportMonksOdd[] | null | undefined,
  marketIds: readonly number[],
  sideFor: (odd: SportMonksOdd) => string | null,
) => {
  const groups = new Map<string, {
    marketId: 7 | 86 | 105
    marketName: string
    side: string
    line: number
    quotes: Quote[]
  }>()
  for (const odd of Array.isArray(odds) ? odds : []) {
    if (!marketIds.includes(Number(odd.market_id)) || odd.stopped === true || odd.suspended === true) continue
    const price = finite(odd.value)
    const rawLine = String(odd.total ?? '').trim() || odd.name
    const line = lineFrom(rawLine)
    const side = sideFor(odd)
    const bookmaker = String(odd.bookmaker?.name ?? '').trim()
    const capturedAt = String(odd.latest_bookmaker_update ?? '').trim()
    if (price === null || price <= 1 || line === null || !side || !bookmaker || !capturedAt) continue
    const marketId = odd.market_id as 7 | 86 | 105
    const key = `${marketId}:${side}:${line}`
    if (!groups.has(key)) {
      groups.set(key, {
        marketId,
        marketName: odd.market_description ?? `Market ${marketId}`,
        side,
        line,
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
  return groups
}

const lowerMedian = (quotes: Quote[]): { chosen: Quote; quotes: Quote[] } | null => {
  const latest = new Map<string, Quote>()
  for (const quote of quotes) {
    const key = String(quote.bookmakerId ?? quote.bookmaker)
    const previous = latest.get(key)
    if (!previous || quote.capturedAt > previous.capturedAt) latest.set(key, quote)
  }
  const rows = Array.from(latest.values()).sort((a, b) =>
    a.price - b.price || (a.bookmakerId ?? 0) - (b.bookmakerId ?? 0) || (a.oddId ?? 0) - (b.oddId ?? 0))
  if (!rows.length) return null
  return { chosen: rows[Math.floor((rows.length - 1) / 2)], quotes: rows }
}

const bounds = (
  buckets: ScoreBucket[],
  modelMass: number,
  possibilities: (bucket: ScoreBucket) => number[],
  side: 'over' | 'under',
  line: number,
  odds: number,
): [number, number] => {
  let lower = 0
  let upper = 0
  for (const bucket of buckets) {
    const profits = possibilities(bucket).map((goals) => totalProfit(goals, side, line, odds))
    lower += bucket.probability * Math.min(...profits)
    upper += bucket.probability * Math.max(...profits)
  }
  const missingMass = Math.max(0, 1 - modelMass)
  return [lower - missingMass, upper + missingMass * (odds - 1)]
}

const baseCandidate = (
  group: ReturnType<typeof quoteGroups> extends Map<string, infer T> ? T : never,
  chosen: Quote,
  quotes: Quote[],
  modelMass: number,
  edgeBounds: [number, number],
) => ({
  market_id: group.marketId,
  market_name: group.marketName,
  handicap: group.line,
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
    selection_policy: ODDS_SELECTION_POLICY as typeof ODDS_SELECTION_POLICY,
  },
  model_mass: modelMass,
  expected_return_lower: edgeBounds[0],
  expected_return_upper: edgeBounds[1],
  robust_positive_edge: edgeBounds[0] > 0.02,
  validation_status: 'shadow' as const,
})

/** Bounded whole/half/quarter Asian total candidates from exact-score mass. */
export function buildAsianGoalLineResearchCandidates(
  predictions: unknown,
  odds: SportMonksOdd[] | null | undefined,
): ScoreDistributionMarketCandidate[] {
  const distribution = validatedScoreDistribution(predictions)
  if (!distribution) return []
  const { buckets, rawMass: modelMass } = distribution
  const groups = quoteGroups(odds, [7, 105], (odd) => {
    const side = norm(odd.label || odd.name)
    return side === 'over' || side === 'under' ? side : null
  })
  const out: ScoreDistributionMarketCandidate[] = []
  for (const group of Array.from(groups.values())) {
    const selected = lowerMedian(group.quotes)
    if (!selected || (group.side !== 'over' && group.side !== 'under')) continue
    const edge = bounds(
      buckets, 1, totalPossibilities, group.side, group.line, selected.chosen.price,
    )
    out.push({
      strategy_key: 'asian-goal-line-score-distribution',
      strategy_version: 'v3',
      market: 'asian_goal_line',
      side: group.side,
      label: `${group.side === 'over' ? 'Over' : 'Under'} ${group.line}`,
      ...baseCandidate(group, selected.chosen, selected.quotes, modelMass, edge),
    })
  }
  return out.sort((a, b) => b.expected_return_lower - a.expected_return_lower)
}

/** Conservative home/away team-total candidates from the same score model. */
export function buildTeamTotalResearchCandidates(
  predictions: unknown,
  odds: SportMonksOdd[] | null | undefined,
  ctx: TeamContext = {},
): ScoreDistributionMarketCandidate[] {
  const distribution = validatedScoreDistribution(predictions)
  if (!distribution) return []
  const { buckets, rawMass: modelMass } = distribution
  const groups = quoteGroups(odds, [86], (odd) => {
    const team = norm(odd.label) === '1' ? 'home' : norm(odd.label) === '2' ? 'away' : null
    const side = /^over\b/i.test(String(odd.total ?? ''))
      ? 'over'
      : /^under\b/i.test(String(odd.total ?? '')) ? 'under' : null
    return team && side ? `${team}_${side}` : null
  })
  const out: ScoreDistributionMarketCandidate[] = []
  for (const group of Array.from(groups.values())) {
    const selected = lowerMedian(group.quotes)
    const [team, side] = group.side.split('_') as ['home' | 'away', 'over' | 'under']
    if (!selected || !team || !side) continue
    const edge = bounds(
      buckets,
      1,
      (bucket) => teamGoalPossibilities(bucket, team),
      side,
      group.line,
      selected.chosen.price,
    )
    const teamName = team === 'home' ? ctx.homeTeam || 'Home' : ctx.awayTeam || 'Away'
    out.push({
      strategy_key: 'team-total-score-distribution',
      strategy_version: 'v3',
      market: 'team_total_goals',
      side: `${team}_${side}`,
      label: `${teamName} ${side === 'over' ? 'Over' : 'Under'} ${group.line}`,
      ...baseCandidate(group, selected.chosen, selected.quotes, modelMass, edge),
    })
  }
  return out.sort((a, b) => b.expected_return_lower - a.expected_return_lower)
}
