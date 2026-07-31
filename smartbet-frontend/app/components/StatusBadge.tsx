/**
 * The one visual language for "what kind of object am I looking at?".
 *
 * The core honesty problem this solves: a mutable live model signal and an
 * immutable published claim used to look identical on screen. They are not the
 * same object and must never read as equivalent.
 *
 * The encoding is structural, not decorative:
 *
 *   DASHED border  = mutable. This can still change before kickoff.
 *   SOLID border   = frozen. This can never change again.
 *   FILLED         = settled. The result is in.
 *
 * Status is carried by the label text and the icon as well as the colour, so it
 * survives greyscale, colour-blindness and forced-colours mode.
 *
 * Wins and losses use identical weight, size and prominence. A losing result is
 * not visually demoted — that is the entire point of the public record.
 */
import React from 'react'
import {
  Activity, Ban, CheckCircle2, Lock, MinusCircle, XCircle, Archive,
} from 'lucide-react'

import type { SignalStatus } from '../lib/signalStatus'

export { statusFromClaim } from '../lib/signalStatus'
export type { SignalStatus }

type Spec = {
  label: string
  Icon: React.ComponentType<{ className?: string }>
  /** Tailwind classes. Border style is the semantic part — see file header. */
  className: string
  /** Screen-reader expansion of what the badge means. */
  hint: string
}

const SPECS: Record<SignalStatus, Spec> = {
  live: {
    label: 'LIVE SIGNAL',
    Icon: Activity,
    // Dashed = mutable. Deliberately the only dashed badge in the product.
    className: 'border-dashed border-sky-400 bg-sky-50 text-sky-800',
    hint: 'Live model signal — can change before kickoff and is not part of the verified record.',
  },
  published_pending: {
    label: 'PUBLISHED — PENDING',
    Icon: Lock,
    className: 'border-solid border-indigo-500 bg-indigo-50 text-indigo-900',
    hint: 'Published pick — frozen before kickoff, awaiting the result.',
  },
  won: {
    label: 'RESULT — WON',
    Icon: CheckCircle2,
    className: 'border-solid border-emerald-600 bg-emerald-600 text-white',
    hint: 'Settled published pick — won.',
  },
  lost: {
    label: 'RESULT — LOST',
    Icon: XCircle,
    // Same weight as WON. Losses are not hidden or softened.
    className: 'border-solid border-rose-600 bg-rose-600 text-white',
    hint: 'Settled published pick — lost.',
  },
  void: {
    label: 'VOID',
    Icon: MinusCircle,
    className: 'border-solid border-slate-400 bg-slate-100 text-slate-700',
    hint: 'Void — excluded from the verified record totals.',
  },
  cancelled: {
    label: 'CANCELLED',
    Icon: Ban,
    className: 'border-solid border-slate-400 bg-slate-100 text-slate-700',
    hint: 'Cancelled — excluded from the verified record totals.',
  },
  legacy: {
    label: 'LEGACY — NOT IN VERIFIED RECORD',
    Icon: Archive,
    className: 'border-solid border-amber-400 bg-amber-50 text-amber-900',
    hint: 'Recorded before the pricing-integrity cutoff. Preserved, but excluded from public performance.',
  },
}

export function StatusBadge({
  status,
  size = 'md',
  className = '',
}: {
  status: SignalStatus
  size?: 'sm' | 'md'
  className?: string
}) {
  const spec = SPECS[status] ?? SPECS.live
  const { Icon } = spec
  const sizing =
    size === 'sm'
      ? 'text-[10px] px-2 py-0.5 gap-1'
      : 'text-xs px-2.5 py-1 gap-1.5'

  return (
    <span
      className={`inline-flex items-center rounded-md border-2 font-semibold uppercase tracking-wide leading-none ${spec.className} ${sizing} ${className}`}
      title={spec.hint}
    >
      <Icon className={size === 'sm' ? 'h-3 w-3 shrink-0' : 'h-3.5 w-3.5 shrink-0'} />
      <span>{spec.label}</span>
      <span className="sr-only"> — {spec.hint}</span>
    </span>
  )
}

/**
 * The legend. Shown once on the verified-record page so the vocabulary is
 * learnable in one place rather than inferred from context.
 */
export function StatusLegend({ className = '' }: { className?: string }) {
  const order: SignalStatus[] = [
    'live', 'published_pending', 'won', 'lost', 'void', 'cancelled', 'legacy',
  ]
  return (
    <div className={className}>
      <ul className="flex flex-wrap gap-2">
        {order.map((s) => (
          <li key={s}>
            <StatusBadge status={s} size="sm" />
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-gray-600">
        A <strong>dashed</strong> outline means the value can still change. A{' '}
        <strong>solid</strong> outline means it was frozen before kickoff and
        cannot change again.
      </p>
    </div>
  )
}

export default StatusBadge
