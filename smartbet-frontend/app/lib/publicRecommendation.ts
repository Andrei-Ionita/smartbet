/**
 * The public shape of a recommendation.
 *
 * Until now the route returned its internal working object verbatim. That
 * object carries everything the ranking pipeline needs — expected value, the
 * pre-adjustment EV, the value-zone classification, the internal score
 * components — and all of it reached the browser. Successive passes deleted
 * fields one at a time as each was noticed, which is a denylist: it protects
 * only against the leaks someone already found. `value_zone.original_ev`
 * survived three separate truth passes that way.
 *
 * This module inverts that. `toPublicRecommendation` builds a NEW object
 * containing only named fields. Anything added to the internal object in future
 * is invisible to the public API until someone deliberately adds it here, and
 * the contract test in __tests__/publicApiContract.test.ts runs the real
 * serializer over a realistic internal object and recursively rejects any
 * EV-, edge- or calibration-shaped key or string.
 *
 * WHY NO EXPECTED VALUE. EV is computed from the signal score. The signal score
 * is a relative ranking of BetGlitch's preference among the outcomes in one
 * market — not a calibrated probability. An EV derived from it has the shape of
 * an expected value without the meaning of one, so publishing any figure, zone
 * or warning built on it asserts an assessment BetGlitch has never validated.
 * That includes the value-zone warning "Extreme EV detected — likely odds
 * error": inferring a bookmaker pricing error from an uncalibrated number is
 * exactly the claim we cannot support.
 *
 * The ranking pipeline keeps using EV internally, unchanged. This is a
 * publication boundary, not a calculation change.
 */

/** Provenance for a recorded price. Auditable, and free of any value claim. */
export interface PublicOddsProvenance {
  odds_market_id?: number | null
  odds_market_name?: string | null
  odds_bookmaker_id?: number | null
  odds_bookmaker_name?: string | null
  odds_captured_at?: string | null
  odds_label?: string | null
}

export interface PublicBestMarket {
  type: string
  name: string
  display_name: string
  predicted_outcome: string
  /** Raw public signal score, 0-1. A relative ranking, NOT a probability. */
  probability: number
  /** Distance to the next-ranked outcome. Structural, not a value claim. */
  probability_gap: number | null
  odds: number | null
  bookmaker?: string | null
  odds_provenance: PublicOddsProvenance | null
}

export interface PublicRecommendation {
  fixture_id: number
  home_team: string
  away_team: string
  home_id: number | null
  away_id: number | null
  season_id: number | null
  league: string
  kickoff: string
  predicted_outcome: string
  /** Raw public signal score, 0-1. A relative ranking, NOT a probability. */
  confidence: number
  odds: number | null
  bookmaker?: string | null
  odds_provenance: PublicOddsProvenance | null
  probabilities: unknown
  odds_data: unknown
  teams_data: unknown
  explanation: string
  best_market: PublicBestMarket | null
  all_markets: Array<{
    type: string
    name: string
    predicted_outcome: string
    probability: number
    odds: number | null
  }>
  is_recommended?: boolean
}

const pickProvenance = (raw: unknown): PublicOddsProvenance | null => {
  if (!raw || typeof raw !== 'object') return null
  const p = raw as Record<string, unknown>
  return {
    odds_market_id: (p.odds_market_id as number) ?? null,
    odds_market_name: (p.odds_market_name as string) ?? null,
    odds_bookmaker_id: (p.odds_bookmaker_id as number) ?? null,
    odds_bookmaker_name: (p.odds_bookmaker_name as string) ?? null,
    odds_captured_at: (p.odds_captured_at as string) ?? null,
    odds_label: (p.odds_label as string) ?? null,
  }
}

/**
 * Project one internal recommendation onto the public contract.
 *
 * Allowlist only — every field is named explicitly. Never spread the source
 * object, and never add a field here without deciding it is publishable.
 *
 * Deliberately NOT copied: expected_value, ev, original_ev, adjusted_ev,
 * original_probability, market_score, revenue_vs_risk_score, signal_quality,
 * enhancement_data (value_zone, adjustments_applied), debug_info
 * (confidence_score, variance, value_zone), and every Variant-B, activation or
 * calibration field. Each is either EV-derived, a quality grade the product
 * cannot justify, or internal machinery.
 */
export function toPublicRecommendation(rec: Record<string, any>): PublicRecommendation {
  const bm = rec.best_market as Record<string, any> | undefined

  return {
    fixture_id: rec.fixture_id,
    home_team: rec.home_team,
    away_team: rec.away_team,
    home_id: rec.home_id ?? null,
    away_id: rec.away_id ?? null,
    season_id: rec.season_id ?? null,
    league: rec.league,
    kickoff: rec.kickoff,
    predicted_outcome: rec.predicted_outcome,
    confidence: rec.confidence,
    odds: rec.odds ?? null,
    bookmaker: rec.bookmaker ?? bm?.bookmaker ?? null,
    odds_provenance: pickProvenance(rec.odds_provenance),
    probabilities: rec.probabilities ?? null,
    odds_data: rec.odds_data ?? null,
    teams_data: rec.teams_data ?? null,
    explanation: rec.explanation,
    best_market: bm
      ? {
        type: bm.type,
        name: bm.name,
        display_name: bm.display_name,
        predicted_outcome: bm.predicted_outcome,
        probability: bm.probability,
        probability_gap: bm.probability_gap ?? null,
        odds: bm.odds ?? null,
        bookmaker: bm.bookmaker ?? null,
        odds_provenance: pickProvenance(bm.odds_provenance),
      }
      : null,
    // Market comparison without the scores that rank them: a visitor can see
    // which outcomes were considered and at what price, but market_score and
    // expected_value are ranking internals and `is_recommended` restated a
    // filter verdict as an endorsement.
    all_markets: Array.isArray(rec.all_markets)
      ? rec.all_markets.map((m: Record<string, any>) => ({
        type: m.type,
        name: m.name,
        predicted_outcome: m.predicted_outcome,
        probability: m.probability,
        odds: m.odds ?? null,
      }))
      : [],
    // `is_recommended` is NOT published. It is true for every row the ranking
    // put in the top ten, so as a field it carries no information a reader
    // could act on — while its name asserts an endorsement the product does
    // not make. The card's own layout already shows which market led.
  }
}

/** Envelope counters. `confidence_threshold` is a filter internal — omitted. */
export function toPublicRecommendationList(recs: Array<Record<string, any>>) {
  return recs.map(toPublicRecommendation)
}
