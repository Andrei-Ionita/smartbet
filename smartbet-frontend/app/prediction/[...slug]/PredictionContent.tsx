'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import FixtureDecisionWorkspace, {
  type FixtureDecisionFixture,
} from '../../components/FixtureDecisionWorkspace'
import ProofCapturePanel from '../../components/ProofCapturePanel'
import FixtureSelectionReceipts from '../../components/FixtureSelectionReceipts'
import { PUBLIC_RESULTS_VISIBLE } from '../../lib/publicResultsMode'

interface PredictionContentProps {
  fixture: FixtureDecisionFixture
  lastUpdated?: string | null
}

export default function PredictionContent({ fixture, lastUpdated }: PredictionContentProps) {
  return (
    <div className="mx-auto max-w-6xl">
      <nav className="mb-6 flex items-center gap-2 text-sm text-slate-500" aria-label="Breadcrumb">
        <Link href="/" className="inline-flex items-center gap-1 hover:text-blue-700">
          <ArrowLeft className="h-4 w-4" /> Home
        </Link>
        <span aria-hidden>/</span>
        <Link href="/explore" className="hover:text-blue-700">Explore</Link>
        <span aria-hidden>/</span>
        <span className="truncate font-medium text-slate-900">{fixture.home_team} vs {fixture.away_team}</span>
      </nav>

      <FixtureDecisionWorkspace fixture={fixture} lastUpdated={lastUpdated} />

      <FixtureSelectionReceipts fixtureId={fixture.fixture_id} />

      {PUBLIC_RESULTS_VISIBLE && <div className="mt-8">
        <ProofCapturePanel
          source="prediction_page"
          leagueInterest={fixture.league}
          title="Inspect the published evidence."
          description="See every current-strategy Gem BetGlitch published before kickoff and how it settled — wins and losses alike. No email or account is required."
        />
      </div>}

      <p className="mx-auto my-10 max-w-3xl text-center text-xs leading-relaxed text-slate-400">
        Model probabilities and market-implied probabilities are separate reference views. BetGlitch does not accept bets, and this workspace is not betting advice.
      </p>
    </div>
  )
}
