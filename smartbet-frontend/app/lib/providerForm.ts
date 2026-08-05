/**
 * THE canonical parser for SportMonks team form.
 *
 * One interpretation, shared by /api/recommendations and /api/internal/evidence,
 * so the same fixture and payload can never produce two different multipliers.
 *
 * WHAT THE PROVIDER ACTUALLY RETURNS (verified in production 2026-08-05)
 * ---------------------------------------------------------------------
 * `standings/seasons/{season_id}?include=form` returns rows shaped:
 *
 *   { participant_id, position, points, ...,
 *     form: [ { fixture_id, form: 'W', sort_order: 1, standing_id, ... }, ... ] }
 *
 * `form` is an ARRAY of one-letter results with an explicit `sort_order`, NOT a
 * string. `teams/multi/{ids}?include=form` returns 403 on this subscription and
 * must not be used.
 *
 * THE BUG THIS REPLACES
 * ---------------------
 * The live route did `typeof p.form === 'string' ? p.form : JSON.stringify(p.form)`
 * and fed the result to calculateFormMomentum, which reads the first five
 * characters looking for W/D/L. On an array that yields `[{"id`, which contains
 * no result letters, so every fixture scored 0 wins / 0 draws / 0 losses and the
 * multiplier collapsed to 1.0. The heuristic has therefore been inert in
 * production — see PARSE_FORM_NOTES below.
 *
 * Availability is genuinely partial: cups return no standings at all, and some
 * leagues return standings with no form relation. That is reported as a
 * structured reason, never smoothed into a default.
 */

export type FormMissingReason =
  | 'provider_form_unavailable'
  | 'provider_form_incomplete'
  | 'provider_form_parse_error'
  | 'fixture_team_mapping_missing'

export interface ParsedForm {
  /** Most-recent-first W/D/L letters, at most 5. Empty when unavailable. */
  letters: string
  /** How many results the provider actually supplied. */
  count: number
  available: boolean
  reason: FormMissingReason | ''
}

const EMPTY = (reason: FormMissingReason): ParsedForm => ({
  letters: '',
  count: 0,
  available: false,
  reason,
})

/** Minimum results before the momentum heuristic means anything. It reads up to
 *  five and weights them; fewer than three is noise. */
export const MIN_FORM_RESULTS = 3

/**
 * Parse one standings row's `form` relation into ordered W/D/L letters.
 *
 * `sort_order` is authoritative for ordering — array order is not guaranteed —
 * and 1 is the most recent result, matching how calculateFormMomentum weights
 * index 0 highest.
 */
export function parseStandingForm(raw: unknown): ParsedForm {
  if (raw === null || raw === undefined) return EMPTY('provider_form_unavailable')

  // A plain string is accepted defensively: some endpoints have historically
  // returned "WWDLW" directly, and rejecting it would lose real data.
  if (typeof raw === 'string') {
    const letters = raw.toUpperCase().replace(/[^WDL]/g, '').slice(0, 5)
    if (!letters) return EMPTY('provider_form_unavailable')
    return {
      letters,
      count: letters.length,
      available: letters.length >= MIN_FORM_RESULTS,
      reason: letters.length >= MIN_FORM_RESULTS ? '' : 'provider_form_incomplete',
    }
  }

  if (!Array.isArray(raw)) return EMPTY('provider_form_parse_error')
  if (raw.length === 0) return EMPTY('provider_form_unavailable')

  const entries: { order: number; letter: string }[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') return EMPTY('provider_form_parse_error')
    const value = (item as any).form
    if (typeof value !== 'string') return EMPTY('provider_form_parse_error')
    const letter = value.trim().toUpperCase()
    if (!'WDL'.includes(letter) || letter.length !== 1) continue
    const order = Number((item as any).sort_order)
    entries.push({ order: Number.isFinite(order) ? order : entries.length + 1, letter })
  }

  if (!entries.length) return EMPTY('provider_form_unavailable')

  entries.sort((a, b) => a.order - b.order)
  const letters = entries.slice(0, 5).map((e) => e.letter).join('')
  return {
    letters,
    count: letters.length,
    available: letters.length >= MIN_FORM_RESULTS,
    reason: letters.length >= MIN_FORM_RESULTS ? '' : 'provider_form_incomplete',
  }
}

/**
 * Build participant_id -> ParsedForm from standings responses.
 * Accepts the raw `{ data: [...] }` bodies so callers need no reshaping.
 */
export function buildFormMap(
  standingsResponses: Array<{ data?: unknown[] } | null | undefined>,
): Map<number, ParsedForm> {
  const map = new Map<number, ParsedForm>()
  for (const response of standingsResponses) {
    for (const row of (response?.data as any[]) || []) {
      const id = Number(row?.participant_id)
      if (!Number.isFinite(id)) continue
      const parsed = parseStandingForm(row?.form)
      // Keep the richest observation if a team appears in several groups.
      const existing = map.get(id)
      if (!existing || parsed.count > existing.count) map.set(id, parsed)
    }
  }
  return map
}

/** Look up one team, distinguishing "no such team" from "team has no form". */
export function formFor(
  map: Map<number, ParsedForm>,
  teamId: number | undefined | null,
): ParsedForm {
  if (teamId === undefined || teamId === null || !Number.isFinite(Number(teamId))) {
    return EMPTY('fixture_team_mapping_missing')
  }
  return map.get(Number(teamId)) ?? EMPTY('provider_form_unavailable')
}

/**
 * PARSE_FORM_NOTES — recorded so the next reader does not have to rediscover it.
 *
 * Verified against production on 2026-08-05 across 12 seasons:
 *   * 7 seasons returned standings; 5 (all cups) returned none;
 *   * of those 7, some returned standings rows with no form relation at all.
 * So even a correct parser cannot reach full coverage, and any market whose
 * fixtures are mostly cup ties will stay largely form-less. That is a property
 * of the data, not of this code.
 */
