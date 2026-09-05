import useSWR from 'swr'

export interface PortfolioSelection {
  selection_id: string; receipt_url: string; fixture_id: number
  home_team: string; away_team: string; league: string; kickoff: string
  market_type: string; predicted_outcome: string; odds: number; bookmaker_count: number
  odds_captured_at: string; published_at: string; current_odds: number; current_price_at: string
  current_bookmaker_count?: number
  status: string; unit_profit: number | null; homepage?: boolean
  evidence: {
    model_probability: number | null; market_probability: number | null
    conservative_probability: number | null; model_ev: number; conservative_ev: number
    calibration_count: number; probability_method: string; evidence_label: string
    context: { lineups: string; observed_at: string | null; form_available: boolean; home_form?: string | null; away_form?: string | null; absences_available: boolean; absence_count: number | null }
  }
}
export interface PortfolioMarket {
  key: string; name: { en: string; ro: string }; strategy_url: string
  status: string; selections: PortfolioSelection[]; evaluated: number
}
export interface SelectionPortfolio {
  success: boolean; version: string; status: string; generated_at: string | null
  homepage: PortfolioSelection[]; markets: PortfolioMarket[]
  unavailable_markets: Record<string, string>
  scan: { fixtures_evaluated?: number; candidates_evaluated?: number; eligible_candidates?: number; published_on_board?: number; rejections?: Record<string, number> }
}
export const portfolioFetcher = async (url: string) => {
  const response = await fetch(url)
  if (!response.ok) throw new Error('Portfolio unavailable')
  return response.json()
}
export function useSelectionPortfolio() {
  return useSWR<SelectionPortfolio>('/api/selection-portfolio', portfolioFetcher, {
    refreshInterval: 120_000, errorRetryCount: 2, revalidateOnFocus: true,
  })
}
export function portfolioFixtureHref(item: Pick<PortfolioSelection, 'league' | 'home_team' | 'away_team' | 'kickoff' | 'fixture_id'>) {
  const slug = (text: string) => text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'fixture'
  return `/prediction/${slug(item.league)}/${slug(`${item.home_team}-vs-${item.away_team}`)}-${item.kickoff.slice(0, 10)}-${item.fixture_id}`
}
export function formatPercent(value: number | null | undefined, signed = false) {
  return value == null || !Number.isFinite(value) ? '—' : `${signed && value > 0 ? '+' : ''}${(value * 100).toFixed(1)}%`
}

export function marketName(key: string, language: 'en' | 'ro') {
  const labels: Record<string, [string, string]> = {
    '1x2': ['Match result', 'Rezultat final'], btts: ['Both teams to score', 'Ambele echipe marchează'],
    double_chance: ['Double chance', 'Șansă dublă'], correct_score: ['Correct score', 'Scor corect'],
    half_time_result: ['Half-time result', 'Rezultat la pauză'], half_time_full_time: ['Half-time / full-time', 'Pauză / final'],
    asian_handicap: ['Asian handicap', 'Handicap asiatic'], asian_goal_line: ['Asian goals', 'Total asiatic'],
    team_total_goals: ['Team goals', 'Golurile echipei'],
  }
  const line = key.match(/^over_under_(\d+\.\d+)$/)?.[1]
  return line ? `${language === 'ro' ? 'Goluri' : 'Goals'} ${line}` : labels[key]?.[language === 'ro' ? 1 : 0] ?? key.replace(/_/g, ' ')
}

export function selectionName(value: string, market: string, language: 'en' | 'ro') {
  const ro = language === 'ro'
  const normalized = value.toLowerCase().trim().replace(/_/g, ' ')
  const labels: Record<string, [string, string]> = {
    home: ['Home', 'Gazde'], draw: ['Draw', 'Egal'], away: ['Away', 'Oaspeți'],
    yes: ['Yes', 'Da'], no: ['No', 'Nu'], over: ['Over', 'Peste'], under: ['Under', 'Sub'],
  }
  const line = market.match(/^over_under_(\d+\.\d+)$/)?.[1]
  if (labels[normalized]) return labels[normalized][ro ? 1 : 0] + (line ? ` ${line}` : '')
  if (market === 'half_time_full_time') return normalized.split(' ').map(v => labels[v]?.[ro ? 1 : 0] ?? v).join(' / ')
  if (ro) return value.replace(/\bhome\b/gi, 'Gazde').replace(/\baway\b/gi, 'Oaspeți').replace(/\bover\b/gi, 'Peste').replace(/\bunder\b/gi, 'Sub')
  return value
}
