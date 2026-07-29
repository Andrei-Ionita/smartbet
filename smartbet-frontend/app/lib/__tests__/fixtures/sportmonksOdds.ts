/**
 * Test fixtures reproducing the exact SportMonks collision patterns that caused
 * the 2026-07-29 odds-capture defect.
 *
 * Derived from the live payload for fixture 19714700 (SC Cambuur v Excelsior),
 * which returned 491 odds entries — 38 of them containing the string "2.5"
 * across seven different markets. Rather than vendor a bulk third-party payload,
 * this fixture keeps a curated subset that preserves every collision pattern,
 * with the real market_ids, market_descriptions, labels and prices.
 *
 * Market reference (confirmed against `market_description`):
 *    1  Fulltime Result                 <- correct for 1x2
 *    2  Double Chance                   <- correct for double_chance
 *    7  Goal Line                       <- correct for O/U 2.5 (Asian, .5 line)
 *   14  Both Teams to Score             <- correct for btts
 *   15  Both Teams to Score in 1st Half   COLLISION
 *   16  Both Teams to Score in 2nd Half   COLLISION
 *   28  1st Half Goals                    COLLISION
 *   37  Result / Total Goals              COLLISION
 *   47  Half Time Double Chance           COLLISION
 *   53  2nd Half Goals                    COLLISION  <- produced the 3.50 quote
 *   80  Goals Over/Under                <- correct for O/U 2.5 (canonical)
 *   86  Team Total Goals                  COLLISION
 *  105  Alternative Goal Line             COLLISION (combined lines "2.5, 3.0")
 *  107  Alternative 1st Half Goal Line    COLLISION
 */
import type { SportMonksOdd } from '../../oddsSelection'

let nextId = 1000
const odd = (o: Partial<SportMonksOdd>): SportMonksOdd => ({
  id: nextId++,
  fixture_id: 19714700,
  stopped: false,
  suspended: false,
  name: null,
  total: null,
  market_description: null,
  latest_bookmaker_update: '2026-07-29 11:16:22',
  ...o,
})

/** The genuine full-time Over/Under 2.5 goals quotes. */
export const CORRECT_OU_25: SportMonksOdd[] = [
  odd({ market_id: 80, market_description: 'Goals Over/Under', label: 'Over', name: '2.5', total: '2.5', value: '1.61', bookmaker_id: 2 }),
  odd({ market_id: 80, market_description: 'Goals Over/Under', label: 'Under', name: '2.5', total: '2.5', value: '2.25', bookmaker_id: 2 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: 'Over', total: '2.5', value: '1.60', bookmaker_id: 32 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: 'Over', total: '2.5', value: '1.60', bookmaker_id: 13 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: 'Over', total: '2.5', value: '1.58', bookmaker_id: 28 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: 'Over', total: '2.5', value: '1.62', bookmaker_id: 64 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Under', name: 'Under', total: '2.5', value: '2.20', bookmaker_id: 32 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Under', name: 'Under', total: '2.5', value: '2.29', bookmaker_id: 64 }),
]

/** Wrong LINE on the right market — must never match a 2.5 request. */
export const WRONG_LINE: SportMonksOdd[] = [
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: 'Over', total: '3', value: '2.02', bookmaker_id: 58 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: '3.0', total: '3.0', value: '2.00', bookmaker_id: 2 }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', name: 'Over', total: '2.75', value: '1.79', bookmaker_id: 35 }),
]

/**
 * The poison. Every one of these contains "2.5" somewhere and was reachable by
 * the old `name/label.includes('2.5')` matcher.
 */
export const COLLIDING_MARKETS: SportMonksOdd[] = [
  // THE defect: 2nd-half-only Over 2.5, legitimately ~3.50, graded as full-time.
  odd({ market_id: 53, market_description: '2nd Half Goals', label: 'Over', name: '2.5', total: null, value: '3.50', bookmaker_id: 2 }),
  odd({ market_id: 53, market_description: '2nd Half Goals', label: 'Under', name: '2.5', total: null, value: '1.28', bookmaker_id: 2 }),
  odd({ market_id: 28, market_description: '1st Half Goals', label: 'Over', name: '2.5', total: null, value: '6.50', bookmaker_id: 2 }),
  odd({ market_id: 37, market_description: 'Result / Total Goals', label: 'Over', name: '1', total: '2.5', value: '3.60', bookmaker_id: 2 }),
  odd({ market_id: 86, market_description: 'Team Total Goals', label: '1', name: null, total: 'Over 2.5', value: '1.20', bookmaker_id: 2 }),
  odd({ market_id: 107, market_description: 'Alternative 1st Half Goal Line', label: 'Over', name: '2.5', total: '2.5', value: '5.75', bookmaker_id: 2 }),
  // Combined Asian line — "2.5, 3.0" is a different bet, not a plain 2.5 line.
  odd({ market_id: 105, market_description: 'Alternative Goal Line', label: 'Over', name: '2.5, 3.0', total: '2.5, 3.0', value: '1.75', bookmaker_id: 2 }),
  odd({ market_id: 105, market_description: 'Alternative Goal Line', label: 'Under', name: '2.5, 3.0', total: '2.5, 3.0', value: '2.05', bookmaker_id: 2 }),
]

/** 1x2 across several books. */
export const X12: SportMonksOdd[] = [
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Home', value: '2.40', bookmaker_id: 32 }),
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Home', value: '2.53', bookmaker_id: 20 }),
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Home', value: '2.45', bookmaker_id: 64 }),
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Draw', value: '3.60', bookmaker_id: 32 }),
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Draw', value: '3.66', bookmaker_id: 64 }),
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Away', value: '2.62', bookmaker_id: 32 }),
  odd({ market_id: 1, market_description: 'Fulltime Result', label: 'Away', value: '2.60', bookmaker_id: 58 }),
]

/** BTTS plus its half-time decoys. */
export const BTTS: SportMonksOdd[] = [
  odd({ market_id: 14, market_description: 'Both Teams to Score', label: 'Yes', value: '1.53', bookmaker_id: 2 }),
  odd({ market_id: 14, market_description: 'Both Teams to Score', label: 'Yes', value: '1.57', bookmaker_id: 32 }),
  odd({ market_id: 14, market_description: 'Both Teams to Score', label: 'No', value: '2.37', bookmaker_id: 2 }),
  odd({ market_id: 15, market_description: 'Both Teams to Score in 1st Half', label: 'Yes', value: '3.75', bookmaker_id: 2 }),
  odd({ market_id: 16, market_description: 'Both Teams to Score in 2nd Half', label: 'Yes', value: '2.62', bookmaker_id: 2 }),
]

/** Double chance — real payloads label these with TEAM NAMES. */
export const DOUBLE_CHANCE: SportMonksOdd[] = [
  odd({ market_id: 2, market_description: 'Double Chance', label: 'Cambuur Leeuwarden or Draw', value: '1.50', bookmaker_id: 2 }),
  odd({ market_id: 2, market_description: 'Double Chance', label: 'Cambuur Leeuwarden or Excelsior', value: '1.28', bookmaker_id: 2 }),
  odd({ market_id: 2, market_description: 'Double Chance', label: 'Draw or Excelsior', value: '1.53', bookmaker_id: 2 }),
  odd({ market_id: 47, market_description: 'Half Time Double Chance', label: 'Cambuur Leeuwarden or Draw', value: '1.36', bookmaker_id: 2 }),
]

/** Suspended / stopped quotes that must be ignored. */
export const STOPPED_ONLY: SportMonksOdd[] = [
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', total: '2.5', value: '1.60', bookmaker_id: 32, stopped: true }),
  odd({ market_id: 7, market_description: 'Goal Line', label: 'Over', total: '2.5', value: '1.61', bookmaker_id: 13, suspended: true }),
]

/** The full realistic payload: correct quotes buried among the collisions. */
export const FULL_PAYLOAD: SportMonksOdd[] = [
  ...COLLIDING_MARKETS,
  ...WRONG_LINE,
  ...CORRECT_OU_25,
  ...X12,
  ...BTTS,
  ...DOUBLE_CHANCE,
]

/** Build Goal Line Over 2.5 quotes from a real price list (audited fixtures). */
export function goalLineOver25(prices: number[], fixtureId: number): SportMonksOdd[] {
  return prices.map((v, i) =>
    odd({
      fixture_id: fixtureId,
      market_id: 7,
      market_description: 'Goal Line',
      label: 'Over',
      name: 'Over',
      total: '2.5',
      value: v.toFixed(2),
      bookmaker_id: 10 + i,
    }),
  )
}

/**
 * The three fixtures from the 2026-07-29 audit, with the real market-7/80
 * Over 2.5 quotes actually offered. `stored` is the (wrong) value production
 * recorded via the old substring matcher.
 */
export const AUDITED_FIXTURES = [
  {
    name: 'Falkirk v St. Mirren',
    fixtureId: 19722822,
    stored: 2.05,
    expected: 1.78,
    prices: [1.68, 1.75, 1.75, 1.75, 1.75, 1.75, 1.75, 1.76, 1.77, 1.78, 1.78, 1.78, 1.78, 1.79, 1.8, 1.8, 1.8, 1.81, 1.82],
  },
  {
    name: 'Aberdeen v Hearts',
    fixtureId: 19722821,
    stored: 1.87,
    expected: 1.67,
    prices: [1.65, 1.65, 1.66, 1.66, 1.66, 1.67, 1.67, 1.67, 1.68, 1.7, 1.7, 1.7, 1.7, 1.71, 1.71],
  },
  {
    name: 'SC Cambuur v Excelsior',
    fixtureId: 19714700,
    stored: 3.5,
    expected: 1.6,
    prices: [1.58, 1.6, 1.6, 1.61, 1.62],
  },
]
