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

import { beforeKickoffLabel, type ProofPayload } from './proofData'

export const size = { width: 1200, height: 630 }

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
      display: 'flex', alignItems: 'center', padding: '8px 20px', borderRadius: 999,
      background: bg, color: '#fff', fontSize: 30,
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ display: 'flex', fontSize: 30, color: MUTED }}>
          Building our verified record
        </div>
        <div style={{ display: 'flex', fontSize: 24, color: MUTED }}>
          —— we post our losses too ——
        </div>
      </div>
    )
  }
  const roi = record.roi_percent
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', fontSize: 34, color: TEXT }}>
        Verified: {record.wins}W – {record.losses}L · {roi >= 0 ? '+' : ''}{roi}% ROI
      </div>
      <div style={{ display: 'flex', fontSize: 24, color: MUTED }}>
        —— we post our losses too ——
      </div>
    </div>
  )
}

function Shell({ children, badge }: { children: React.ReactNode; badge: string }) {
  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      background: NAVY, padding: 56, fontFamily: 'Inter',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Brand />
        <div style={{ display: 'flex', fontSize: 22, color: MUTED, letterSpacing: 1 }}>{badge}</div>
      </div>
      <div style={{
        display: 'flex', flexDirection: 'column', flex: 1, marginTop: 36, padding: 40,
        borderRadius: 24, background: CARD, border: '1px solid #1E2A44',
        justifyContent: 'space-between',
      }}>{children}</div>
      <div style={{ display: 'flex', marginTop: 22, fontSize: 24, color: MUTED }}>
        betglitch.com/track-record
      </div>
    </div>
  )
}

function priceLine(p: ProofPayload['pick']) {
  const odds = p.odds ? `@ ${p.odds}` : '@ n/a'
  return p.bookmaker ? `${odds} (${p.bookmaker})` : odds
}

function PickCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  const before = beforeKickoffLabel(p.prediction_logged_at, p.kickoff)
  const loggedUtc =
    new Date(p.prediction_logged_at).toISOString().slice(0, 16).replace('T', ' ') + ' UTC'
  return (
    <Shell badge="PUBLISHED BEFORE KICKOFF">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', fontSize: 26, color: MUTED }}>
          {p.league} · {p.home_team} vs {p.away_team}
        </div>
        <div style={{ display: 'flex', fontSize: 52, color: TEXT }}>
          {p.predicted_outcome.toUpperCase()} {priceLine(p)}
        </div>
        <div style={{ display: 'flex', fontSize: 26, color: MUTED }}>
          Model score {Math.round(p.model_score_percent)}%
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Pill text="LOGGED" bg={BLUE} />
          <div style={{ display: 'flex', fontSize: 28, color: TEXT }}>{loggedUtc}</div>
        </div>
        {before ? <div style={{ display: 'flex', fontSize: 26, color: GREEN }}>{before}</div> : null}
        <div style={{ display: 'flex', fontSize: 24, color: MUTED }}>
          The result will be shown here after settlement — win or lose
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
  const scoreLine = (r.actual_score_home != null && r.actual_score_away != null)
    ? `${p.home_team} ${r.actual_score_home} – ${r.actual_score_away} ${p.away_team}  (FT)`
    : `${p.home_team} vs ${p.away_team}  (FT)`
  return (
    <Shell badge="THIRD-PARTY SETTLED">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', fontSize: 40, color: TEXT }}>{scoreLine}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', fontSize: 32, color: MUTED }}>
            Our pick: {p.predicted_outcome.toUpperCase()} {priceLine(p)}
          </div>
          <Pill text={won ? 'WON' : 'LOST'} bg={won ? GREEN : RED} />
        </div>
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

function VoidCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  const cancelled = data.result.status === 'CANCELLED'
  return (
    <Shell badge="THIRD-PARTY SETTLED">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', fontSize: 40, color: TEXT }}>
          {p.home_team} vs {p.away_team}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', fontSize: 32, color: MUTED }}>
            Our pick: {p.predicted_outcome.toUpperCase()} {priceLine(p)}
          </div>
          <Pill text={cancelled ? 'CANCELLED' : 'VOID'} bg={GREY} />
        </div>
        <div style={{ display: 'flex', fontSize: 24, color: MUTED }}>
          No result — excluded from our record entirely
        </div>
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

/** Render the correct card for a claim's settlement state. */
export async function renderProofImage(data: ProofPayload | null) {
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
  return new ImageResponse(card, fontOpt)
}
