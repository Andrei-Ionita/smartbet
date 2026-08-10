'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import FixtureDecisionWorkspace, {
  type FixtureDecisionFixture,
} from '../../components/FixtureDecisionWorkspace'
import ProofCapturePanel from '../../components/ProofCapturePanel'

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

      <div className="mt-8">
        <ProofCapturePanel
          source="prediction_page"
          leagueInterest={fixture.league}
          title="Follow published picks and results by email."
          description="Occasional updates from the public record: new commitments, settled results, and methodology changes — wins and losses alike."
        />
      </div>

      <p className="mx-auto my-10 max-w-3xl text-center text-xs leading-relaxed text-slate-400">
        Provider probabilities and market-implied probabilities are separate reference views. BetGlitch does not accept bets, and this workspace is not betting advice.
      </p>
    </div>
  )
}
