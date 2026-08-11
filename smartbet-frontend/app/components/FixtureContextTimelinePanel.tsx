'use client'

import { useState } from 'react'
import {
  Activity,
  CalendarClock,
  ChevronDown,
  ChevronUp,
  MapPin,
  ScanSearch,
  Shirt,
  Users,
} from 'lucide-react'

import type {
  FixtureContextTimeline,
  FixtureTimelineEvent,
} from '../lib/fixtureTimeline'


interface Props {
  timeline?: FixtureContextTimeline | null
  homeTeam: string
  awayTeam: string
  ro: boolean
}

const value = (input: unknown): string =>
  input === null || input === undefined || input === '' ? '—' : String(input)

const pct = (input: unknown): string => {
  const n = Number(input)
  return Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : '—'
}

const odds = (input: unknown): string => {
  const n = Number(input)
  return Number.isFinite(n) ? n.toFixed(2) : 'unavailable'
}

const pair = (input: unknown): [unknown, unknown] =>
  Array.isArray(input) ? [input[0], input[1]] : [null, null]

function eventText(event: FixtureTimelineEvent, ro: boolean): string {
  const data = event.data || {}
  const before = value(data.from)
  const after = value(data.to)
  const market = value(data.market)
  const outcome = value(data.outcome)

  switch (event.code) {
    case 'context_capture_started':
      return ro
        ? 'BetGlitch a început să arhiveze contextul disponibil pentru acest meci.'
        : 'BetGlitch began archiving the available context for this fixture.'
    case 'predictability_changed':
      return ro
        ? `Indicatorul de predictibilitate s-a schimbat: ${before} → ${after}.`
        : `The provider predictability flag changed: ${before} → ${after}.`
    case 'lineup_status_changed':
      return ro
        ? `Statutul echipelor de start s-a schimbat: ${before} → ${after}.`
        : `Lineup status changed: ${before} → ${after}.`
    case 'formation_changed': {
      const from = pair(data.from)
      const to = pair(data.to)
      return ro
        ? `Formațiile s-au schimbat: ${value(from[0])}/${value(from[1])} → ${value(to[0])}/${value(to[1])}.`
        : `Formations changed: ${value(from[0])}/${value(from[1])} → ${value(to[0])}/${value(to[1])}.`
    }
    case 'sidelined_count_changed': {
      const from = pair(data.from)
      const to = pair(data.to)
      return ro
        ? `Numărul absențelor s-a schimbat: ${value(from[0])}/${value(from[1])} → ${value(to[0])}/${value(to[1])}.`
        : `Unavailable-player counts changed: ${value(from[0])}/${value(from[1])} → ${value(to[0])}/${value(to[1])}.`
    }
    case 'form_changed':
      return ro ? 'Forma recentă furnizată a fost actualizată.' : 'The supplied recent-form record was updated.'
    case 'venue_changed':
      return ro ? `Locația s-a schimbat: ${before} → ${after}.` : `Venue changed: ${before} → ${after}.`
    case 'neutral_venue_changed':
      return ro
        ? `Indicatorul de teren neutru s-a schimbat: ${before} → ${after}.`
        : `Neutral-venue status changed: ${before} → ${after}.`
    case 'model_leader_changed':
      return ro
        ? `Liderul modelului pentru ${market} s-a schimbat: ${before} → ${after} (${pct(data.probability)}).`
        : `The provider-model leader for ${market} changed: ${before} → ${after} (${pct(data.probability)}).`
    case 'model_probability_changed':
      return ro
        ? `Perspectiva modelului pentru ${market} · ${outcome} s-a schimbat: ${pct(data.from)} → ${pct(data.to)}.`
        : `The provider view for ${market} · ${outcome} moved: ${pct(data.from)} → ${pct(data.to)}.`
    case 'verified_price_changed':
      return ro
        ? `Cota verificată pentru ${market} · ${outcome} s-a schimbat: ${odds(data.from)} → ${odds(data.to)}.`
        : `The verified price for ${market} · ${outcome} moved: ${odds(data.from)} → ${odds(data.to)}.`
    default:
      return ro ? 'A fost observată o modificare a contextului.' : 'A context change was observed.'
  }
}

const statusLabel = (status: string, ro: boolean): string => {
  if (status === 'confirmed') return ro ? 'Confirmate' : 'Confirmed'
  if (status === 'available_unconfirmed') return ro ? 'Disponibile, neconfirmate' : 'Available, unconfirmed'
  return ro ? 'Indisponibile' : 'Unavailable'
}

const categoryStyle: Record<string, string> = {
  price: 'bg-emerald-100 text-emerald-800',
  model: 'bg-blue-100 text-blue-800',
  lineup: 'bg-violet-100 text-violet-800',
  squad: 'bg-amber-100 text-amber-800',
  form: 'bg-cyan-100 text-cyan-800',
  context: 'bg-slate-200 text-slate-700',
  availability: 'bg-slate-200 text-slate-700',
}

export default function FixtureContextTimelinePanel({ timeline, homeTeam, awayTeam, ro }: Props) {
  const [expanded, setExpanded] = useState(false)
  const current = timeline?.current
  const events = timeline?.events ?? []
  const visibleEvents = expanded ? events : events.slice(0, 6)

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-7">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-700">
            {ro ? 'ISTORIC PRE-MECI' : 'PRE-MATCH HISTORY'}
          </p>
          <h3 className="mt-1 text-xl font-bold text-slate-950">
            {ro ? 'Ce s-a schimbat înainte de start?' : 'What changed before kickoff?'}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
            {ro
              ? 'Fiecare modificare provine dintr-o observație arhivată. Faptul că două valori s-au mișcat împreună nu dovedește că una a cauzat-o pe cealaltă.'
              : 'Every change comes from an archived observation. Two values moving together does not prove that one caused the other.'}
          </p>
        </div>
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-800">
          <CalendarClock className="h-3.5 w-3.5" />
          {timeline?.snapshot_count ?? 0} {ro ? 'capturi de context' : 'context snapshots'}
        </span>
      </div>

      {!current ? (
        <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-sm leading-relaxed text-slate-600">
          {ro
            ? 'Istoricul începe după ce procesul programat observă acest meci. Lipsa datelor este afișată ca atare; BetGlitch nu reconstruiește retrospectiv contextul.'
            : 'History begins after the scheduled evidence sweep observes this fixture. Missing data stays missing; BetGlitch does not reconstruct pre-match context retrospectively.'}
        </div>
      ) : (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ContextMetric
              icon={<Shirt className="h-4 w-4" />}
              label={ro ? 'Echipe de start' : 'Lineups'}
              value={statusLabel(current.lineup_status, ro)}
            />
            <ContextMetric
              icon={<Users className="h-4 w-4" />}
              label={ro ? 'Jucători indisponibili' : 'Unavailable players'}
              value={`${homeTeam} ${current.home_sidelined_count} · ${awayTeam} ${current.away_sidelined_count}`}
            />
            <ContextMetric
              icon={<Activity className="h-4 w-4" />}
              label={ro ? 'Formații' : 'Formations'}
              value={`${current.home_formation ?? '—'} · ${current.away_formation ?? '—'}`}
            />
            <ContextMetric
              icon={<MapPin className="h-4 w-4" />}
              label={ro ? 'Locație' : 'Venue'}
              value={current.venue?.name ?? (ro ? 'Nefurnizată' : 'Not supplied')}
            />
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <ContextMetric
              icon={<ScanSearch className="h-4 w-4" />}
              label={ro ? 'Predictibilitate furnizor' : 'Provider predictability'}
              value={current.fixture_predictable === true
                ? (ro ? 'Da' : 'Yes')
                : current.fixture_predictable === false ? (ro ? 'Nu' : 'No') : (ro ? 'Necunoscută' : 'Unknown')}
            />
            <ContextMetric
              icon={<Activity className="h-4 w-4" />}
              label={`${homeTeam} · ${ro ? 'formă' : 'form'}`}
              value={current.home_form ?? (ro ? 'Nefurnizată' : 'Not supplied')}
            />
            <ContextMetric
              icon={<Activity className="h-4 w-4" />}
              label={`${awayTeam} · ${ro ? 'formă' : 'form'}`}
              value={current.away_form ?? (ro ? 'Nefurnizată' : 'Not supplied')}
            />
          </div>

          <div className="mt-6 border-t border-slate-200 pt-5">
            <h4 className="font-bold text-slate-950">{ro ? 'Cronologia modificărilor' : 'Change timeline'}</h4>
            {visibleEvents.length > 0 ? (
              <ol className="mt-4 space-y-4">
                {visibleEvents.map((event, index) => (
                  <li key={`${event.observed_at}-${event.code}-${index}`} className="relative pl-7">
                    <span className="absolute left-0 top-1.5 h-3 w-3 rounded-full border-2 border-white bg-violet-500 ring-2 ring-violet-100" />
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${categoryStyle[event.category] ?? categoryStyle.context}`}>
                        {event.category}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(event.observed_at).toLocaleString(ro ? 'ro-RO' : 'en-GB')} · {Math.max(0, event.hours_to_kickoff).toFixed(1)}h {ro ? 'înainte de start' : 'before kickoff'}
                      </span>
                    </div>
                    <p className="mt-1 text-sm leading-relaxed text-slate-700">{eventText(event, ro)}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-sm text-slate-600">
                {ro ? 'Nu a fost observată încă nicio modificare.' : 'No change has been observed yet.'}
              </p>
            )}
            {events.length > 6 && (
              <button
                type="button"
                onClick={() => setExpanded((open) => !open)}
                className="mt-4 inline-flex min-h-[40px] items-center gap-1.5 text-sm font-semibold text-violet-700 hover:text-violet-900"
              >
                {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                {expanded
                  ? (ro ? 'Arată mai puțin' : 'Show less')
                  : ro ? `Arată toate (${events.length})` : `Show all (${events.length})`}
              </button>
            )}
          </div>
        </>
      )}

      <p className="mt-5 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
        {ro
          ? 'Doar informațiile observate înainte de start sunt publicate aici. „Disponibil” nu înseamnă „confirmat”, iar absența unei valori nu este completată prin presupuneri.'
          : 'Only information observed before kickoff appears here. “Available” does not mean “confirmed”, and missing values are never filled by assumption.'}
      </p>
    </section>
  )
}

function ContextMetric({ icon, label, value: metricValue }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">{icon}{label}</div>
      <p className="mt-1 text-sm font-bold leading-snug text-slate-950">{metricValue}</p>
    </div>
  )
}
