import { CheckCircle2, CircleDashed, Clock3, FlaskConical, ShieldCheck } from 'lucide-react'
import type { EvidenceStatus, PublicStrategyEvidence } from '../lib/useStrategyEvidence'

const STATUS_STYLE: Record<EvidenceStatus, string> = {
  not_started: 'border-gray-200 bg-gray-50 text-gray-700',
  insufficient_evidence: 'border-amber-200 bg-amber-50 text-amber-900',
  collecting_evidence: 'border-blue-200 bg-blue-50 text-blue-900',
  review_ready: 'border-violet-200 bg-violet-50 text-violet-900',
  validated: 'border-emerald-200 bg-emerald-50 text-emerald-900',
}

const STATUS_ICON = {
  not_started: CircleDashed,
  insufficient_evidence: Clock3,
  collecting_evidence: FlaskConical,
  review_ready: ShieldCheck,
  validated: CheckCircle2,
}

const LABELS = {
  en: {
    not_started: 'Test not started',
    insufficient_evidence: 'Insufficient evidence',
    collecting_evidence: 'Collecting evidence',
    review_ready: 'Ready for review',
    validated: 'Validated evidence',
    unavailable: 'Evidence status unavailable',
    loading: 'Checking evidence',
    decisions: 'forward-settled decisions',
  },
  ro: {
    not_started: 'Testul nu a început',
    insufficient_evidence: 'Dovezi insuficiente',
    collecting_evidence: 'Colectăm dovezi',
    review_ready: 'Pregătită pentru evaluare',
    validated: 'Dovezi validate',
    unavailable: 'Statut indisponibil',
    loading: 'Verificăm dovezile',
    decisions: 'decizii forward încheiate',
  },
}

export default function StrategyEvidenceBadge({
  evidence,
  language,
  loading = false,
  available = true,
  showProgress = false,
}: {
  evidence?: PublicStrategyEvidence
  language: 'en' | 'ro'
  loading?: boolean
  available?: boolean
  showProgress?: boolean
}) {
  const labels = LABELS[language]
  if (loading) {
    return <span className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-500"><CircleDashed className="h-3.5 w-3.5 animate-spin" />{labels.loading}</span>
  }
  if (!available || !evidence) {
    return <span className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-500"><CircleDashed className="h-3.5 w-3.5" />{labels.unavailable}</span>
  }

  const Icon = STATUS_ICON[evidence.evidence_status]
  return (
    <div>
      <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold ${STATUS_STYLE[evidence.evidence_status]}`}>
        <Icon className="h-3.5 w-3.5" />
        {labels[evidence.evidence_status]}
      </span>
      {showProgress && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{evidence.forward_settled} / {evidence.minimum_forward_settled_for_review} {labels.decisions}</span>
            <span>{evidence.evidence_progress_percent}%</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-gray-100">
            <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${evidence.evidence_progress_percent}%` }} />
          </div>
        </div>
      )}
    </div>
  )
}
