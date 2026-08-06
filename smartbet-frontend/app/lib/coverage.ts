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
 * Nothing here changes pipeline behaviour: SIGNAL_COMPETITION_IDS mirrors the
 * list inside app/api/recommendations/route.ts, and a test asserts the two stay
 * identical so this file cannot drift into a lie.
 */

/** Competitions the fixture search and the /explore filter can return. */
export const SEARCHABLE_COMPETITIONS = [
  { id: '2', name: 'UEFA Champions League' },
  { id: '5', name: 'UEFA Europa League' },
  { id: '2286', name: 'UEFA Europa Conference League' },
  { id: '8', name: 'Premier League' },
  { id: '9', name: 'Championship' },
  { id: '24', name: 'FA Cup' },
  { id: '27', name: 'Carabao Cup' },
  { id: '72', name: 'Eredivisie' },
  { id: '82', name: 'Bundesliga' },
  { id: '181', name: 'Admiral Bundesliga' },
  { id: '208', name: 'Pro League' },
  { id: '244', name: '1. HNL' },
  { id: '271', name: 'Superliga' },
  { id: '301', name: 'Ligue 1' },
  { id: '384', name: 'Serie A' },
  { id: '387', name: 'Serie B' },
  { id: '390', name: 'Coppa Italia' },
  { id: '444', name: 'Eliteserien' },
  { id: '453', name: 'Ekstraklasa' },
  { id: '462', name: 'Liga Portugal' },
  { id: '486', name: 'Russian Premier League' },
  { id: '501', name: 'Premiership' },
  { id: '564', name: 'La Liga' },
  { id: '567', name: 'La Liga 2' },
  { id: '570', name: 'Copa Del Rey' },
  { id: '573', name: 'Allsvenskan' },
  { id: '591', name: 'Super League' },
  { id: '600', name: 'Super Lig' },
  { id: '609', name: 'Premier League (Additional)' },
  { id: '1371', name: 'UEFA Europa League Play-offs' },
] as const

/**
 * Competition ids the signal pipeline sweeps. Mirrors `keyLeagues` in
 * app/api/recommendations/route.ts — asserted equal by coverage.test.ts.
 */
export const SIGNAL_COMPETITION_IDS = [
  8, 9, 24, 27, 72, 82, 181, 208, 244, 271, 301, 384, 387, 390, 444, 453, 462,
  486, 501, 564, 567, 570, 573, 591, 600, 609, 1371,
] as const

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
  { id: '', name: 'All Leagues' },
  ...SEARCHABLE_COMPETITIONS,
]
