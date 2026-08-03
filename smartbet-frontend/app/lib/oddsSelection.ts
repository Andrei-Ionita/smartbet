/**
 * Deterministic odds selection.
 *
 * WHY THIS MODULE EXISTS
 * ----------------------
 * The previous implementation matched odds with substring tests such as
 * `odd.name?.includes('2.5')`. SportMonks returns ~490 odds entries per fixture,
 * ~38 of which contain the string "2.5" across at least seven *different*
 * markets — including `market_id 53` ("2nd Half Goals"). The old loop accepted
 * the first such entry in arbitrary API order, so a full-time Over 2.5 pick
 * could be priced with a SECOND-HALF Over 2.5 quote (legitimately ~3.50 instead
 * of ~1.60) and then graded against full-time goals.
 *
 * The 2026-07-29 production audit found this inflated the recommended
 * portfolio's ROI from -4.90% to +10.61%. See
 * `docs/audit/gem-selector-diagnostics-2026-07-29.md`.
 *
 * Every selection here is therefore keyed on explicit identifiers — never on
 * substrings — and returns full provenance so any published price can be
 * independently audited.
 */

export type ProductMarket = '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'

/** A single SportMonks odds entry (only the fields we rely on). */
export interface SportMonksOdd {
  id?: number | null
  fixture_id?: number | null
  market_id?: number | null
  bookmaker_id?: number | null
  label?: string | null
  value?: string | number | null
  name?: string | null
  total?: string | number | null
  handicap?: string | null
  market_description?: string | null
  stopped?: boolean | null
  suspended?: boolean | null
  latest_bookmaker_update?: string | null
  /** Present when the request includes `odds.bookmaker`. */
  bookmaker?: { id?: number | null; name?: string | null } | null
}

/** Everything needed to audit a published price after the fact. */
export interface OddsProvenance {
  odds: number
  odds_market_id: number
  odds_market_description: string | null
  odds_line: number | null
  odds_label: string
  odds_bookmaker_id: number | null
  odds_bookmaker_name: string | null
  odds_bookmaker_count: number
  odds_min: number
  odds_max: number
  odds_captured_at: string | null
  odds_fixture_id: number | null
  odds_entry_id: number | null
  odds_selection_policy: string
}

export type OddsUnavailableReason =
  | 'no_odds_payload'
  | 'market_not_offered'
  | 'line_not_offered'
  | 'outcome_not_offered'
  | 'all_entries_stopped'
  | 'no_valid_price'

export type OddsResult =
  | { ok: true; provenance: OddsProvenance }
  | { ok: false; reason: OddsUnavailableReason }

/**
 * Deterministic bookmaker policy.
 *
 * We take the LOWER MEDIAN of every valid quote for the exact market, line and
 * outcome. Rationale:
 *   - it is an actually-quoted price from a real bookmaker (not a synthetic
 *     average), so it was genuinely obtainable;
 *   - it is robust to a single mispriced or stale book, which is precisely the
 *     failure mode that produced the 2026-07-29 defect;
 *   - it is conservative: with an even number of books we take the lower of the
 *     two middle prices, never the better one;
 *   - it is fully deterministic given the same payload.
 *
 * We deliberately do NOT take the best available price. Publishing the maximum
 * quote across all books systematically captures bookmaker errors and would
 * overstate both EV and realised ROI.
 */
export const ODDS_SELECTION_POLICY = 'lower_median_v1'

/** Markets whose quotes we accept, keyed by our product market. */
interface MarketSpec {
  /** Human-readable name of the bet this prices. */
  description: string
  /** SportMonks market_ids that genuinely price this bet. Order is irrelevant. */
  marketIds: number[]
  /** Exact goal line required (e.g. 2.5). `null` for markets without a line. */
  requiredLine: number | null
  /** Every predicted outcome this product market can emit. */
  outcomes: string[]
  /** Build the set of acceptable labels for a predicted outcome. */
  labelsFor: (outcome: string, ctx: TeamContext) => string[]
  /**
   * SportMonks markets that price a DIFFERENT bet but are easy to confuse with
   * this one. Documented per market, and asserted in table-driven tests, so a
   * future edit cannot quietly widen the allowlist.
   */
  rejects: { marketId: number; description: string }[]
}

/**
 * Markets that must never price a full-match goals bet. Kept as one named list
 * because several product markets share the same confusable neighbours.
 */
const GOALS_CONFUSABLES = [
  { marketId: 28, description: '1st Half Goals' },
  { marketId: 53, description: '2nd Half Goals' },
  { marketId: 37, description: 'Result / Total Goals' },
  { marketId: 81, description: 'Alternative Total Goals' },
  // Observed live on 2026-08-03 (fixtures 19730342, 19635928): the retired
  // fixture-detail matcher resolved a full-match Over 2.5 to this combined
  // market. It prices a total AND a BTTS leg together — a different bet.
  { marketId: 82, description: 'Total Goals / Both Teams to Score' },
  { marketId: 86, description: 'Team Total Goals' },
  { marketId: 105, description: 'Alternative Goal Line (combined lines)' },
  { marketId: 107, description: 'Alternative 1st Half Goal Line' },
]

export interface TeamContext {
  homeTeam?: string | null
  awayTeam?: string | null
}

const norm = (s: unknown): string =>
  String(s ?? '')
    .toLowerCase()
    .replace(/\//g, ' or ')
    .replace(/[^a-z0-9. ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

/**
 * market_id 80 = "Goals Over/Under" (the canonical full-time total).
 * market_id  7 = "Goal Line" (Asian total). At a .5 line these are economically
 *                identical — no push or half-win is possible — and market 7 has
 *                materially wider bookmaker coverage (4 books vs 1 on the
 *                fixture audited). Accepting both is a deliberate, documented
 *                policy; `odds_market_id` records which one priced each pick.
 *
 * Explicitly EXCLUDED (all contain "2.5" and all previously collided):
 *   28  1st Half Goals            37  Result / Total Goals
 *   53  2nd Half Goals            81  Alternative Total Goals
 *   82  Total Goals / BTTS        86  Team Total Goals
 *  105  Alternative Goal Line    107  Alternative 1st Half Goal Line
 */
const GOALS_OVER_UNDER_MARKETS = [80, 7]

export const MARKET_SPECS: Record<ProductMarket, MarketSpec> = {
  'over_under_2.5': {
    description: 'Full-match total goals, 2.5 line',
    marketIds: GOALS_OVER_UNDER_MARKETS,
    requiredLine: 2.5,
    outcomes: ['over', 'under'],
    labelsFor: (outcome) => (norm(outcome) === 'over' ? ['over'] : ['under']),
    rejects: GOALS_CONFUSABLES,
  },
  '1x2': {
    // market_id 1 = "Fulltime Result" (a.k.a. "Full Time Result").
    description: 'Full-match result',
    marketIds: [1],
    requiredLine: null,
    outcomes: ['home', 'draw', 'away'],
    labelsFor: (outcome) => [norm(outcome)],
    rejects: [
      { marketId: 6, description: '1st Half Result' },
      { marketId: 37, description: 'Result / Total Goals' },
      { marketId: 126, description: 'Result / Both Teams To Score' },
    ],
  },
  btts: {
    // market_id 14 = "Both Teams to Score". 15 and 16 are the 1st/2nd half
    // variants and must never match.
    description: 'Both teams to score, full match',
    marketIds: [14],
    requiredLine: null,
    outcomes: ['yes', 'no'],
    labelsFor: (outcome) => (norm(outcome) === 'yes' ? ['yes'] : ['no']),
    rejects: [
      { marketId: 15, description: 'Both Teams to Score in 1st Half' },
      { marketId: 16, description: 'Both Teams to Score in 2nd Half' },
      { marketId: 125, description: 'BTTS in Both Halves' },
      { marketId: 88, description: 'Result / BTTS combination' },
    ],
  },
  double_chance: {
    // market_id 2 = "Double Chance". 47 is "Half Time Double Chance".
    description: 'Double chance, full match',
    marketIds: [2],
    requiredLine: null,
    outcomes: ['1X', 'X2', '12'],
    rejects: [
      { marketId: 47, description: 'Half Time Double Chance' },
      { marketId: 122, description: 'Double Chance / BTTS combination' },
    ],
    labelsFor: (outcome, ctx) => {
      const home = norm(ctx.homeTeam)
      const away = norm(ctx.awayTeam)
      const pair = (a: string, b: string) => [`${a} or ${b}`, `${b} or ${a}`]
      switch (norm(outcome)) {
        case '1x':
          return [...pair('home', 'draw'), ...(home ? pair(home, 'draw') : [])]
        case 'x2':
          return [...pair('draw', 'away'), ...(away ? pair(away, 'draw') : [])]
        case '12':
          return [
            ...pair('home', 'away'),
            ...(home && away ? pair(home, away) : []),
          ]
        default:
          return []
      }
    },
  },
}

/** Parse a SportMonks line/total. Handles "2.5", 2.5, "3", and combined
 *  Asian lines like "2.5, 3.0" (which are NOT a plain 2.5 line -> reject). */
function parseLine(total: unknown): number | null {
  if (total === null || total === undefined) return null
  const raw = String(total).trim()
  if (raw === '' || raw.toLowerCase() === 'none') return null
  // Combined/split lines ("2.5, 3.0") are a different bet — never a plain line.
  if (raw.includes(',')) return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

function parsePrice(value: unknown): number | null {
  if (value === null || value === undefined) return null
  const n = typeof value === 'number' ? value : Number(String(value).trim())
  // A price of 1.0 or below implies no return; treat as absent rather than
  // silently producing a negative-EV pick.
  return Number.isFinite(n) && n > 1 ? n : null
}

function isLive(o: SportMonksOdd): boolean {
  return o.stopped !== true && o.suspended !== true
}

/**
 * Select the price for one product market + outcome.
 *
 * Selection is keyed on market_id, exact line and exact (normalised) label.
 * API array order NEVER affects the result.
 */
export function selectOdds(
  odds: SportMonksOdd[] | null | undefined,
  market: ProductMarket,
  outcome: string,
  ctx: TeamContext = {},
): OddsResult {
  if (!Array.isArray(odds) || odds.length === 0) {
    return { ok: false, reason: 'no_odds_payload' }
  }

  const spec = MARKET_SPECS[market]
  const wantedLabels = spec.labelsFor(outcome, ctx).map(norm).filter(Boolean)

  const inMarket = odds.filter(
    (o) => typeof o.market_id === 'number' && spec.marketIds.indexOf(o.market_id) !== -1,
  )
  if (inMarket.length === 0) return { ok: false, reason: 'market_not_offered' }

  const onLine =
    spec.requiredLine === null
      ? inMarket
      : inMarket.filter((o) => parseLine(o.total) === spec.requiredLine)
  if (onLine.length === 0) return { ok: false, reason: 'line_not_offered' }

  // Exact label equality after normalisation — never substring containment.
  const onOutcome = onLine.filter((o) => wantedLabels.indexOf(norm(o.label)) !== -1)
  if (onOutcome.length === 0) return { ok: false, reason: 'outcome_not_offered' }

  const live = onOutcome.filter(isLive)
  if (live.length === 0) return { ok: false, reason: 'all_entries_stopped' }

  const priced = live
    .map((o) => ({ odd: o, price: parsePrice(o.value) }))
    .filter((p): p is { odd: SportMonksOdd; price: number } => p.price !== null)
  if (priced.length === 0) return { ok: false, reason: 'no_valid_price' }

  // Total ordering => deterministic regardless of payload order.
  priced.sort(
    (a, b) =>
      a.price - b.price ||
      (a.odd.bookmaker_id ?? 0) - (b.odd.bookmaker_id ?? 0) ||
      (a.odd.id ?? 0) - (b.odd.id ?? 0),
  )

  const chosen = priced[Math.floor((priced.length - 1) / 2)] // lower median
  const prices = priced.map((p) => p.price)

  return {
    ok: true,
    provenance: {
      odds: chosen.price,
      odds_market_id: chosen.odd.market_id as number,
      odds_market_description: chosen.odd.market_description ?? null,
      odds_line: spec.requiredLine,
      odds_label: String(chosen.odd.label ?? ''),
      odds_bookmaker_id: chosen.odd.bookmaker_id ?? null,
      // Requires the `odds.bookmaker` include. A verified record demands it —
      // if the include is ever dropped this goes null and the row is correctly
      // classified missing_provenance rather than silently accepted.
      odds_bookmaker_name: chosen.odd.bookmaker?.name ?? null,
      odds_bookmaker_count: priced.length,
      odds_min: prices[0],
      odds_max: prices[prices.length - 1],
      odds_captured_at: chosen.odd.latest_bookmaker_update ?? null,
      odds_fixture_id: chosen.odd.fixture_id ?? null,
      odds_entry_id: chosen.odd.id ?? null,
      odds_selection_policy: ODDS_SELECTION_POLICY,
    },
  }
}
