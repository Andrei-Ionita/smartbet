import Link from 'next/link'
import EmailCapture from './EmailCapture'

interface ProofCapturePanelProps {
  source: string
  title?: string
  description?: string
  leagueInterest?: string
}

export default function ProofCapturePanel({
  source,
  title = 'Want the best picks before kickoff?',
  description = 'Join the free list for weekly high-conviction picks, verified track-record updates, and bankroll guidance.',
  leagueInterest = '',
}: ProofCapturePanelProps) {
  return (
    <div className="rounded-3xl border border-blue-200 bg-gradient-to-br from-blue-50 via-white to-emerald-50 p-6 shadow-sm">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl">
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Proof-led funnel</p>
          <h3 className="text-2xl font-bold text-gray-900">{title}</h3>
          <p className="mt-3 text-sm leading-6 text-gray-600">{description}</p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/track-record" className="font-semibold text-blue-700 hover:text-blue-900">
              Review the public track record
            </Link>
            <Link href="/pricing" className="font-semibold text-emerald-700 hover:text-emerald-900">
              See the premium roadmap
            </Link>
          </div>
        </div>
        <div className="w-full max-w-md">
          <EmailCapture
            source={source}
            leagueInterest={leagueInterest}
            interests={['weekly_picks', 'track_record', 'premium_launch']}
            title="Get weekly Smart Picks"
            description="Free email brief with top picks, proof of performance, and launch updates."
          />
        </div>
      </div>
    </div>
  )
}
