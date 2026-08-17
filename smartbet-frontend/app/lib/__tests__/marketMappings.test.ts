/**
 * Table-driven coverage for EVERY supported BetGlitch market.
 *
 * The 2026-07-29 defect was found in over_under_2.5, but the same class of bug
 * (a confusable SportMonks market pricing the wrong bet) applies to all of
 * them. These tests assert the canonical mapping per market and prove that
 * each market's documented `rejects` list genuinely cannot resolve.
 */
import { describe, expect, it } from 'vitest'

import {
  MARKET_SPECS,
  selectOdds,
  type ProductMarket,
  type SportMonksOdd,
} from '../oddsSelection'

const TEAM_CTX = { homeTeam: 'Cambuur Leeuwarden', awayTeam: 'Excelsior' }

let seq = 5000
const odd = (o: Partial<SportMonksOdd>): SportMonksOdd => ({
  id: seq++,
  fixture_id: 19714700,
  stopped: false,
  suspended: false,
  name: null,
  total: null,
  market_description: null,
  latest_bookmaker_update: '2026-07-29 11:16:22',
  ...o,
})

/** A valid quote for `market` + `outcome`, on the canonical market id. */
function validQuote(
  market: ProductMarket,
  outcome: string,
  value = '1.90',
  bookmakerId = 2,
): SportMonksOdd {
  const spec = MARKET_SPECS[market]
  const label = spec.labelsFor(outcome, TEAM_CTX)[0]
  return odd({
    market_id: spec.marketIds[0],
    market_description: spec.description,
    label: label
      .split(' ')
      .map((w) => (w === 'or' ? 'or' : w.charAt(0).toUpperCase() + w.slice(1)))
      .join(' '),
    total: spec.requiredLine === null ? null : String(spec.requiredLine),
    value,
    bookmaker_id: bookmakerId,
  })
}

const ALL_MARKETS = Object.keys(MARKET_SPECS) as ProductMarket[]

describe('canonical mapping per supported market', () => {
  it('covers every ProductMarket in the union', () => {
    expect(ALL_MARKETS.sort()).toEqual(
      [
        '1x2', 'btts', 'over_under_1.5', 'over_under_2.5', 'over_under_3.5',
        'double_chance', 'half_time_result', 'half_time_full_time',
        'first_team_to_score', 'correct_score',
      ].sort(),
    )
  })

  it.each(ALL_MARKETS)('%s resolves each of its outcomes on the canonical market', (market) => {
    const spec = MARKET_SPECS[market]
    for (const outcome of spec.outcomes) {
      const r = selectOdds([validQuote(market, outcome)], market, outcome, TEAM_CTX)
      expect(r.ok, `${market}/${outcome} should resolve`).toBe(true)
      if (r.ok) {
        expect(spec.marketIds).toContain(r.provenance.odds_market_id)
        expect(r.provenance.odds_line).toBe(spec.requiredLine)
      }
    }
  })

  it.each(ALL_MARKETS)('%s: outcomes are mutually exclusive', (market) => {
    const spec = MARKET_SPECS[market]
    if (spec.outcomes.length < 2) return
    for (const outcome of spec.outcomes) {
      const others = spec.outcomes.filter((o) => o !== outcome)
      // Payload contains ONLY the other outcomes -> must not resolve.
      const payload = others.map((o, i) => validQuote(market, o, String(2 + i)))
      const r = selectOdds(payload, market, outcome, TEAM_CTX)
      expect(r.ok, `${market}/${outcome} matched a sibling outcome`).toBe(false)
    }
  })

  it.each(ALL_MARKETS)('%s: every documented rejected market cannot resolve', (market) => {
    const spec = MARKET_SPECS[market]
    expect(spec.rejects.length).toBeGreaterThan(0)
    for (const rejected of spec.rejects) {
      expect(spec.marketIds).not.toContain(rejected.marketId)
      for (const outcome of spec.outcomes) {
        const label = spec.labelsFor(outcome, TEAM_CTX)[0]
        // Same label and line, but the confusable market id.
        const decoy = odd({
          market_id: rejected.marketId,
          market_description: rejected.description,
          label: label.charAt(0).toUpperCase() + label.slice(1),
          name: spec.requiredLine === null ? null : String(spec.requiredLine),
          total: spec.requiredLine === null ? null : String(spec.requiredLine),
          value: '3.50',
          bookmaker_id: 2,
        })
        const r = selectOdds([decoy], market, outcome, TEAM_CTX)
        expect(
          r.ok,
          `${market}/${outcome} resolved against ${rejected.description} (id ${rejected.marketId})`,
        ).toBe(false)
      }
    }
  })

  it.each(ALL_MARKETS)('%s: no exact match yields a typed unavailable state', (market) => {
    const spec = MARKET_SPECS[market]
    const r = selectOdds([], market, spec.outcomes[0], TEAM_CTX)
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.reason).toBe('no_odds_payload')
  })

  it('no two product markets share the same canonical market id and line', () => {
    const seen = new Map<string, string>()
    for (const market of ALL_MARKETS) {
      for (const id of MARKET_SPECS[market].marketIds) {
        const identity = `${id}:${MARKET_SPECS[market].requiredLine ?? 'main'}`
        expect(
          seen.has(identity),
          `${identity} claimed by ${seen.get(identity)} and ${market}`,
        ).toBe(false)
        seen.set(identity, market)
      }
    }
  })
})

describe('full-match Over/Under 2.5 cannot resolve against any neighbour', () => {
  const line = '2.5'
  const cases: { name: string; entry: SportMonksOdd }[] = [
    {
      name: 'second-half goals',
      entry: odd({ market_id: 53, market_description: '2nd Half Goals', label: 'Over', name: line, value: '3.50', bookmaker_id: 2 }),
    },
    {
      name: 'first-half goals',
      entry: odd({ market_id: 28, market_description: '1st Half Goals', label: 'Over', name: line, value: '6.50', bookmaker_id: 2 }),
    },
    {
      name: 'team totals',
      entry: odd({ market_id: 86, market_description: 'Team Total Goals', label: 'Over', total: 'Over 2.5', value: '1.20', bookmaker_id: 2 }),
    },
    {
      name: 'alternative combined Asian line',
      entry: odd({ market_id: 105, market_description: 'Alternative Goal Line', label: 'Over', name: '2.5, 3.0', total: '2.5, 3.0', value: '1.75', bookmaker_id: 2 }),
    },
    {
      name: 'corners',
      entry: odd({ market_id: 220, market_description: 'Corners Over/Under', label: 'Over', name: line, total: line, value: '2.10', bookmaker_id: 2 }),
    },
    {
      name: 'cards',
      entry: odd({ market_id: 221, market_description: 'Cards Over/Under', label: 'Over', name: line, total: line, value: '1.95', bookmaker_id: 2 }),
    },
    {
      name: 'the other outcome side (Under)',
      entry: odd({ market_id: 80, market_description: 'Goals Over/Under', label: 'Under', name: line, total: line, value: '2.25', bookmaker_id: 2 }),
    },
    {
      name: 'result / total goals combination',
      entry: odd({ market_id: 37, market_description: 'Result / Total Goals', label: 'Over', name: '1', total: line, value: '3.60', bookmaker_id: 2 }),
    },
  ]

  it.each(cases)('rejects $name', ({ entry }) => {
    const r = selectOdds([entry], 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
  })

  it('rejects all of them together, even in bulk', () => {
    const r = selectOdds(cases.map((c) => c.entry), 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
  })

  it('still resolves when a genuine quote is buried among all of them', () => {
    const genuine = odd({
      market_id: 7, market_description: 'Goal Line', label: 'Over',
      name: 'Over', total: '2.5', value: '1.60', bookmaker_id: 32,
    })
    const r = selectOdds([...cases.map((c) => c.entry), genuine], 'over_under_2.5', 'over')
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.provenance.odds).toBe(1.6)
      expect(r.provenance.odds_market_id).toBe(7)
    }
  })
})
