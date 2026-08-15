/**
 * THE single source of truth for every coverage number BetGlitch displays.
 *
 * Public copy used to hardcode "27 leagues" on /about and in two blog posts
 * while /explore rendered `LEAGUES.length - 1` = 30 competitions. Both numbers
 * were live at the same time, on pages one click apart.
 *
 * Neither was a typo. They count different things, and the honest fix is to
 * name what each one measures rather than pick a winner:
 *
 *   SEARCHABLE_COMPETITIONS — what the fixture search and the /explore filter
 *     can return. Includes the three UEFA club tournaments.
 *
 *   SIGNAL_COMPETITIONS — what the signal pipeline actually sweeps for ranked
 *     outcomes. The UEFA tournaments are NOT in this set, so a fixture can be
 *     searchable without ever producing a signal.
 *
 * Provider league names are not unique (there are many "Premier League" and
 * "Superliga" competitions). Public names and countries therefore live here,
 * keyed by the immutable SportMonks league id.
 */

/** Competitions the fixture search and the /explore filter can return. */
export const SEARCHABLE_COMPETITIONS = [
  { id: '2', name: 'UEFA Champions League', country: 'Europe' },
  { id: '5', name: 'UEFA Europa League', country: 'Europe' },
  { id: '2286', name: 'UEFA Europa Conference League', country: 'Europe' },
  { id: '8', name: 'English Premier League', country: 'England' },
  { id: '9', name: 'EFL Championship', country: 'England' },
  { id: '24', name: 'FA Cup', country: 'England' },
  { id: '27', name: 'EFL Cup', country: 'England' },
  { id: '72', name: 'Eredivisie', country: 'Netherlands' },
  { id: '82', name: 'Bundesliga', country: 'Germany' },
  { id: '181', name: 'Austrian Bundesliga', country: 'Austria' },
  { id: '208', name: 'Belgian Pro League', country: 'Belgium' },
  { id: '244', name: 'Croatian HNL', country: 'Croatia' },
  { id: '271', name: 'Danish Superliga', country: 'Denmark' },
  { id: '301', name: 'Ligue 1', country: 'France' },
  { id: '384', name: 'Serie A', country: 'Italy' },
  { id: '387', name: 'Serie B', country: 'Italy' },
  { id: '390', name: 'Coppa Italia', country: 'Italy' },
  { id: '444', name: 'Eliteserien', country: 'Norway' },
  { id: '453', name: 'Ekstraklasa', country: 'Poland' },
  { id: '462', name: 'Liga Portugal', country: 'Portugal' },
  { id: '474', name: 'Romanian SuperLiga', country: 'Romania' },
  { id: '501', name: 'Scottish Premiership', country: 'Scotland' },
  { id: '564', name: 'La Liga', country: 'Spain' },
  { id: '567', name: 'La Liga 2', country: 'Spain' },
  { id: '570', name: 'Copa del Rey', country: 'Spain' },
  { id: '573', name: 'Allsvenskan', country: 'Sweden' },
  { id: '591', name: 'Swiss Super League', country: 'Switzerland' },
  { id: '600', name: 'Süper Lig', country: 'Türkiye' },
  { id: '609', name: 'Ukrainian Premier League', country: 'Ukraine' },
  { id: '1371', name: 'UEFA Europa League Play-offs', country: 'Europe' },
] as const

export type SearchableCompetition = (typeof SEARCHABLE_COMPETITIONS)[number]

const COMPETITION_BY_ID = new Map(
  SEARCHABLE_COMPETITIONS.map((competition) => [Number(competition.id), competition]),
)

const COUNTRY_NAMES_RO: Record<string, string> = {
  Austria: 'Austria',
  Belgium: 'Belgia',
  Croatia: 'Croația',
  Denmark: 'Danemarca',
  England: 'Anglia',
  Europe: 'Europa',
  France: 'Franța',
  Germany: 'Germania',
  Italy: 'Italia',
  Netherlands: 'Țările de Jos',
  Norway: 'Norvegia',
  Poland: 'Polonia',
  Portugal: 'Portugalia',
  Romania: 'România',
  Russia: 'Rusia',
  Scotland: 'Scoția',
  Spain: 'Spania',
  Sweden: 'Suedia',
  Switzerland: 'Elveția',
  Türkiye: 'Turcia',
  Ukraine: 'Ucraina',
}

export function competitionById(id: number | null | undefined) {
  return id == null ? undefined : COMPETITION_BY_ID.get(id)
}

export function publicCompetitionLabel(
  id: number | null | undefined,
  providerFallback = 'Unknown competition',
  language: 'en' | 'ro' = 'en',
): string {
  const competition = competitionById(id)
  if (!competition) return providerFallback
  const country = language === 'ro'
    ? COUNTRY_NAMES_RO[competition.country] || competition.country
    : competition.country
  return `${competition.name} — ${country}`
}

export function competitionOptionLabel(
  competition: { name: string; country: string },
  language: 'en' | 'ro',
): string {
  if (!competition.country) return language === 'ro' ? 'Toate competițiile' : 'All competitions'
  const country = language === 'ro'
    ? COUNTRY_NAMES_RO[competition.country] || competition.country
    : competition.country
  return `${competition.name} — ${country}`
}

/**
 * Competition ids the signal pipeline sweeps. Mirrors `keyLeagues` in
 * app/api/recommendations/route.ts — asserted equal by coverage.test.ts.
 */
export const SIGNAL_COMPETITION_IDS = [
  8, 9, 24, 27, 72, 82, 181, 208, 244, 271, 301, 384, 387, 390, 444, 453, 462,
  474, 501, 564, 567, 570, 573, 591, 600, 609, 1371,
] as const

/** The exact named objects consumed by the signal engine. */
export const SIGNAL_COMPETITIONS = SIGNAL_COMPETITION_IDS.map((id) => {
  const competition = competitionById(id)
  if (!competition) throw new Error(`Missing competition metadata for SportMonks league ${id}`)
  return { id, name: competition.name, country: competition.country }
})

/**
 * Selected in BetGlitch's SportMonks Growth subscription on 2026-08-13 as a
 * no-cost replacement for Russian Premier League #486. Real odds and
 * prediction payloads still need the production activation check.
 */
export const ROMANIAN_SUPERLIGA = {
  id: 474,
  name: 'Romanian SuperLiga',
  providerName: 'Liga 1',
  country: 'Romania',
  configured: true,
  providerEntitlementVerified: true,
  providerPayloadsVerified: true,
} as const

/** How many competitions a visitor can search. Currently 30. */
export const SEARCHABLE_COMPETITION_COUNT = SEARCHABLE_COMPETITIONS.length

/** How many competitions can produce a live signal. Currently 27. */
export const SIGNAL_COMPETITION_COUNT = SIGNAL_COMPETITION_IDS.length

/** How far ahead fixtures are indexed. */
export const COVERAGE_HORIZON_DAYS = 14

/**
 * Markets BetGlitch ranks outcomes in. Matches the evidence pipeline's market
 * set — see core/services/market_outcomes.py.
 */
export const SUPPORTED_MARKETS = [
  '1X2', 'Both teams to score', 'Over/Under 2.5', 'Double chance',
] as const

export const SUPPORTED_MARKET_COUNT = SUPPORTED_MARKETS.length

/** The /explore filter's options, with its leading "all" entry. */
export const EXPLORE_LEAGUE_OPTIONS = [
  { id: '', name: 'All competitions', country: '', label: 'All competitions' },
  ...SEARCHABLE_COMPETITIONS.map((competition) => ({
    ...competition,
    label: `${competition.name} — ${competition.country}`,
  })),
]
