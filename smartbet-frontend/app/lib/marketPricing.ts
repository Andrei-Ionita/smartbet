/**
 * THE single market-pricing contract for every surface that shows a price.
 *
 * WHY THIS MODULE EXISTS
 * ----------------------
 * `app/lib/oddsSelection.ts` already defined the canonical market identities and
 * the deterministic `lower_median_v1` policy — but only ONE caller used it.
 * `src/services/fixtureService.ts`, which backs `/api/fixture/{id}`, the Explore
 * detail modal and every `/prediction/*` page, carried a second, independent
 * copy of the same logic. That copy was wrong in four separate ways:
 *
 *   - BTTS matched `market_id 28` ("1st Half Goals") instead of 14.
 *   - Over/Under matched `market_id 18` plus any label containing "2.5",
 *     which collides with markets 28/53/37/81/86/105/107.
 *   - It took the MAXIMUM quote across bookmakers, systematically capturing
 *     the single most mispriced book.
 *   - When nothing matched it left `oddsValue = 1`, and `1` then flowed into
 *     `EV = probability × odds − 1` as if it were a real quote.
 *
 * Observed live on fixture 19726112 before this module existed: Over 2.5 priced
 * at 3.00 (a second-half quote; the real full-time price was ~1.7-2.2) yielding
 * "+73.0% Expected Value", displayed beside BTTS and Double Chance both showing
 * exactly 1.00.
 *
 * Two equivalent copies of a selection rule is the defect, not the symptom. This
 * module is the one place a price becomes a *product* value: it wraps the
 * canonical selector in a typed result that makes "no price" impossible to
 * confuse with "a price of 1", and refuses to compute anything price-derived
 * when no correct quote exists.
 */

import {
  ODDS_SELECTION_POLICY,
  selectOdds,
  type OddsProvenance,
  type OddsUnavailableReason,
  type ProductMarket,
  type SportMonksOdd,
  type TeamContext,
} from './oddsSelection'

export type { OddsProvenance, OddsUnavailableReason, ProductMarket, TeamContext }

export interface PricedBookmaker {
  id: number | null
  name: string | null
}

/**
 * The result of pricing one product market + outcome.
 *
 * Deliberately a discriminated union. An unavailable price carries NO `odds`
 * field at all, so it cannot be read as a number by accident — the previous
 * `oddsValue = 1` placeholder was indistinguishable from a genuine (if useless)
 * quote at every call site downstream.
 */
export type MarketPrice =
  | {
      status: 'verified'
      odds: number
      bookmaker: PricedBookmaker
      provenance: OddsProvenance
      unavailable_reason?: undefined
    }
  | {
      status: 'unavailable'
      odds?: undefined
      bookmaker?: undefined
      provenance?: undefined
      unavailable_reason: OddsUnavailableReason
    }

/**
 * Provenance fields that must all be present for a price to be publishable.
 * Mirrors `REQUIRED_PROVENANCE_FIELDS` in `core/services/public_universe.py` —
 * the backend classifies a row as `missing_provenance` on exactly this set, so
 * the UI must not display as verified anything the write boundary would reject.
 */
export const REQUIRED_PROVENANCE_FIELDS = [
  'odds',
  'odds_market_id',
  'odds_label',
  'odds_bookmaker_id',
  'odds_bookmaker_name',
  'odds_captured_at',
  'odds_selection_policy',
] as const

/** Selection policies the verified record accepts. Mirrors the backend set. */
export const VERIFIED_ODDS_POLICIES: readonly string[] = [ODDS_SELECTION_POLICY]

/**
 * Price the given product market + outcome from a raw SportMonks odds array.
 *
 * All market identity, line matching, outcome matching, confusable rejection and
 * bookmaker policy live in `oddsSelection.ts`. This function adds no matching of
 * its own — that is the entire point.
 */
export function priceMarket(
  odds: SportMonksOdd[] | null | undefined,
  market: ProductMarket,
  outcome: string,
  ctx: TeamContext = {},
): MarketPrice {
  const selection = selectOdds(odds, market, outcome, ctx)

  if (!selection.ok) {
    return { status: 'unavailable', unavailable_reason: selection.reason }
  }

  const { provenance } = selection
  return {
    status: 'verified',
    odds: provenance.odds,
    bookmaker: {
      id: provenance.odds_bookmaker_id,
      name: provenance.odds_bookmaker_name,
    },
    provenance,
  }
}

/** Every field the verified record requires is present and non-empty. */
export function isProvenanceComplete(
  provenance: Partial<OddsProvenance> | null | undefined,
): boolean {
  if (!provenance) return false

  for (const field of REQUIRED_PROVENANCE_FIELDS) {
    const value = (provenance as Record<string, unknown>)[field]
    if (value === null || value === undefined || value === '') return false
  }

  if (VERIFIED_ODDS_POLICIES.indexOf(String(provenance.odds_selection_policy)) === -1) {
    return false
  }

  return typeof provenance.odds === 'number' && provenance.odds > 1
}

/**
 * The single question every price-dependent UI element must ask.
 *
 * A price is publishable only when the canonical selector produced it, the
 * provenance is complete and the recorded policy is one the verified record
 * accepts. Numerical plausibility (`odds > 1.01`) is NOT sufficient: it proves
 * the number looks like a price, not that it prices the intended bet.
 */
export function isPricePublishable(price: MarketPrice | null | undefined): boolean {
  if (!price || price.status !== 'verified') return false
  return isProvenanceComplete(price.provenance)
}

/**
 * The serialised shape a price arrives in once it has crossed an API boundary.
 * `MarketPrice` is a union; JSON is not, so surfaces receive these flat fields.
 */
export interface CanonicalPriceFields {
  price_status?: 'verified' | 'unavailable'
  odds_provenance?: OddsProvenance | null
  odds_unavailable_reason?: OddsUnavailableReason | string
}

export type PriceCarrier = CanonicalPriceFields & { odds?: number | null }

/**
 * Whether a UI may render price-derived values for this payload.
 *
 * This is the ONLY question a display component should ask about a price. It
 * deliberately cannot be satisfied by a plausible-looking number: the payload
 * must carry the canonical status AND complete provenance, which together prove
 * the quote came from the intended market via `lower_median_v1`.
 *
 * The gate this replaced was `odds > 1.01 && ev <= 0.20`. Both halves are
 * properties of the *number*, not of the *market*, so a second-half Over 2.5
 * quote at 3.00 passed it cleanly.
 */
export function canPublishPrice(source: PriceCarrier | null | undefined): boolean {
  if (!source) return false
  if (source.price_status !== 'verified') return false
  if (typeof source.odds !== 'number' || !(source.odds > 1)) return false
  return isProvenanceComplete(source.odds_provenance)
}

/**
 * Expected value, or `null` when there is no verified price.
 *
 * Returning `null` rather than a number is the contract: every caller is forced
 * to decide what to render when no EV exists, instead of silently publishing
 * `probability × 1 − 1`.
 */
export function expectedValue(
  probability: number,
  price: MarketPrice | null | undefined,
): number | null {
  if (!isPricePublishable(price) || !price || price.status !== 'verified') return null
  if (!Number.isFinite(probability) || probability <= 0) return null
  return probability * price.odds - 1
}

/** Bookmaker-implied probability, or `null` without a verified price. */
export function impliedProbability(price: MarketPrice | null | undefined): number | null {
  if (!isPricePublishable(price) || !price || price.status !== 'verified') return null
  return 1 / price.odds
}

/**
 * Why no price was shown, in both public languages.
 *
 * The user-facing string is intentionally the same for every reason — a visitor
 * does not need the taxonomy, only the honest statement that BetGlitch has no
 * price it would stand behind. The reason code is kept in the payload for
 * diagnosis.
 */
export const PRICE_UNAVAILABLE_COPY = {
  en: 'Verified price unavailable',
  ro: 'Preț verificat indisponibil',
} as const

export function priceUnavailableLabel(lang?: string): string {
  return lang === 'ro' ? PRICE_UNAVAILABLE_COPY.ro : PRICE_UNAVAILABLE_COPY.en
}

/** Diagnostic wording for the unavailable reason codes. Not user-facing copy. */
export const UNAVAILABLE_REASON_DETAIL: Record<OddsUnavailableReason, string> = {
  no_odds_payload: 'The provider returned no odds for this fixture.',
  market_not_offered: 'No bookmaker offers this market for this fixture.',
  line_not_offered: 'The market is offered but not on the required line.',
  outcome_not_offered: 'The line is offered but not for the predicted outcome.',
  all_entries_stopped: 'Every matching quote is stopped or suspended.',
  no_valid_price: 'No matching quote carries a price above 1.00.',
}
