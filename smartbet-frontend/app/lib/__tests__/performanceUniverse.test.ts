import { describe, it, expect } from 'vitest'
import { existsSync, readFileSync } from 'fs'
import { join } from 'path'

/**
 * ONE performance universe, ONE staking position.
 *
 * A public skeptic (2026-08-08) found the product contradicting itself on two
 * axes at once:
 *
 *   1. /monitoring published an accuracy percentage, a dollar P/L and per-row
 *      ROI computed over legacy rows whose prices /track-record explicitly
 *      excludes — while the same page's summary said "no settled results yet".
 *      It also quoted per-row odds picked by string-matching the outcome
 *      against the 1X2 board, so a BTTS row showed a 1X2 price (Cardiff BTTS:
 *      1.80 committed vs 8.70 displayed).
 *   2. The bankroll setup endorsed Fractional Kelly as "⭐ Recommended" citing
 *      "backtested +540% growth over 275 bets" — a figure computed on the
 *      pre-cutoff odds data later shown to be captured from the wrong market,
 *      and a staking method that requires the calibrated edge estimate the
 *      product says it does not have.
 *
 * These tests pin both retractions. They are surface scans because that is
 * what the defect was: claims living in JSX that no unit test ever read.
 */

const root = join(__dirname, '..', '..', '..')
const read = (p: string) => readFileSync(join(root, p), 'utf-8').replace(/\r\n/g, '\n')

const MONITORING_TABLE = read('app/components/RecommendedPredictionsTable.tsx')
const MONITORING_ROUTE = read('app/api/django/recommended-predictions/route.ts')
const BANKROLL_MODAL = read('app/components/BankrollSetupModal.tsx')
const DASHBOARD_CARDS = read('app/components/dashboard/PersonalizedRecommendations.tsx')

/** Strip comments so a retired claim quoted in an explanation cannot fail. */
const scannable = (src: string) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1')

describe('the monitoring page publishes no performance figure', () => {
  const rendered = scannable(MONITORING_TABLE)

  it.each([
    'Total P/L',
    'profit_loss_10',
    'total_profit_loss',
    'average_roi',
    'roi_percent',
    '% ROI',
    'Avg ROI',
    'edge_vs_market',
    'implied_baseline',
  ])('does not render %s', (banned) => {
    expect(rendered).not.toContain(banned)
  })

  it('publishes no accuracy percentage over the legacy universe', () => {
    expect(rendered).not.toContain('summary.accuracy')
    expect(rendered).not.toContain('Accuracy')
  })

  it('points performance claims at the verified record instead', () => {
    expect(MONITORING_TABLE).toContain('/track-record')
    expect(MONITORING_TABLE).toContain('not a performance record')
  })

  it('reconciles its counters against the table, not just arithmetically', () => {
    // 317 tracked / 296 completed / 13 pending left 8 rows unexplained. The
    // first fix invented a "no usable result" bucket for them — wrong: those
    // 8 ARE graded, they are audit-excluded, and the table showed 178 + 126 =
    // 304 graded rows against a headline claiming 296.
    expect(MONITORING_ROUTE).toContain('audit_excluded')
    expect(MONITORING_ROUTE).toContain('graded')
    expect(MONITORING_TABLE).toContain('Graded against a final score')
    expect(MONITORING_TABLE).toContain('Of those, audit-excluded')
    // The retired, incorrect label must not come back.
    expect(MONITORING_TABLE).not.toContain('no_usable_result')
    expect(MONITORING_TABLE).not.toContain('Postponed, abandoned or ungraded')
  })
})

describe('the monitoring payload carries no price', () => {
  const rendered = scannable(MONITORING_TABLE)

  it('never picks a price by string-matching the outcome against the 1X2 board', () => {
    // This exact pattern produced the wrong-market prices on BTTS/O-U rows.
    expect(rendered).not.toMatch(/outcome === 'home' \? pred\.odds_home/)
    expect(rendered).not.toContain('odds_home')
    expect(rendered).not.toContain('odds_away')
  })

  it('the proxy serializes an allowlist, not the raw Django row', () => {
    expect(MONITORING_ROUTE).toContain('toMonitoringRow')
    expect(MONITORING_ROUTE).not.toContain('...item')
    for (const leaked of [
      'odds_home', 'odds_draw', 'odds_away', 'bookmaker',
      'profit_loss_10', 'roi_percent', 'expected_value', 'stake_recommendation',
    ]) {
      // Present only inside the DTO's own comment block, never as a field.
      expect(scannable(MONITORING_ROUTE)).not.toContain(leaked)
    }
  })
})

describe('no staking method is endorsed and no growth figure is claimed', () => {
  const rendered = scannable(BANKROLL_MODAL)

  it.each(['540', 'backtested', 'Recommended)', '⭐'])(
    'the bankroll setup no longer contains %s',
    (banned) => {
      expect(rendered).not.toContain(banned)
    },
  )

  it('does not default the user into a Kelly strategy', () => {
    expect(rendered).toContain("stakingStrategy: 'fixed_amount'")
    expect(rendered).not.toContain("stakingStrategy: 'kelly_fractional'")
  })

  it('offers no edge-based staking method at all', () => {
    // First response was to keep Kelly but warn about it. That still
    // contradicted "BetGlitch does not size bets for you", so after the
    // score's measured AUC came in at 0.554 the options were removed
    // outright — the bankroll is a journal, not a staking engine.
    // Kelly may still be NAMED — the copy explains why it is not offered —
    // but it must not exist as a selectable option anywhere.
    const rendered = scannable(BANKROLL_MODAL)
    expect(rendered).not.toContain("value: 'kelly'")
    expect(rendered).not.toContain("value: 'kelly_fractional'")
    expect(rendered).toContain("value: 'fixed_amount'")
    expect(rendered).toContain("value: 'fixed_percentage'")

    // ...and the dead component that still labelled Kelly strategies is gone.
    expect(existsSync(join(root, 'app/components/StakeRecommendation.tsx')))
      .toBe(false)
  })

  it('says plainly what the bankroll page is, in both languages', () => {
    expect(BANKROLL_MODAL).toContain('This is a journal of bets you choose')
    expect(BANKROLL_MODAL).toContain('Acesta este un jurnal al pariurilor')
  })

  it('offers no one-click staking instruction on the dashboard', () => {
    const dash = scannable(DASHBOARD_CARDS)
    expect(dash).not.toContain('Place Bet')
    expect(dash).not.toContain('recommended_stake')
    expect(dash).not.toContain('stake_recommendation')
  })
})

describe('one number, one notation', () => {
  it('the all-markets grid states the score as N / 100, never a percentage', () => {
    const card = read('app/components/RecommendationCard.tsx')
    expect(card).not.toContain('{(market.probability * 100).toFixed(0)}%')
    expect(card).toContain('{(market.probability * 100).toFixed(0)} / 100')
  })
})

describe('navigation gives feedback while the provider is slow', () => {
  it('the prediction route has a loading boundary', () => {
    // "View full match analysis" appeared dead: the server component was
    // fetching fixture detail with no loading state for several seconds.
    const loading = read('app/prediction/[...slug]/loading.tsx')
    expect(loading).toContain('export default function Loading')
  })
})

describe('Explore shows content before the visitor searches', () => {
  const explore = read('app/explore/ExploreContent.tsx')
  const searchRoute = read('app/api/search/route.ts')

  it('browses upcoming fixtures with no query and no league', () => {
    expect(explore).not.toContain('if (!selectedLeague) return')
    expect(searchRoute).toContain("searchParams.get('mode') === 'browse'")
    expect(searchRoute).toContain('!query && !league && !isBrowse')
  })
})

describe('no surface claims an AI model BetGlitch does not own', () => {
  /**
   * The English copy was cleaned in an earlier truth pass; the Romanian
   * strings kept "Modelele noastre AI" and "predicțiile AI" for weeks, and a
   * reviewer noted the site advertises AI while stating it trains no
   * predictive model. Scanning ONE language is how that survived.
   */
  const translations = read('app/locales/translations.ts')
  const service = read('src/services/fixtureService.ts')

  it.each([
    'Modelele noastre AI',
    'predicțiile AI',
    'analiza AI',
    'AI analysis',
    'Our AI models',
    'AI-powered',
  ])('no language contains %s', (banned) => {
    expect(translations).not.toContain(banned)
  })

  it('the fixture payload does not label its source as AI', () => {
    expect(service).not.toContain("source: 'AI'")
  })
})
