/**
 * Public formatting + the card's timestamp semantics.
 *
 * The primary proof timestamp on a public card is PUBLICATION, not model
 * generation — presenting generation time as the immutable publication time
 * would overstate our foresight.
 */
import { describe, expect, it } from 'vitest'

import {
  beforeKickoffFromPublication, formatBookmaker, formatModelScore, formatOdds,
  formatSelection, formatUtc,
} from '../../proof/_shared/format'

describe('odds formatting', () => {
  it.each([
    [1.8, '1.80'],
    [1.75, '1.75'],
    [2, '2.00'],
    [10.5, '10.50'],
  ])('renders %s as %s', (input, expected) => {
    expect(formatOdds(input)).toBe(expected)
  })

  it('never renders a bare single decimal', () => {
    expect(formatOdds(1.8)).not.toBe('1.8')
  })

  it('handles a missing price', () => {
    expect(formatOdds(null)).toBe('n/a')
    expect(formatOdds(undefined)).toBe('n/a')
  })
})

describe('market + outcome formatting', () => {
  it.each([
    ['btts', 'Btts yes', 'BTTS — YES'],
    ['btts', 'Btts no', 'BTTS — NO'],
    ['over_under_2.5', 'Over 2.5', 'Over/Under 2.5 — OVER 2.5'],
    ['1x2', 'Home', 'Match Result — HOME'],
    ['double_chance', '1X', 'Double Chance — 1X'],
  ])('%s + %s -> %s', (market, outcome, expected) => {
    expect(formatSelection(market, outcome)).toBe(expected)
  })

  it('never emits the raw stored strings', () => {
    const out = formatSelection('btts', 'Btts yes')
    expect(out).not.toContain('btts —')
    expect(out).not.toContain('Btts yes')
  })

  it('supports the long market name', () => {
    expect(formatSelection('btts', 'Btts yes', { long: true }))
      .toBe('Both Teams to Score — YES')
  })
})

describe('bookmaker casing', () => {
  it.each([
    ['bet365', 'Bet365'],
    ['Marathonbet', 'Marathonbet'],
    ['william hill', 'William Hill'],
  ])('%s -> %s', (input, expected) => {
    expect(formatBookmaker(input)).toBe(expected)
  })

  it('returns null when absent', () => {
    expect(formatBookmaker(null)).toBeNull()
  })
})

describe('timestamps', () => {
  it('renders a readable UTC string', () => {
    expect(formatUtc('2026-07-30T14:20:14.773451+00:00'))
      .toBe('30 JUL 2026 · 14:20 UTC')
  })

  it('handles a missing timestamp', () => {
    expect(formatUtc(null)).toBe('n/a')
  })
})

describe('model score is labelled as a score', () => {
  it('keeps one decimal', () => {
    expect(formatModelScore(62.36)).toBe('62.4%')
  })
})

describe('lead time is measured from PUBLICATION', () => {
  const kickoff = '2026-08-08T17:00:00+00:00'

  it('uses published_at, not prediction generation', () => {
    const published = '2026-07-30T14:20:00+00:00'   // 9d 2h before kickoff
    const generated = '2026-07-30T13:58:00+00:00'   // 22 min earlier

    const fromPublication = beforeKickoffFromPublication(published, kickoff)
    const fromGeneration = beforeKickoffFromPublication(generated, kickoff)

    expect(fromPublication).toBe('9D 2H BEFORE KICKOFF')
    // Generation is EARLIER, so it would overstate the lead time.
    expect(fromGeneration).not.toBe(fromPublication)
  })

  it.each([
    ['2026-08-08T11:00:00+00:00', '6H 0M BEFORE KICKOFF'],
    ['2026-08-08T16:30:00+00:00', '30M BEFORE KICKOFF'],
    ['2026-08-06T17:00:00+00:00', '2D 0H BEFORE KICKOFF'],
  ])('publication %s -> %s', (published, expected) => {
    expect(beforeKickoffFromPublication(published, kickoff)).toBe(expected)
  })

  it('returns null when publication is at or after kickoff', () => {
    expect(beforeKickoffFromPublication(kickoff, kickoff)).toBeNull()
    expect(beforeKickoffFromPublication('2026-08-09T00:00:00+00:00', kickoff))
      .toBeNull()
  })
})
