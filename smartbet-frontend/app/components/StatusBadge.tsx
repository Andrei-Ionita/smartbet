/**
 * The one visual language for "what kind of object am I looking at?".
 *
 * The core honesty problem this solves: a mutable live signal and an
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

/**
 * Romanian wording for the badge vocabulary.
 *
 * The badge is rendered by server components on the proof and track-record
 * pages, which have no language context, so English stays the default and a
 * caller that knows the visitor's language opts in with `lang`. Explore does —
 * a Romanian visitor was being read an English sentence describing the very
 * object the page had just introduced in Romanian.
 */
const RO: Record<SignalStatus, { label: string; hint: string }> = {
  live: {
    label: 'SEMNAL LIVE',
    hint: 'Semnal live — se poate modifica înainte de start și nu face parte din istoricul verificat.',
  },
  published_pending: {
    label: 'ANGAJAMENT — ÎN AȘTEPTARE',
    hint: 'Angajament public — înghețat înainte de start, în așteptarea încheierii. Nu este inclus în performanța verificată.',
  },
  won: {
    label: 'REZULTAT — CÂȘTIGAT',
    hint: 'Angajament public încheiat — câștigat.',
  },
  lost: {
    label: 'REZULTAT — PIERDUT',
    hint: 'Angajament public încheiat — pierdut.',
  },
  void: {
    label: 'ANULAT',
    hint: 'Anulat — exclus din totalurile istoricului verificat.',
  },
  cancelled: {
    label: 'CONTRAMANDAT',
    hint: 'Contramandat — exclus din totalurile istoricului verificat.',
  },
  legacy: {
    label: 'ISTORIC — NU E ÎN ISTORICUL VERIFICAT',
    hint: 'Înregistrat înainte de pragul de integritate a prețurilor. Păstrat, dar exclus din performanța publică.',
  },
}

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
    hint: 'Live signal — can change before kickoff and is not part of the verified record.',
  },
  published_pending: {
    label: 'COMMITMENT — PENDING',
    Icon: Lock,
    className: 'border-solid border-indigo-500 bg-indigo-50 text-indigo-900',
    hint: 'Public commitment — frozen before kickoff, awaiting settlement. Not included in verified performance.',
  },
  won: {
    label: 'RESULT — WON',
    Icon: CheckCircle2,
    className: 'border-solid border-emerald-600 bg-emerald-600 text-white',
    hint: 'Settled public commitment — won.',
  },
  lost: {
    label: 'RESULT — LOST',
    Icon: XCircle,
    // Same weight as WON. Losses are not hidden or softened.
    className: 'border-solid border-rose-600 bg-rose-600 text-white',
    hint: 'Settled public commitment — lost.',
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
  lang,
}: {
  status: SignalStatus
  size?: 'sm' | 'md'
  className?: string
  /** Omit for English. Server-rendered proof surfaces have no language context. */
  lang?: string
}) {
  const base = SPECS[status] ?? SPECS.live
  const translated = lang === 'ro' ? RO[status] ?? RO.live : null
  const spec = translated ? { ...base, ...translated } : base
  const { Icon } = base
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
/** The outline rule, in both languages. Split around the two emphasised
 *  words so the sentence stays grammatical in each. */
const LEGEND_NOTE = {
  en: { a: 'A ', dashed: 'dashed', b: ' outline means the value can still change. A ', solid: 'solid', c: ' outline means it was frozen before kickoff and cannot change again.' },
  ro: { a: 'Un contur ', dashed: 'punctat', b: ' înseamnă că valoarea se mai poate schimba. Un contur ', solid: 'continuu', c: ' înseamnă că a fost înghețată înainte de start și nu se mai poate schimba.' },
} as const

export function StatusLegend({
  className = '',
  lang,
}: {
  className?: string
  /** Omit for English, matching StatusBadge. */
  lang?: string
}) {
  const order: SignalStatus[] = [
    'live', 'published_pending', 'won', 'lost', 'void', 'cancelled', 'legacy',
  ]
  const note = lang === 'ro' ? LEGEND_NOTE.ro : LEGEND_NOTE.en
  return (
    <div className={className}>
      <ul className="flex flex-wrap gap-2">
        {order.map((s) => (
          <li key={s}>
            <StatusBadge status={s} size="sm" lang={lang} />
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-gray-600">
        {note.a}<strong>{note.dashed}</strong>{note.b}<strong>{note.solid}</strong>{note.c}
      </p>
    </div>
  )
}

export default StatusBadge
