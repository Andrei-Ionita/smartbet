/**
 * Public formatting for proof surfaces.
 *
 * Every published value a reader sees goes through here, so the card, the proof
 * page and the OG image can never drift into different renderings of the same
 * claim.
 */

/** Odds always carry two decimals: 1.80, never 1.8. */
export function formatOdds(odds: number | null | undefined): string {
  if (odds === null || odds === undefined || Number.isNaN(odds)) return 'n/a'
  return odds.toFixed(2)
}

const MARKET_NAMES: Record<string, string> = {
  btts: 'BTTS',
  over_under_2_5: 'Over/Under 2.5',
  'over_under_2.5': 'Over/Under 2.5',
  '1x2': 'Match Result',
  double_chance: 'Double Chance',
}

const MARKET_LONG: Record<string, string> = {
  btts: 'Both Teams to Score',
  'over_under_2.5': 'Over/Under 2.5 Goals',
  '1x2': 'Match Result',
  double_chance: 'Double Chance',
}

/**
 * Turn the stored market + outcome into public wording.
 * `btts` + `Btts yes` -> "BTTS — YES", never "btts — Btts yes".
 */
export function formatSelection(
  marketType: string,
  predictedOutcome: string,
  { long = false }: { long?: boolean } = {},
): string {
  const market = (long ? MARKET_LONG : MARKET_NAMES)[marketType]
    ?? marketType.replace(/_/g, ' ').toUpperCase()

  let outcome = (predictedOutcome || '').trim()
  // Strip a leading repetition of the market name ("Btts yes" -> "yes").
  const bare = outcome.replace(/^(btts|over\/under|double chance|match result)\s*/i, '')
  outcome = (bare || outcome).trim()

  return `${market} — ${outcome.toUpperCase()}`
}

/** Bookmaker names in normal public casing: "bet365" -> "Bet365". */
export function formatBookmaker(name: string | null | undefined): string | null {
  if (!name) return null
  return name
    .split(/\s+/)
    .map((w) => (w.length <= 3 && w === w.toUpperCase()
      ? w
      : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ')
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

/** "30 JUL 2026 · 14:20 UTC" */
export function formatUtc(iso: string | null | undefined): string {
  if (!iso) return 'n/a'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const day = String(d.getUTCDate()).padStart(2, '0')
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  return `${day} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()} · ${hh}:${mm} UTC`
}

/** Model score, labelled as a score — never as a calibrated probability. */
export function formatModelScore(pct: number | null | undefined): string {
  if (pct === null || pct === undefined || Number.isNaN(pct)) return 'n/a'
  // "62.4 / 100", never "62.4%". A percent sign presents the frozen ranking as
  // a calibrated probability — the exact reading every other surface retired.
  // Display-only: the stored claim value and its hash are untouched, and the
  // one decimal place preserves the immutable value's precision.
  return `${pct.toFixed(1)} / 100`
}

/**
 * Lead time BEFORE KICKOFF, measured from PUBLICATION.
 *
 * The public claim's proof is when we PUBLISHED it, not when the model happened
 * to generate the prediction — presenting generation time as the immutable
 * proof timestamp would overstate our foresight.
 */
export function beforeKickoffFromPublication(
  publishedAtIso: string,
  kickoffIso: string,
): string | null {
  const deltaMs = new Date(kickoffIso).getTime() - new Date(publishedAtIso).getTime()
  if (!Number.isFinite(deltaMs) || deltaMs <= 0) return null
  const mins = Math.floor(deltaMs / 60000)
  const totalHours = Math.floor(mins / 60)
  if (totalHours >= 48) {
    const d = Math.floor(totalHours / 24)
    const h = totalHours % 24
    return `${d}D ${h}H BEFORE KICKOFF`
  }
  const m = mins % 60
  return totalHours > 0
    ? `${totalHours}H ${m}M BEFORE KICKOFF`
    : `${m}M BEFORE KICKOFF`
}
