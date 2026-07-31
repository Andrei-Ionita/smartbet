import type { Metadata } from 'next'

/**
 * STAFF VISUAL PREVIEW page. noindex, never linked publicly, and it renders no
 * canonical proof URL — it exists only to inspect card layouts before a real
 * fixture settles.
 */
export const metadata: Metadata = {
  title: 'Card visual preview · BetGlitch (staff)',
  robots: { index: false, follow: false, nocache: true },
}

const STATES = ['pending', 'won', 'lost', 'void', 'cancelled']

export default function PreviewPage(
  { params }: { params: { claimId: string; state: string } },
) {
  const state = params.state?.toLowerCase()
  const imageUrl = `/proof/preview/${params.claimId}/${state}/opengraph-image`

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="rounded-lg border-2 border-amber-500 bg-amber-50 px-4 py-3">
        <p className="text-sm font-bold uppercase tracking-wide text-amber-900">
          Visual preview — not a real settlement
        </p>
        <p className="mt-1 text-sm text-amber-900">
          Synthetic result data over a real immutable claim. Nothing here creates
          or modifies a settlement record, and no public statistic is affected.
        </p>
      </div>

      <h1 className="mt-6 text-xl font-bold text-gray-900">
        {state?.toUpperCase()} — 1200×630
      </h1>

      <img
        src={imageUrl}
        alt={`BetGlitch ${state} card preview`}
        width={1200}
        height={630}
        className="mt-4 w-full rounded-2xl border border-gray-200 shadow-sm"
      />

      <div className="mt-6 flex flex-wrap gap-3 text-sm">
        {STATES.map((s) => (
          <a
            key={s}
            href={`/proof/preview/${params.claimId}/${s}`}
            className={`rounded-lg border px-3 py-1.5 font-semibold ${
              s === state
                ? 'border-blue-600 bg-blue-600 text-white'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {s.toUpperCase()}
          </a>
        ))}
      </div>

      <p className="mt-6 text-xs text-gray-500">
        Direct image: <span className="break-all font-mono">{imageUrl}</span>
      </p>
    </div>
  )
}
