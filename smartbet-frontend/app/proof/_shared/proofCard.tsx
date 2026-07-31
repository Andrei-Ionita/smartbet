/**
 * Proof-card rendering, shared by the claim route and the fixture route.
 *
 * Cards render ONLY frozen claim fields. Four visual states — PICK/PENDING,
 * RESULT/WON, RESULT/LOST, VOID-CANCELLED — with wins and losses given
 * identical prominence and quality.
 */
import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { ImageResponse } from 'next/og'

import { type ProofPayload } from './proofData'
import {
  beforeKickoffFromPublication, formatBookmaker, formatModelScore,
  formatOdds, formatSelection, formatUtc,
} from './format'

export const size = { width: 1200, height: 630 }

/**
 * Bump whenever the card's visual contract changes. Emitted as the
 * `x-betglitch-card` response header so any served image can be traced to the
 * code that produced it — a cached older artifact is then provable, not
 * guesswork.
 *
 * v2: PUBLISHED (not LOGGED) as the primary timestamp, lead time measured from
 *     publication, formatted odds/market/bookmaker, single transparency line.
 */
export const CARD_VERSION = 'v2-published-ts'

const NAVY = '#0B1220'
const CARD = '#111A2E'
const BLUE = '#3B82F6'
const GREEN = '#22C55E'
const RED = '#EF4444'
const GREY = '#64748B'
const MUTED = '#8CA0BD'
const TEXT = '#F1F5F9'

function Brand() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: 40, height: 40, borderRadius: 10, background: BLUE, color: '#fff',
        fontSize: 26,
      }}>{'/'}</div>
      <div style={{ fontSize: 30, letterSpacing: 2, color: TEXT }}>BETGLITCH</div>
    </div>
  )
}

function Pill({ text, bg }: { text: string; bg: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', padding: '6px 18px', borderRadius: 999,
      background: bg, color: '#fff', fontSize: 26,
    }}>{text}</div>
  )
}

/**
 * Cumulative record. At zero verified results this must NOT print "0W – 0L ·
 * +0% ROI" — a zero sample rendered as a figure reads as break-even
 * performance. The verified record restarts at the pricing-integrity cutoff.
 */
function RecordFooter({ record }: { record: ProofPayload['record'] }) {
  if (!record || record.total_bets === 0) {
    return (
      <div style={{ display: 'flex', fontSize: 21, color: MUTED }}>
        Building our verified record from pick #1
      </div>
    )
  }
  const roi = record.roi_percent
  return (
    <div style={{ display: 'flex', fontSize: 24, color: TEXT }}>
      Verified: {record.wins}W – {record.losses}L · {roi >= 0 ? '+' : ''}{roi}% ROI
    </div>
  )
}

function Shell({ children, badge }: { children: React.ReactNode; badge: string }) {
  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      background: NAVY, padding: 44, fontFamily: 'Inter',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Brand />
        <div style={{ display: 'flex', fontSize: 22, color: MUTED, letterSpacing: 1 }}>{badge}</div>
      </div>
      <div style={{
        display: 'flex', flexDirection: 'column', flex: 1, marginTop: 22, padding: 32,
        borderRadius: 24, background: CARD, border: '1px solid #1E2A44',
        justifyContent: 'space-between',
      }}>{children}</div>
      <div style={{ display: 'flex', marginTop: 16, fontSize: 20, color: MUTED }}>
        betglitch.com/track-record
      </div>
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div style={{ display: 'flex', fontSize: 17, color: MUTED, letterSpacing: 1 }}>
        {label}
      </div>
      <div style={{ display: 'flex', fontSize: 26, color: TEXT }}>{value}</div>
    </div>
  )
}

function priceLine(p: ProofPayload['pick']) {
  const book = formatBookmaker(p.bookmaker)
  return book
    ? `${formatOdds(p.odds)} · ${book.toUpperCase()}`
    : formatOdds(p.odds)
}

function Fixture({ p }: { p: ProofPayload['pick'] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', fontSize: 21, color: MUTED }}>{p.league}</div>
      <div style={{ display: 'flex', fontSize: 29, color: TEXT }}>
        {p.home_team} vs {p.away_team}
      </div>
    </div>
  )
}

function PickCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  // The public proof timestamp is PUBLICATION, not model generation.
  const before = beforeKickoffFromPublication(p.published_at, p.kickoff)
  return (
    <Shell badge="PICK — PENDING · PUBLISHED BEFORE KICKOFF">
      <Fixture p={p} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', fontSize: 46, color: TEXT }}>
          {formatSelection(p.market_type, p.predicted_outcome)}
        </div>
        <Meta label="RECORDED ODDS" value={priceLine(p)} />
        <Meta label="MODEL SCORE" value={formatModelScore(p.model_score_percent)} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Pill text="PUBLISHED" bg={BLUE} />
          <div style={{ display: 'flex', fontSize: 24, color: TEXT }}>
            {formatUtc(p.published_at)}
          </div>
        </div>
        {before ? (
          <div style={{ display: 'flex', fontSize: 22, color: GREEN }}>{before}</div>
        ) : null}
        <div style={{ display: 'flex', fontSize: 20, color: MUTED }}>
          Result added automatically after full-time — win or lose.
        </div>
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

function ResultCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  const r = data.result
  const won = r.status === 'WON'
  const score = (r.actual_score_home != null && r.actual_score_away != null)
    ? `${r.actual_score_home} – ${r.actual_score_away}`
    : '—'
  return (
    <Shell badge={`RESULT — ${r.status} · SETTLED BY THIRD-PARTY DATA`}>
      <Fixture p={p} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ display: 'flex', fontSize: 46, color: TEXT }}>
            {p.home_team.split(' ')[0]} {score} {p.away_team.split(' ')[0]}
          </div>
          <Pill text={won ? 'WON' : 'LOST'} bg={won ? GREEN : RED} />
        </div>
        <div style={{ display: 'flex', fontSize: 25, color: MUTED }}>
          Our pick: {formatSelection(p.market_type, p.predicted_outcome)}
        </div>
        <Meta label="RECORDED ODDS" value={priceLine(p)} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', fontSize: 22, color: MUTED }}>
          PUBLISHED {formatUtc(p.published_at)}
        </div>
        {r.settled_at ? (
          <div style={{ display: 'flex', fontSize: 22, color: MUTED }}>
            SETTLED {formatUtc(r.settled_at)}
          </div>
        ) : null}
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

function VoidCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  const cancelled = data.result.status === 'CANCELLED'
  return (
    <Shell badge={`${data.result.status} · SETTLED BY THIRD-PARTY DATA`}>
      <Fixture p={p} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ display: 'flex', fontSize: 38, color: TEXT }}>
            {formatSelection(p.market_type, p.predicted_outcome)}
          </div>
          <Pill text={cancelled ? 'CANCELLED' : 'VOID'} bg={GREY} />
        </div>
        <Meta label="RECORDED ODDS" value={priceLine(p)} />
        <div style={{ display: 'flex', fontSize: 24, color: MUTED }}>
          No result — excluded from our record entirely
        </div>
      </div>
      <div style={{ display: 'flex', fontSize: 22, color: MUTED }}>
        PUBLISHED {formatUtc(p.published_at)}
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

/** Render the correct card for a claim's settlement state. */
export async function renderProofImage(
  data: ProofPayload | null,
  opts: { previewNotice?: string } = {},
) {
  // Node.js runtime (not edge) has filesystem access; `fetch(new URL(...,
  // import.meta.url))` only resolves reliably under the edge runtime, so read
  // the bundled font from disk instead.
  const fontBuffer = await readFile(join(process.cwd(), 'public/fonts/Inter-Regular.woff'))
  const fontData = fontBuffer.buffer.slice(
    fontBuffer.byteOffset, fontBuffer.byteOffset + fontBuffer.byteLength,
  )
  const fontOpt = {
    fonts: [{ name: 'Inter', data: fontData, weight: 400 as const, style: 'normal' as const }],
    ...size,
    headers: { 'x-betglitch-card': CARD_VERSION },
  }

  if (!data) {
    return new ImageResponse(
      <div style={{
        width: '100%', height: '100%', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: NAVY, color: MUTED, fontSize: 40,
        fontFamily: 'Inter',
      }}>
        Not published as a BetGlitch claim
      </div>, fontOpt)
  }

  const status = data.result?.status ?? 'PENDING'
  const card = status === 'WON' || status === 'LOST'
    ? <ResultCard data={data} />
    : status === 'VOID' || status === 'CANCELLED'
      ? <VoidCard data={data} />
      : <PickCard data={data} />

  if (!opts.previewNotice) return new ImageResponse(card, fontOpt)

  // Staff preview: the notice must be impossible to mistake for a real card.
  return new ImageResponse(
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#B45309', color: '#fff', fontSize: 22, padding: '8px 0',
        fontFamily: 'Inter', letterSpacing: 1,
      }}>{opts.previewNotice}</div>
      <div style={{ display: 'flex', flex: 1 }}>{card}</div>
    </div>,
    fontOpt,
  )
}
