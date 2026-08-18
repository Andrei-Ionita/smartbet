'use client'

import { ArrowRight, CheckCircle2, Search, ShieldQuestion } from 'lucide-react'

import type { Lang } from '../lib/terminology'
import type { ModelShortlistItem } from '../../src/types/recommendation'

const WORDS = {
  en: {
    label: 'Model shortlist', leading: 'Leading signal', strength: 'Signal strength',
    price: 'Verified price', why: 'Why it stands out', notGem: 'Why it is not a Gem',
    disclaimer: 'Signal strength ranks the model outputs; it is not a calibrated win probability.',
    details: 'Investigate fixture', books: 'bookmakers',
    separation: 'points clear of the next outcome', checkedAcross: 'The displayed price was checked across',
    supportOne: 'One supporting market model agrees.', supportMany: 'supporting market models agree.',
    supportNone: 'No supporting market model explicitly contradicts the leading outcome.',
    gapReliability: 'A stricter Gem reliability check was not satisfied.',
    gapModelPrice: 'The complete model-versus-price test did not qualify.',
    gapSupport: 'Both supporting market models explicitly disagreed.',
    gapPrice: 'A stricter Gem price-quality check was not satisfied.',
    gapOther: 'It did not pass every Gem qualification gate.',
  },
  ro: {
    label: 'Lista modelului', leading: 'Semnal principal', strength: 'Forța semnalului',
    price: 'Cotă verificată', why: 'De ce iese în evidență', notGem: 'De ce nu este Gem',
    disclaimer: 'Forța semnalului ordonează rezultatele modelului; nu este o probabilitate calibrată de câștig.',
    details: 'Analizează meciul', books: 'case',
    separation: 'puncte peste următorul rezultat', checkedAcross: 'Cota afișată a fost verificată la',
    supportOne: 'Un model de piață suplimentar este aliniat.', supportMany: 'modele de piață suplimentare sunt aliniate.',
    supportNone: 'Niciun model de piață suplimentar nu contrazice explicit rezultatul principal.',
    gapReliability: 'O verificare mai strictă de fiabilitate Gem nu a fost îndeplinită.',
    gapModelPrice: 'Testul complet model–cotă nu s-a calificat.',
    gapSupport: 'Ambele modele de piață suplimentare au fost în dezacord.',
    gapPrice: 'O verificare mai strictă a calității cotei Gem nu a fost îndeplinită.',
    gapOther: 'Nu a trecut toate filtrele de calificare Gem.',
  },
} as const

function kickoffLabel(value: string, language: Lang) {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T') + 'Z'
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language === 'ro' ? 'ro-RO' : 'en-GB', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

export default function ModelShortlistCard({
  item,
  language,
  displayRank,
  onViewDetails,
}: {
  item: ModelShortlistItem
  language: Lang
  displayRank: number
  onViewDetails: (fixtureId: number) => void
}) {
  const w = WORDS[language]
  const shortlistReasons = [
    `${Math.round(item.signal_gap * 100)} ${w.separation}.`,
    `${w.checkedAcross} ${item.bookmakers_checked} ${w.books}.`,
    item.supporting_models === 0
      ? w.supportNone
      : item.supporting_models === 1
        ? w.supportOne
        : `${item.supporting_models} ${w.supportMany}`,
  ]
  const gapLabels: Record<string, string> = {
    reliability: w.gapReliability,
    model_price: w.gapModelPrice,
    support_models: w.gapSupport,
    price_quality: w.gapPrice,
    other: w.gapOther,
  }
  const gemGapReasons = item.gem_gap_categories.map(code => gapLabels[code] ?? w.gapOther)

  return (
    <article className="flex h-full flex-col rounded-2xl border border-blue-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-bold text-blue-800">
          <Search className="h-4 w-4" aria-hidden="true" />
          {w.label} #{displayRank}
        </div>
        <span className="text-xs text-gray-500">{kickoffLabel(item.kickoff, language)}</span>
      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {item.league}
      </p>
      <h3 className="mt-1 text-lg font-bold leading-snug text-gray-950">
        {item.home_team} <span className="font-normal text-gray-400">vs</span>{' '}
        {item.away_team}
      </h3>

      <dl className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <div className="rounded-xl bg-blue-50 p-3">
          <dt className="text-xs text-blue-700">{w.leading}</dt>
          <dd className="mt-1 font-bold text-blue-950">{item.leading_selection}</dd>
        </div>
        <div className="rounded-xl bg-gray-50 p-3">
          <dt className="text-xs text-gray-500">{w.strength}</dt>
          <dd className="mt-1 font-bold text-gray-950">
            {Math.round(item.signal_strength * 100)}/100
          </dd>
        </div>
        <div className="rounded-xl bg-gray-50 p-3">
          <dt className="text-xs text-gray-500">{w.price}</dt>
          <dd className="mt-1 font-bold text-gray-950">{item.verified_price.toFixed(2)}</dd>
          <dd className="text-xs text-gray-500">{item.bookmakers_checked} {w.books}</dd>
        </div>
      </dl>

      <div className="mt-4 flex-1">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-gray-700">
          <CheckCircle2 className="h-4 w-4 text-blue-600" /> {w.why}
        </p>
        <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-gray-600">
          {shortlistReasons.map(reason => <li key={reason}>• {reason}</li>)}
        </ul>

        <p className="mt-4 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-amber-800">
          <ShieldQuestion className="h-4 w-4" /> {w.notGem}
        </p>
        <p className="mt-2 text-xs leading-relaxed text-amber-900">
          {gemGapReasons.join(' ')}
        </p>
      </div>

      <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-600">
        {w.disclaimer}
      </p>
      <button
        type="button"
        onClick={() => onViewDetails(item.fixture_id)}
        className="mt-4 inline-flex min-h-[42px] items-center justify-center gap-2 rounded-xl border border-gray-300 px-4 text-sm font-semibold text-gray-800 hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
      >
        {w.details} <ArrowRight className="h-4 w-4" />
      </button>
    </article>
  )
}
