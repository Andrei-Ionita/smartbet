export type FixtureTimelineCategory =
  | 'availability'
  | 'context'
  | 'lineup'
  | 'squad'
  | 'form'
  | 'model'
  | 'price'

export interface FixtureTimelineEvent {
  code: string
  category: FixtureTimelineCategory
  observed_at: string
  hours_to_kickoff: number
  data: Record<string, unknown>
}

export interface FixtureContextCurrent {
  observed_at: string
  hours_to_kickoff: number
  fixture_predictable: boolean | null
  lineup_status: 'confirmed' | 'available_unconfirmed' | 'unavailable'
  home_formation: string | null
  away_formation: string | null
  home_form: string | null
  away_form: string | null
  home_sidelined_count: number
  away_sidelined_count: number
  venue: {
    id?: number | null
    name?: string | null
    city_name?: string | null
    capacity?: number | null
  } | null
  neutral_venue: boolean | null
  data_availability: Record<string, boolean>
}

export interface FixtureContextTimeline {
  fixture_id: number
  source: 'append_only_pre_match_observations'
  methodology_version: string
  snapshot_count: number
  signal_snapshot_count: number
  first_observed_at: string | null
  last_observed_at: string | null
  current: FixtureContextCurrent | null
  events: FixtureTimelineEvent[]
  limitations: string[]
}
