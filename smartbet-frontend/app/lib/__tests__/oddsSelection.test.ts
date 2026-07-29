/**
 * Regression tests for the 2026-07-29 odds-capture defect.
 *
 * The defect: substring matching on "2.5" let a SECOND-HALF Over 2.5 quote
 * (~3.50) price a FULL-TIME Over 2.5 pick (~1.60). Audit report:
 * `docs/audit/gem-selector-diagnostics-2026-07-29.md`.
 */
import { describe, expect, it } from 'vitest'

import { ODDS_SELECTION_POLICY, selectOdds, type SportMonksOdd } from '../oddsSelection'
import {
  AUDITED_FIXTURES,
  BTTS,
  COLLIDING_MARKETS,
  CORRECT_OU_25,
  DOUBLE_CHANCE,
  FULL_PAYLOAD,
  STOPPED_ONLY,
  WRONG_LINE,
  X12,
  goalLineOver25,
} from './fixtures/sportmonksOdds'

const ok = (r: ReturnType<typeof selectOdds>) => {
  if (!r.ok) throw new Error(`expected success, got "${r.reason}"`)
  return r.provenance
}

describe('market identity', () => {
  it('only accepts the goals markets (80, 7) for over_under_2.5', () => {
    const p = ok(selectOdds(FULL_PAYLOAD, 'over_under_2.5', 'over'))
    expect([80, 7]).toContain(p.odds_market_id)
    expect(p.odds_market_description).toMatch(/Goal Line|Goals Over\/Under/)
  })

  it('NEVER prices a full-time pick from 2nd Half Goals (the actual defect)', () => {
    const p = ok(selectOdds(FULL_PAYLOAD, 'over_under_2.5', 'over'))
    expect(p.odds).not.toBe(3.5)
    expect(p.odds_market_id).not.toBe(53)
    expect(p.odds_market_description).not.toBe('2nd Half Goals')
  })

  it('reports market_not_offered when ONLY colliding markets exist', () => {
    // The old matcher would have happily returned 3.50 here.
    const r = selectOdds(COLLIDING_MARKETS, 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.reason).toBe('market_not_offered')
  })

  it.each([
    ['1st Half Goals', 28],
    ['Result / Total Goals', 37],
    ['2nd Half Goals', 53],
    ['Team Total Goals', 86],
    ['Alternative Goal Line', 105],
    ['Alternative 1st Half Goal Line', 107],
  ])('rejects collision market %s (id %i) in isolation', (_desc, marketId) => {
    const only = COLLIDING_MARKETS.filter((o) => o.market_id === marketId)
    const r = selectOdds(only, 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
  })

  it('substring collisions cannot match: no selected price comes from a "2.5"-containing decoy', () => {
    const decoyPrices = COLLIDING_MARKETS.map((o) => Number(o.value))
    const p = ok(selectOdds(FULL_PAYLOAD, 'over_under_2.5', 'over'))
    expect(decoyPrices).not.toContain(p.odds)
  })
})

describe('line matching', () => {
  it('matches the 2.5 line exactly and ignores 2.75 / 3.0', () => {
    const r = selectOdds([...WRONG_LINE, ...CORRECT_OU_25], 'over_under_2.5', 'over')
    const p = ok(r)
    expect(p.odds_line).toBe(2.5)
    expect([2.02, 2.0, 1.79]).not.toContain(p.odds)
  })

  it('reports line_not_offered when the right market lacks a 2.5 line', () => {
    const r = selectOdds(WRONG_LINE, 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.reason).toBe('line_not_offered')
  })

  it('rejects combined Asian lines such as "2.5, 3.0"', () => {
    const combined = COLLIDING_MARKETS.filter((o) => String(o.total).includes(','))
    expect(combined.length).toBeGreaterThan(0)
    const r = selectOdds(combined, 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
  })
})

describe('outcome matching', () => {
  it('Over 2.5 can never be priced with an Under 2.5 quote', () => {
    const p = ok(selectOdds(CORRECT_OU_25, 'over_under_2.5', 'over'))
    const underPrices = CORRECT_OU_25.filter(
      (o) => String(o.label).toLowerCase() === 'under',
    ).map((o) => Number(o.value))
    expect(underPrices).not.toContain(p.odds)
    expect(p.odds_label.toLowerCase()).toBe('over')
  })

  it('Under 2.5 selects only under quotes', () => {
    const p = ok(selectOdds(CORRECT_OU_25, 'over_under_2.5', 'under'))
    expect(p.odds_label.toLowerCase()).toBe('under')
    expect(p.odds).toBeGreaterThan(2)
  })

  it('reports outcome_not_offered when the side is absent', () => {
    const overOnly = CORRECT_OU_25.filter((o) => String(o.label).toLowerCase() === 'over')
    const r = selectOdds(overOnly, 'over_under_2.5', 'under')
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.reason).toBe('outcome_not_offered')
  })
})

describe('determinism', () => {
  const shuffles = (arr: SportMonksOdd[], seed: number): SportMonksOdd[] => {
    const a = [...arr]
    let s = seed
    for (let i = a.length - 1; i > 0; i--) {
      s = (s * 1103515245 + 12345) % 2147483648
      const j = s % (i + 1)
      ;[a[i], a[j]] = [a[j], a[i]]
    }
    return a
  }

  it('API entry order does not affect the selected price or bookmaker', () => {
    const baseline = ok(selectOdds(FULL_PAYLOAD, 'over_under_2.5', 'over'))
    for (let seed = 1; seed <= 50; seed++) {
      const p = ok(selectOdds(shuffles(FULL_PAYLOAD, seed), 'over_under_2.5', 'over'))
      expect(p.odds).toBe(baseline.odds)
      expect(p.odds_bookmaker_id).toBe(baseline.odds_bookmaker_id)
      expect(p.odds_market_id).toBe(baseline.odds_market_id)
    }
  })

  it('applies the documented lower-median policy, not the best price', () => {
    const p = ok(selectOdds(CORRECT_OU_25, 'over_under_2.5', 'over'))
    // Valid Over quotes: 1.58, 1.60, 1.60, 1.61, 1.62 -> lower median 1.60
    expect(p.odds).toBe(1.6)
    expect(p.odds).not.toBe(p.odds_max) // never the most favourable
    expect(p.odds_bookmaker_count).toBe(5)
    expect(p.odds_min).toBe(1.58)
    expect(p.odds_max).toBe(1.62)
    expect(p.odds_selection_policy).toBe(ODDS_SELECTION_POLICY)
  })
})

describe('unavailable states (never fall back to a wrong market)', () => {
  it.each([
    ['empty array', [] as SportMonksOdd[], 'no_odds_payload'],
    ['null payload', null, 'no_odds_payload'],
    ['only stopped/suspended', STOPPED_ONLY, 'all_entries_stopped'],
  ])('%s -> %s', (_name, payload, reason) => {
    const r = selectOdds(payload as SportMonksOdd[] | null, 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.reason).toBe(reason)
  })

  it('rejects unusable prices (<= 1.0) rather than recording them', () => {
    const junk: SportMonksOdd[] = [
      { market_id: 7, market_description: 'Goal Line', label: 'Over', total: '2.5', value: '1.00', bookmaker_id: 1 },
      { market_id: 7, market_description: 'Goal Line', label: 'Over', total: '2.5', value: 'n/a', bookmaker_id: 2 },
    ]
    const r = selectOdds(junk, 'over_under_2.5', 'over')
    expect(r.ok).toBe(false)
    if (!r.ok) expect(r.reason).toBe('no_valid_price')
  })
})

describe('provenance', () => {
  it('matches the payload entry actually selected', () => {
    const p = ok(selectOdds(FULL_PAYLOAD, 'over_under_2.5', 'over'))
    const source = FULL_PAYLOAD.find((o) => o.id === p.odds_entry_id)
    expect(source).toBeDefined()
    expect(Number(source!.value)).toBe(p.odds)
    expect(source!.market_id).toBe(p.odds_market_id)
    expect(source!.bookmaker_id).toBe(p.odds_bookmaker_id)
    expect(source!.market_description).toBe(p.odds_market_description)
    expect(String(source!.label)).toBe(p.odds_label)
    expect(source!.fixture_id).toBe(p.odds_fixture_id)
    expect(source!.latest_bookmaker_update).toBe(p.odds_captured_at)
  })
})

describe('other product markets', () => {
  it('1x2 uses market 1 and the exact outcome label', () => {
    const p = ok(selectOdds(FULL_PAYLOAD, '1x2', 'home'))
    expect(p.odds_market_id).toBe(1)
    expect(p.odds_label.toLowerCase()).toBe('home')
    expect(p.odds).toBe(2.45) // 2.40, 2.45, 2.53 -> lower median
  })

  it('btts uses market 14 and never the half-time variants', () => {
    const p = ok(selectOdds(FULL_PAYLOAD, 'btts', 'yes'))
    expect(p.odds_market_id).toBe(14)
    expect([3.75, 2.62]).not.toContain(p.odds) // markets 15 / 16
  })

  it('double chance resolves team-name labels and skips Half Time Double Chance', () => {
    const p = ok(
      selectOdds(DOUBLE_CHANCE, 'double_chance', '1X', {
        homeTeam: 'Cambuur Leeuwarden',
        awayTeam: 'Excelsior',
      }),
    )
    expect(p.odds_market_id).toBe(2)
    expect(p.odds).toBe(1.5)
    expect(p.odds).not.toBe(1.36) // market 47
  })

  it('markets do not leak into each other', () => {
    expect(selectOdds(X12, 'over_under_2.5', 'over').ok).toBe(false)
    expect(selectOdds(BTTS, '1x2', 'home').ok).toBe(false)
    expect(selectOdds(CORRECT_OU_25, 'btts', 'yes').ok).toBe(false)
  })
})

describe('audited production fixtures resolve to the corrected price', () => {
  it.each(AUDITED_FIXTURES)(
    '$name: stored $stored -> corrected $expected',
    ({ fixtureId, stored, expected, prices }) => {
      const payload = [
        ...goalLineOver25(prices, fixtureId),
        // bury the poison alongside, as production did
        ...COLLIDING_MARKETS,
      ]
      const p = ok(selectOdds(payload, 'over_under_2.5', 'over'))
      expect(p.odds).toBe(expected)
      expect(p.odds).not.toBe(stored)
      expect(p.odds_market_id).toBe(7)
      expect(p.odds_fixture_id).toBe(fixtureId)
    },
  )

  it('the corrected SC Cambuur price flips its gem verdict to a rejection', () => {
    const cambuur = AUDITED_FIXTURES.find((f) => f.fixtureId === 19714700)!
    const p = ok(selectOdds(goalLineOver25(cambuur.prices, cambuur.fixtureId), 'over_under_2.5', 'over'))
    // Gem gate: p_cons = confidence - measured margin (0.0304) - safety eps (0.01)
    const pCons = 0.5887 - 0.0304 - 0.01
    const edgeAtStored = pCons * cambuur.stored - 1
    const edgeAtTrue = pCons * p.odds - 1
    expect(edgeAtStored).toBeGreaterThan(0.02) // would have been published
    expect(edgeAtTrue).toBeLessThan(0) // correctly rejected
  })
})
