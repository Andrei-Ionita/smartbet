/**
 * Regression evidence for the fixture-detail odds defect (2026-08-03).
 *
 * `/api/fixture/{id}` — which backs the Explore detail modal and every
 * `/prediction/*` page — carried its OWN copy of odds selection instead of using
 * `app/lib/oddsSelection.ts`. Four independent faults:
 *
 *   1. BTTS matched `market_id 28` ("1st Half Goals") or any entry whose name
 *      contained "btts", so the half-time variants could win and the canonical
 *      market (14) was never consulted.
 *   2. Over/Under matched `market_id 18` OR any label/name containing "2.5",
 *      which collides with markets 28, 37, 53, 81, 86, 105 and 107.
 *   3. Among whatever survived, it took the MAXIMUM price across bookmakers.
 *   4. With nothing matched it left the price at the literal `1`, and that `1`
 *      flowed into `EV = probability × odds − 1` as though it were a quote.
 *
 * Each `describe` below reconstructs the retired algorithm, records what it
 * displayed, and asserts what the canonical contract returns instead.
 *
 * The legacy functions here are DELIBERATE reconstructions used as evidence.
 * They must never be exported or imported by product code.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  canPublishPrice,
  expectedValue,
  isProvenanceComplete,
  priceMarket,
  type MarketPrice,
} from '../marketPricing'
import { ODDS_SELECTION_POLICY, type SportMonksOdd } from '../oddsSelection'
import {
  BTTS,
  COLLIDING_MARKETS,
  CORRECT_OU_25,
  FULL_PAYLOAD,
  X12,
} from './fixtures/sportmonksOdds'

// ── Bookmaker names ────────────────────────────────────────────────────────
// The shared fixtures predate the `odds.bookmaker` include. Production requests
// it (both `/api/fixture/{id}` and `/api/recommendations` ask for
// `odds;odds.bookmaker`), and a price without a named book is correctly treated
// as unpublishable, so attach names to exercise the publishable path.
const BOOKMAKERS: Record<number, string> = {
  2: 'bet365',
  13: 'Betfair',
  20: 'Marathonbet',
  28: '1xBet',
  32: 'Unibet',
  58: 'Pinnacle',
  64: '888sport',
}

const named = (odds: SportMonksOdd[]): SportMonksOdd[] =>
  odds.map((o) => ({
    ...o,
    bookmaker: { id: o.bookmaker_id ?? null, name: BOOKMAKERS[o.bookmaker_id ?? -1] ?? 'Book' },
  }))

const verified = (p: MarketPrice) => {
  if (p.status !== 'verified') throw new Error(`expected verified, got "${p.unavailable_reason}"`)
  return p
}

// ── The retired algorithm, reconstructed ───────────────────────────────────

/** Old Over/Under matcher: market 18 OR any "2.5" substring, then max price. */
function legacyOverUnder(odds: SportMonksOdd[], outcome: 'Over' | 'Under'): number {
  let oddsValue = 1
  const candidates = odds.filter((o) => {
    if (o.market_id === 18) return true
    return (
      String(o.name ?? '').toLowerCase().includes('2.5') ||
      String(o.label ?? '').toLowerCase().includes('2.5') ||
      String(o.name ?? '').toLowerCase().includes('over/under')
    )
  })

  let maxVal = -1
  for (const o of candidates) {
    const label = String(o.label ?? '').toLowerCase()
    const name = String(o.name ?? '').toLowerCase()
    if (!label.includes('2.5') && !name.includes('2.5')) continue

    const val = parseFloat(String(o.value))
    const sideMatches =
      (outcome === 'Over' && label.includes('over')) ||
      (outcome === 'Under' && label.includes('under'))
    if (sideMatches && val >= 1.3 && val <= 3.5 && val > maxVal) maxVal = val
  }

  if (maxVal > 0) oddsValue = maxVal
  return oddsValue
}

/** Old BTTS matcher: market 28 OR any name containing "btts", then max price. */
function legacyBtts(odds: SportMonksOdd[], outcome: 'yes' | 'no'): number {
  let oddsValue = 1
  const candidates = odds.filter(
    (o) => o.market_id === 28 || String(o.name ?? '').toLowerCase().includes('btts'),
  )

  let maxVal = -1
  for (const o of candidates) {
    if (String(o.label ?? '').toLowerCase() !== outcome) continue
    const val = parseFloat(String(o.value)) || 0
    if (val > maxVal) maxVal = val
  }

  if (maxVal > 0) oddsValue = maxVal
  return oddsValue
}

/** Old 1X2 matcher: right market, but maximum price across books. */
function legacyX12(odds: SportMonksOdd[], outcome: 'Home' | 'Draw' | 'Away'): number {
  let oddsValue = 1
  let maxVal = -1
  for (const o of odds.filter((x) => x.market_id === 1)) {
    if (String(o.label ?? '').toLowerCase() !== outcome.toLowerCase()) continue
    const val = parseFloat(String(o.value)) || 0
    if (val > maxVal) maxVal = val
  }
  if (maxVal > 0) oddsValue = maxVal
  return oddsValue
}

// ── 1. BTTS matched market_id 28 ───────────────────────────────────────────

describe('regression 1 — BTTS priced off a half-time market', () => {
  // A payload where the half-time BTTS variants carry "BTTS" in their name, so
  // the old substring filter reached them while never consulting market 14.
  const payload = named([
    ...BTTS.map((o) =>
      o.market_id === 15 ? { ...o, name: 'BTTS 1st Half' } : o.market_id === 16 ? { ...o, name: 'BTTS 2nd Half' } : o,
    ),
    ...COLLIDING_MARKETS,
  ])

  it('old algorithm resolved a first-half quote', () => {
    // 3.75 is the market 15 ("Both Teams to Score in 1st Half") price.
    expect(legacyBtts(payload, 'yes')).toBe(3.75)
  })

  it('canonical selection uses market 14 and its real price', () => {
    const price = verified(priceMarket(payload, 'btts', 'yes'))

    expect(price.provenance.odds_market_id).toBe(14)
    expect(price.provenance.odds_market_description).toBe('Both Teams to Score')
    expect(price.odds).toBe(1.53)
    expect(price.bookmaker.name).toBe('bet365')
    expect(price.provenance.odds_selection_policy).toBe(ODDS_SELECTION_POLICY)
  })

  it('the half-time markets are unreachable even in isolation', () => {
    for (const marketId of [15, 16]) {
      const only = named(BTTS.filter((o) => o.market_id === marketId))
      expect(priceMarket(only, 'btts', 'yes').status).toBe('unavailable')
    }
  })

  it('BTTS cannot be priced from first-half GOALS (market 28) either', () => {
    const firstHalfGoals = named(COLLIDING_MARKETS.filter((o) => o.market_id === 28))
    const price = priceMarket(firstHalfGoals, 'btts', 'yes')

    expect(price.status).toBe('unavailable')
    expect(price.unavailable_reason).toBe('market_not_offered')
  })
})

// ── 2. Over 2.5 matched market_id 18 ───────────────────────────────────────

describe('regression 2 — full-match Over 2.5 priced off market_id 18', () => {
  // market_id 18 is not 80 ("Goals Over/Under") and not 7 ("Goal Line"), so
  // whatever it prices, it is not the bet the product means by "Over 2.5".
  const market18: SportMonksOdd[] = [
    {
      id: 9001,
      fixture_id: 19714700,
      market_id: 18,
      market_description: 'Provider market 18',
      label: 'Over',
      name: '2.5',
      total: '2.5',
      value: '2.90',
      bookmaker_id: 2,
      stopped: false,
      suspended: false,
      latest_bookmaker_update: '2026-07-29 11:16:22',
    },
  ]
  const payload = named([...market18, ...CORRECT_OU_25])

  it('old algorithm accepted market 18 unconditionally and its price won on max', () => {
    expect(legacyOverUnder(payload, 'Over')).toBe(2.9)
  })

  it('canonical selection accepts only markets 80 and 7', () => {
    const price = verified(priceMarket(payload, 'over_under_2.5', 'over'))

    expect([80, 7]).toContain(price.provenance.odds_market_id)
    expect(price.provenance.odds_market_id).not.toBe(18)
    expect(price.odds).toBe(1.6)
  })

  it('market 18 alone yields no price at all', () => {
    const price = priceMarket(named(market18), 'over_under_2.5', 'over')

    expect(price.status).toBe('unavailable')
    expect(price.unavailable_reason).toBe('market_not_offered')
    expect(price.odds).toBeUndefined()
  })
})

// ── 3. Substring collisions across several "2.5" markets ───────────────────

describe('regression 3 — every market whose text contains "2.5"', () => {
  const payload = named(FULL_PAYLOAD)

  it('old algorithm resolved the second-half quote', () => {
    // 3.50 is market 53 ("2nd Half Goals"). It is inside the legacy 1.30-3.50
    // plausibility band and is the maximum, so it won.
    expect(legacyOverUnder(payload, 'Over')).toBe(3.5)
  })

  it('canonical selection resolves the genuine full-match quote', () => {
    const price = verified(priceMarket(payload, 'over_under_2.5', 'over'))

    expect(price.odds).toBe(1.6)
    expect(price.provenance.odds_market_id).not.toBe(53)
    expect(price.provenance.odds_line).toBe(2.5)
  })

  it.each([
    ['1st Half Goals', 28],
    ['2nd Half Goals', 53],
    ['Result / Total Goals', 37],
    ['Team Total Goals', 86],
    ['Alternative Goal Line (combined 2.5, 3.0)', 105],
    ['Alternative 1st Half Goal Line', 107],
  ])('%s (id %i) cannot price a full-match Over 2.5', (_label, marketId) => {
    const only = named(COLLIDING_MARKETS.filter((o) => o.market_id === marketId))
    expect(priceMarket(only, 'over_under_2.5', 'over').status).toBe('unavailable')
  })

  it('a combined Asian line is not a plain 2.5 line', () => {
    const combined = named(COLLIDING_MARKETS.filter((o) => o.market_id === 105))
    expect(combined.every((o) => String(o.total).includes(','))).toBe(true)
    expect(priceMarket(combined, 'over_under_2.5', 'over').status).toBe('unavailable')
  })

  it('an Over request is never satisfied by an Under quote', () => {
    const undersOnly = named(CORRECT_OU_25.filter((o) => o.label === 'Under'))
    const price = priceMarket(undersOnly, 'over_under_2.5', 'over')

    expect(price.status).toBe('unavailable')
    expect(price.unavailable_reason).toBe('outcome_not_offered')
  })

  it('1X2 is never satisfied by a result-plus-total combination', () => {
    const combo = named(COLLIDING_MARKETS.filter((o) => o.market_id === 37))
    expect(priceMarket(combo, '1x2', 'home').status).toBe('unavailable')
  })
})

// ── 4. An outlier bookmaker won through maximum selection ──────────────────

describe('regression 4 — maximum-price selection captured the outlier book', () => {
  const payload = named(X12)

  it('old algorithm published the single best quote', () => {
    expect(legacyX12(payload, 'Home')).toBe(2.53)
  })

  it('canonical selection publishes the lower median', () => {
    const price = verified(priceMarket(payload, '1x2', 'home'))

    // Quotes: 2.40 (Unibet), 2.45 (888sport), 2.53 (Marathonbet).
    expect(price.odds).toBe(2.45)
    expect(price.bookmaker.name).toBe('888sport')
    expect(price.provenance.odds_bookmaker_count).toBe(3)
    expect(price.provenance.odds_min).toBe(2.4)
    expect(price.provenance.odds_max).toBe(2.53)
  })

  it('the published price is never the maximum when books disagree', () => {
    const price = verified(priceMarket(payload, '1x2', 'home'))
    expect(price.odds).toBeLessThan(price.provenance.odds_max)
  })

  it('payload order does not change the result', () => {
    const forward = verified(priceMarket(payload, '1x2', 'home'))
    const reversed = verified(priceMarket([...payload].reverse(), '1x2', 'home'))

    expect(reversed.odds).toBe(forward.odds)
    expect(reversed.provenance.odds_entry_id).toBe(forward.provenance.odds_entry_id)
  })
})

// ── 5. No valid quote previously rendered as 1.00 ──────────────────────────

describe('regression 5 — the 1.00 placeholder', () => {
  // Colliding markets only: nothing here prices full-match BTTS.
  const payload = named(COLLIDING_MARKETS)

  it('old algorithm displayed a price of exactly 1', () => {
    expect(legacyBtts(payload, 'yes')).toBe(1)
  })

  it('canonical selection returns a typed unavailable result with no price', () => {
    const price = priceMarket(payload, 'btts', 'yes')

    expect(price.status).toBe('unavailable')
    expect(price.unavailable_reason).toBe('market_not_offered')
    expect(price.odds).toBeUndefined()
    expect(price.provenance).toBeUndefined()
  })

  it('no expected value is computed without a price', () => {
    const price = priceMarket(payload, 'btts', 'yes')

    expect(expectedValue(0.62, price)).toBeNull()
    expect(canPublishPrice({ ...price, odds: undefined })).toBe(false)
  })

  it('a quote of exactly 1.00 is rejected rather than published', () => {
    const worthless = named([
      { ...CORRECT_OU_25[0], value: '1.00' },
      { ...CORRECT_OU_25[2], value: '1.0' },
    ])
    const price = priceMarket(worthless, 'over_under_2.5', 'over')

    expect(price.status).toBe('unavailable')
    expect(price.unavailable_reason).toBe('no_valid_price')
  })

  it('a stopped or suspended quote is not a price', () => {
    const halted = named(
      CORRECT_OU_25.filter((o) => o.label === 'Over').map((o, i) =>
        i % 2 === 0 ? { ...o, stopped: true } : { ...o, suspended: true },
      ),
    )
    const price = priceMarket(halted, 'over_under_2.5', 'over')

    expect(price.status).toBe('unavailable')
    expect(price.unavailable_reason).toBe('all_entries_stopped')
  })

  it('the live production symptom is reproduced and corrected', () => {
    // Fixture 19726112 (Club Brugge v KV Kortrijk) served Over 2.5 at 3.00 with
    // probability 0.5768, published as "+73.0% Expected Value", beside BTTS and
    // Double Chance both showing 1.00.
    const modelProbability = 0.5768
    const defectPrice = 3.0
    expect(modelProbability * defectPrice - 1).toBeCloseTo(0.7304, 4)

    const corrected = verified(priceMarket(named(FULL_PAYLOAD), 'over_under_2.5', 'over'))
    const correctedEV = expectedValue(modelProbability, corrected)

    expect(corrected.odds).toBe(1.6)
    expect(correctedEV).not.toBeNull()
    expect(correctedEV!).toBeLessThan(0)
  })
})

// ── 6. Multi-bookmaker lower_median_v1 ─────────────────────────────────────

describe('regression 6 — deterministic lower median across books', () => {
  const overQuotes = named(CORRECT_OU_25.filter((o) => o.label === 'Over'))

  it('selects the lower middle quote, never the best', () => {
    const price = verified(priceMarket(overQuotes, 'over_under_2.5', 'over'))

    // 1.58, 1.60, 1.60, 1.61, 1.62 -> lower median 1.60.
    expect(price.odds).toBe(1.6)
    expect(price.provenance.odds_bookmaker_count).toBe(5)
    expect(price.provenance.odds_min).toBe(1.58)
    expect(price.provenance.odds_max).toBe(1.62)
  })

  it('takes the lower of the two middles with an even number of books', () => {
    const four = overQuotes.slice(0, 4)
    const prices = four
      .map((o) => Number(o.value))
      .sort((a, b) => a - b)
    const price = verified(priceMarket(four, 'over_under_2.5', 'over'))

    expect(price.odds).toBe(prices[1])
    expect(price.odds).toBeLessThanOrEqual(prices[2])
  })

  it('records complete provenance for the selected quote', () => {
    const price = verified(priceMarket(overQuotes, 'over_under_2.5', 'over'))

    expect(isProvenanceComplete(price.provenance)).toBe(true)
    expect(canPublishPrice({ odds: price.odds, price_status: 'verified', odds_provenance: price.provenance })).toBe(true)
    expect(price.provenance.odds_selection_policy).toBe('lower_median_v1')
    expect(price.provenance.odds_captured_at).toBeTruthy()
  })

  it('refuses to publish when the bookmaker name is missing', () => {
    // Dropping the `odds.bookmaker` include leaves provenance incomplete. The
    // price must then read unavailable rather than be shown without a source.
    const anonymous = CORRECT_OU_25.filter((o) => o.label === 'Over')
    const price = verified(priceMarket(anonymous, 'over_under_2.5', 'over'))

    expect(price.provenance.odds_bookmaker_name).toBeNull()
    expect(isProvenanceComplete(price.provenance)).toBe(false)
    expect(canPublishPrice({ odds: price.odds, price_status: 'verified', odds_provenance: price.provenance })).toBe(false)
  })
})

// ── Cross-surface consistency ──────────────────────────────────────────────

describe('every surface prices the same payload identically', () => {
  const payload = named(FULL_PAYLOAD)
  const ctx = { homeTeam: 'Cambuur Leeuwarden', awayTeam: 'Excelsior' }

  it.each([
    ['over_under_2.5', 'over'],
    ['over_under_2.5', 'under'],
    ['btts', 'yes'],
    ['btts', 'no'],
    ['1x2', 'home'],
    ['1x2', 'draw'],
    ['1x2', 'away'],
    ['double_chance', '1X'],
    ['double_chance', 'X2'],
    ['double_chance', '12'],
  ] as const)('%s / %s resolves to one value regardless of caller', (market, outcome) => {
    // Fixture detail, recommendation ingestion and the publication queue all
    // reach the price through this one function. Calling it repeatedly stands in
    // for calling it from different modules: the contract is that the payload
    // alone determines the answer.
    const first = priceMarket(payload, market, outcome, ctx)
    const second = priceMarket([...payload].reverse(), market, outcome, ctx)
    const third = priceMarket(payload, market, outcome, ctx)

    expect(second).toEqual(first)
    expect(third).toEqual(first)
  })

  it('the same market cannot yield different prices on different pages', () => {
    const detail = priceMarket(payload, 'over_under_2.5', 'over', ctx)
    const ingestion = priceMarket(payload, 'over_under_2.5', 'over')

    expect(verified(ingestion).odds).toBe(verified(detail).odds)
    expect(verified(ingestion).provenance.odds_entry_id).toBe(
      verified(detail).provenance.odds_entry_id,
    )
  })
})

// ── The duplicated selector is gone, not merely bypassed ───────────────────

const read = (rel: string) => readFileSync(join(process.cwd(), rel), 'utf-8')

describe('fixture detail no longer owns a selection contract', () => {
  const src = read('src/services/fixtureService.ts')

  it('delegates pricing to the canonical module', () => {
    expect(src).toContain("from '@/app/lib/marketPricing'")
    expect(src).toContain('priceMarket(')
  })

  it('declares no market ids of its own', () => {
    expect(src).not.toMatch(/market_id\s*===\s*\d+/)
  })

  it('matches no market by substring', () => {
    expect(src).not.toMatch(/\.includes\(['"]2\.5['"]\)/)
    expect(src).not.toMatch(/\.includes\(['"]btts['"]\)/)
    expect(src).not.toMatch(/\.includes\(['"]over\/under['"]\)/)
  })

  it('carries no maximum-price selection', () => {
    expect(src).not.toContain('maxVal')
    expect(src).not.toContain('bestOddEntry')
  })

  it('has no numeric placeholder standing in for a missing price', () => {
    expect(src).not.toMatch(/let\s+oddsValue\s*=\s*1\b/)
  })

  it('does not guess bookmaker names from an id table', () => {
    expect(src).not.toContain('bookmakerMap')
    expect(src).not.toContain('getBookmakerName')
  })

  it('publishes no fabricated interval', () => {
    expect(src).not.toContain('confidence_interval')
    expect(src).not.toContain('upper_bound')
  })
})

describe('recommendation ingestion uses the same contract', () => {
  const src = read('app/api/recommendations/route.ts')

  it('prices through the shared module', () => {
    expect(src).toContain("from '@/app/lib/marketPricing'")
    expect(src).toContain('priceMarket(')
  })

  it('has no placeholder price', () => {
    expect(src).not.toMatch(/provenance\.odds\s*:\s*1\b/)
  })

  it('cannot recommend a market without a canonical price', () => {
    expect(src).toContain('clearsEV(')
  })
})

describe('the card reads status, not magnitude', () => {
  const src = read('app/components/RecommendationCard.tsx')

  it('asks the canonical contract whether a price may be shown', () => {
    expect(src).toContain('canPublishPrice')
    expect(src).toContain('const priceVerified = canPublishPrice(priceSource)')
  })

  it('no longer gates on a bare odds floor or an EV ceiling', () => {
    expect(src).not.toContain('MIN_USABLE_ODDS')
    expect(src).not.toContain('MAX_PUBLISHABLE_EV')
  })

  it('does not re-derive market identity', () => {
    expect(src).not.toMatch(/market_id/)
  })

  it('states the unavailable case in both languages', () => {
    expect(src).toContain('priceUnavailableLabel')
    expect(src).toContain("language === 'ro' ? 'Valoare neverificată' : 'Value not verified'")
  })

  it('keeps the live-signal framing intact', () => {
    expect(src).toContain("'SEMNAL LIVE' : 'LIVE SIGNAL'")
    expect(src).toContain('is not part of the verified record unless')
    expect(src).toContain("'Scor semnal' : 'Signal score'")
  })
})

// ── The edge claim priced a different market than it predicted ─────────────

describe('regression 7 — edge compared against an unrelated leg', () => {
  const src = read('app/components/RecommendationCard.tsx')

  /*
   * SUPERSEDED CONTRACT, deliberately.
   *
   * These three assertions pinned the REPAIRED comparison panel: implied
   * probability taken from the predicted market's own price, gated on the
   * canonical status. The 2026-08-06 public-truth pass removed the panel
   * entirely instead, because a correct subtraction of a price-implied
   * probability from an uncalibrated ranking is still not an edge.
   *
   * Deleting the comparison satisfies the original defect strictly more than
   * repairing it did, so these now assert absence. The reproduction test below
   * is untouched — the arithmetic of the original defect is still the record of
   * what went wrong.
   */
  it('publishes no implied-probability comparison at all', () => {
    expect(src).not.toContain('const marketImplied =')
    expect(src).not.toMatch(/1 \/ \(priceSource\.odds as number\)/)
  })

  /** Comments name the defect they removed; only rendered code is scanned. */
  const rendered = src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .map((line) => line.replace(/\/\/.*$/, ''))
    .join('\n')

  it('no longer string-matches the outcome against the 1X2 board', () => {
    // The odds board still DISPLAYS home/draw/away quotes — clearly labelled as
    // unverified and informational, which is honest. What must never return is
    // a leg being selected by outcome name to stand in for the predicted
    // market's price. That selection pattern is what is asserted absent.
    expect(rendered).not.toMatch(/outcome === 'home' \? recommendation\.odds_data\?\.home/)
    expect(rendered).not.toMatch(/predicted_outcome[^\r\n]*toLowerCase\(\)[\s\S]{0,200}odds_data\?\.away/)
  })

  it('renders no edge figure under any gate', () => {
    expect(rendered).not.toContain('Edge vs Market')
    expect(rendered).not.toContain('Edge vs Piață')
    expect(rendered).not.toMatch(/const edge = /)
  })

  it('reproduces the live figures the defect produced', () => {
    // Malmö FF v Degerfors, 2026-08-03. Best market BTTS Yes, model 62%,
    // canonical price 1.73 (888Sport). The block read the AWAY price, 5.65.
    const modelProbability = 62
    const awayImplied = (1 / 5.65) * 100
    const bttsImplied = (1 / 1.73) * 100

    expect(Math.round(awayImplied)).toBe(18)
    expect(Math.round(modelProbability - awayImplied)).toBe(44)

    // Against the price actually being predicted, the edge is single digits and
    // consistent with the +6.8% expected value shown beside it.
    expect(Math.round(bttsImplied)).toBe(58)
    expect(Math.round(modelProbability - bttsImplied)).toBe(4)
  })
})
