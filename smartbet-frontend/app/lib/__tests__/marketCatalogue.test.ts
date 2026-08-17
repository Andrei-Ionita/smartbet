import { describe, expect, it } from 'vitest'
import { buildMarketCatalogue } from '../marketCatalogue'
import type { SportMonksOdd } from '../oddsSelection'

const odd = (input: Partial<SportMonksOdd>): SportMonksOdd => ({
  id: 1,
  fixture_id: 99,
  market_id: 6,
  bookmaker_id: 2,
  label: 'Home',
  value: '1.90',
  handicap: '-1.5',
  market_description: 'Asian Handicap',
  latest_bookmaker_update: '2026-08-15 10:00:00',
  bookmaker: { id: 2, name: 'Book A' },
  ...input,
})

describe('buildMarketCatalogue', () => {
  it('groups opposite handicap selections on the same absolute line', () => {
    const catalogue = buildMarketCatalogue([
      odd({ id: 1, handicap: '-1.5', label: 'Home', value: '1.90' }),
      odd({ id: 2, handicap: '+1.5', label: 'Away', value: '1.92' }),
    ])

    expect(catalogue.market_count).toBe(1)
    expect(catalogue.markets[0].lines).toHaveLength(1)
    expect(catalogue.markets[0].lines[0].label).toBe('Handicap 1.5')
    expect(catalogue.markets[0].lines[0].selections.map((selection) => selection.label))
      .toEqual(['Away +1.5', 'Home -1.5'])
    expect(catalogue.markets[0].consideration_status).toBe('shadow')
  })

  it('uses a deterministic lower median reference price', () => {
    const catalogue = buildMarketCatalogue([
      odd({ id: 3, value: '2.10', bookmaker_id: 3, bookmaker: { id: 3, name: 'Book C' } }),
      odd({ id: 1, value: '1.80', bookmaker_id: 1, bookmaker: { id: 1, name: 'Book A' } }),
      odd({ id: 2, value: '2.00', bookmaker_id: 2, bookmaker: { id: 2, name: 'Book B' } }),
      odd({ id: 4, value: '2.30', bookmaker_id: 4, bookmaker: { id: 4, name: 'Book D' } }),
    ])
    const selection = catalogue.markets[0].lines[0].selections[0]

    expect(selection.reference_price).toBe(2.00)
    expect(selection.bookmaker).toBe('Book B')
    expect(selection.bookmaker_count).toBe(4)
    expect(selection.price_min).toBe(1.80)
    expect(selection.price_max).toBe(2.30)
  })

  it('excludes stopped, anonymous and undated quotes', () => {
    const catalogue = buildMarketCatalogue([
      odd({ stopped: true }),
      odd({ bookmaker: null }),
      odd({ latest_bookmaker_update: null }),
    ])

    expect(catalogue.market_count).toBe(0)
    expect(catalogue.selection_count).toBe(0)
  })

  it('marks supported total lines as modelled and other lines as shadow', () => {
    const catalogue = buildMarketCatalogue([
      odd({ market_id: 7, market_description: 'Goal Line', handicap: null, total: '2.5', label: 'Over' }),
      odd({ market_id: 105, market_description: 'Alternative Goal Line', handicap: null, total: '2.75', label: 'Over' }),
    ])

    expect(catalogue.markets.find((market) => market.market_id === 7)?.consideration_status).toBe('modelled')
    expect(catalogue.markets.find((market) => market.market_id === 105)?.consideration_status).toBe('shadow')
  })

  it('shows team totals as shadow research rather than prices-only', () => {
    const catalogue = buildMarketCatalogue([
      odd({
        market_id: 86, market_description: 'Team Total Goals',
        handicap: null, total: 'Over 1.5', label: '1',
      }),
    ])

    expect(catalogue.markets[0].consideration_status).toBe('shadow')
  })
})
