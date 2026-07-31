/**
 * Intentional empty states.
 *
 * Every empty screen here answers three questions, in this order:
 *   1. Why is this empty?
 *   2. Is that expected, or is something broken?
 *   3. What can I do next?
 *
 * An empty screen is an invitation to act, so each state carries an action.
 * Nothing here apologises and nothing is vague: expected states say so plainly,
 * and problem states say what failed.
 */
import React from 'react'
import Link from 'next/link'
import {
  Archive, CircleSlash, Hourglass, SearchX, ServerCrash, Tag, Trophy,
} from 'lucide-react'

type Tone = 'expected' | 'problem'

export type EmptyStateKey =
  | 'no_live_signals'
  | 'no_search_results'
  | 'no_pending_claims'
  | 'no_verified_results'
  | 'no_league_fixtures'
  | 'missing_odds'
  | 'provider_unavailable'
  | 'first_dashboard'

type Action = { label: string; href: string }

type Spec = {
  Icon: React.ComponentType<{ className?: string }>
  tone: Tone
  title: string
  body: string
  primary?: Action
  secondary?: Action
}

const SPECS: Record<EmptyStateKey, Spec> = {
  no_verified_results: {
    Icon: Trophy,
    tone: 'expected',
    title: 'The verified record is being built',
    body:
      'No published pick has settled yet. Once one does, its result appears here automatically—win or lose. BetGlitch restarted its public record under a stricter pricing and publication standard, so earlier predictions are excluded.',
    primary: { label: 'View published pending picks', href: '/track-record#pending' },
    secondary: { label: 'Explore live signals', href: '/explore' },
  },
  no_pending_claims: {
    Icon: Hourglass,
    tone: 'expected',
    title: 'No published picks are awaiting a result',
    body:
      'Nothing is currently frozen and waiting on a match. Published picks appear here between publication and full-time.',
    primary: { label: 'Explore live signals', href: '/explore' },
  },
  no_live_signals: {
    Icon: CircleSlash,
    tone: 'expected',
    title: 'No live signals match these filters',
    body:
      'The model has no output for this selection right now. Try another league, widen the date range or check back after the next model update.',
    primary: { label: 'Browse all fixtures', href: '/explore' },
  },
  no_search_results: {
    Icon: SearchX,
    tone: 'expected',
    title: 'No fixtures match that search',
    body:
      'Check the spelling, or search for a league or country instead of a team.',
    primary: { label: 'Clear filters and browse', href: '/explore' },
  },
  no_league_fixtures: {
    Icon: CircleSlash,
    tone: 'expected',
    title: 'No upcoming fixtures in this league',
    body:
      'This competition has nothing scheduled inside the 14-day window. That is normal between rounds and during off-seasons.',
    primary: { label: 'Choose another league', href: '/explore' },
  },
  missing_odds: {
    Icon: Tag,
    tone: 'expected',
    title: 'No verified price is available for this market',
    body:
      'The model signal is still shown, but BetGlitch will not publish a priced claim without complete market provenance—the exact bookmaker, market and capture time must all be recorded.',
  },
  provider_unavailable: {
    Icon: ServerCrash,
    tone: 'problem',
    title: 'Match data is temporarily unavailable',
    body:
      'The data provider did not respond. Nothing is wrong with your account and no signals were lost. Reload in a moment.',
    primary: { label: 'Back to home', href: '/' },
  },
  first_dashboard: {
    Icon: Archive,
    tone: 'expected',
    title: 'Your dashboard fills in as you use BetGlitch',
    body:
      'Set a bankroll to size stakes, and follow the verified record as published picks settle.',
    primary: { label: 'Explore live signals', href: '/explore' },
    secondary: { label: 'Set up bankroll', href: '/bankroll' },
  },
}

export function EmptyState({
  state,
  className = '',
  children,
}: {
  state: EmptyStateKey
  className?: string
  children?: React.ReactNode
}) {
  const spec = SPECS[state]
  const { Icon } = spec
  const problem = spec.tone === 'problem'

  return (
    <div
      role={problem ? 'alert' : undefined}
      className={`rounded-2xl border p-6 text-center sm:p-8 ${
        problem ? 'border-amber-300 bg-amber-50' : 'border-gray-200 bg-white'
      } ${className}`}
    >
      <div
        className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl ${
          problem ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'
        }`}
      >
        <Icon className="h-6 w-6" />
      </div>

      <h3 className="text-lg font-bold text-gray-900">{spec.title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-gray-600">
        {spec.body}
      </p>

      {children}

      {(spec.primary || spec.secondary) && (
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          {spec.primary && (
            <Link
              href={spec.primary.href}
              className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
            >
              {spec.primary.label}
            </Link>
          )}
          {spec.secondary && (
            <Link
              href={spec.secondary.href}
              className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
            >
              {spec.secondary.label}
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

export default EmptyState
