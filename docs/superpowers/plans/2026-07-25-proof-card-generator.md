# Proof-Card Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a proof-card generator that turns any recommended BetGlitch pick/result into a branded 1200×630 PNG plus a shareable link that unfurls into the card on Telegram/Twitter/Discord — powering the founder's manual community-seeding growth motion.

**Architecture:** One lean Django endpoint (`GET /api/proof/<fixture_id>/`) returns the card payload (pick + result + cumulative record). A Next.js file-convention image route (`app/proof/[fixtureId]/opengraph-image.tsx`) renders the Pick or Result "Receipt" card as a PNG via native `next/og` `ImageResponse` (runtime `nodejs`, one bundled font, styled elements instead of emoji for Satori safety). A proof page embeds that PNG as the authoritative card, sets OpenGraph metadata for unfurl, and offers copy-link / download controls. A `ShareProofButton` on `/track-record` rows and prediction pages is the one-click "grab a card" entry point.

**Tech Stack:** Django REST (one function view), Next.js 14 App Router, `next/og` (native — NO new npm dependency), one bundled web font.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-07-25-proof-card-generator-design.md`.

- **No new npm dependency.** `next/og` `ImageResponse` is native to Next 14.
- **Image size:** exactly `1200×630`. **Image route runtime:** `nodejs` (not edge — it fetches an internal Django API).
- **Eligibility:** only `is_recommended=True` fixtures get a proof card. Unknown or non-recommended `fixture_id` → HTTP `404` with `{"found": false}`.
- **Cumulative record source:** `AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)` — the same source the dashboard uses, so card and site always agree. Use keys `wins`, `losses`, `roi_percent`.
- **`result` is always present** in the payload: `{"resolved": false}` when pending, full object when resolved. Never `null`.
- **Cards use styled elements, not emoji** (Satori has limited/unreliable emoji rendering): WON/LOST/VERIFIED render as colored pills; the brand mark is a styled bolt/badge, not `⚡`. No `🔒✅❌✓⚡` glyphs in the PNG.
- **Cards sell transparent data, not a profit promise.** Result cards MUST show the honest record with losses; the LOST card renders the record identically to the WON card.
- **No new DB model or migration.** Reuse `PredictionLog` + `AccuracyCalculator`.
- **Django tests** live in `core/tests.py` (existing pattern: a `_pred` helper creating `PredictionLog` rows — see `AccuracyCalculatorUnificationTests`).
- **No frontend unit-test framework exists.** Card layout is verified visually (Task 5), not via a new harness.
- **Env vars:** frontend server fetches Django at `process.env.NEXT_PUBLIC_API_URL` (= `https://api.betglitch.com`); client share links use `process.env.NEXT_PUBLIC_APP_URL` (= `https://www.betglitch.com`). Both fall back to localhost in dev.
- **Deploy:** frontend and backend both auto-deploy from `master` on Railway.

## File Structure

| File | Purpose | New? |
|---|---|---|
| `core/transparency_views.py` | Add `proof_card_data` view. | modify |
| `core/urls.py` | Add `api/proof/<int:fixture_id>/` route. | modify |
| `core/tests.py` | Add `ProofCardEndpointTests`. | modify |
| `smartbet-frontend/app/proof/[fixtureId]/opengraph-image.tsx` | Renders Pick/Result card PNG via ImageResponse. | create |
| `smartbet-frontend/app/proof/[fixtureId]/Inter-Regular.woff` | Bundled font for Satori. | create (binary) |
| `smartbet-frontend/app/proof/[fixtureId]/proofData.ts` | Shared fetch helper + TS types for the proof payload. | create |
| `smartbet-frontend/app/proof/[fixtureId]/page.tsx` | Proof page: embeds PNG, OG metadata, controls, 404 state. | create |
| `smartbet-frontend/app/components/ShareProofButton.tsx` | One-click copy-link + download-PNG button. | create |
| `smartbet-frontend/app/track-record/TrackRecordContent.tsx` | Add ShareProofButton per row. | modify |
| `smartbet-frontend/app/prediction/[...slug]/PredictionContent.tsx` | Add ShareProofButton. | modify |

---

## Task 1: Backend proof endpoint + tests

**Files:**
- Modify: `core/transparency_views.py` (add `proof_card_data`)
- Modify: `core/urls.py` (add route)
- Modify: `core/tests.py` (add `ProofCardEndpointTests`)

**Interfaces:**
- Consumes: `PredictionLog`, `AccuracyCalculator` (both already imported in `transparency_views.py`), `JsonResponse`.
- Produces: `GET /api/proof/<int:fixture_id>/` → JSON `{found, pick, result, record}` (shape in Global Constraints). Frontend Tasks 2 and 3 consume this.

- [ ] **Step 1: Write the failing tests**

Append to `core/tests.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Proof-card endpoint (2026-07-25): GET /api/proof/<fixture_id>/ returns the
# payload for a shareable proof card. Only recommended picks are eligible.
# ─────────────────────────────────────────────────────────────────────────────

class ProofCardEndpointTests(TestCase):
    """GET /api/proof/<fixture_id>/ payload shape + eligibility."""

    def _pred(self, fixture_id, *, is_recommended=True, resolved=None,
              confidence=0.64, odds=1.85):
        # resolved: None = pending, True = win, False = loss
        kickoff = timezone.now() + timedelta(hours=3)
        was_correct = None
        score_h = score_a = None
        actual_outcome = None
        if resolved is not None:
            was_correct = resolved
            score_h, score_a = (2, 1) if resolved else (0, 0)
            actual_outcome = 'Over 2.5' if resolved else 'Under 2.5'
        return PredictionLog.objects.create(
            fixture_id=fixture_id, home_team='Almeria', away_team='Malaga',
            league='La Liga 2', kickoff=kickoff, predicted_outcome='Over 2.5',
            market_type='over_under_2.5', confidence=confidence, odds=odds,
            probability_home=confidence, probability_draw=(1 - confidence) / 2,
            probability_away=(1 - confidence) / 2,
            actual_outcome=actual_outcome, actual_score_home=score_h,
            actual_score_away=score_a, was_correct=was_correct,
            is_recommended=is_recommended,
            profit_loss_10=(8.0 if resolved else -10.0) if resolved is not None else None,
        )

    def test_pending_pick_returns_unresolved(self):
        self._pred(800001, resolved=None)
        resp = self.client.get('/api/proof/800001/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['found'])
        self.assertEqual(data['result']['resolved'], False)
        self.assertNotIn('was_correct', data['result'])
        self.assertEqual(data['pick']['home_team'], 'Almeria')
        self.assertEqual(data['pick']['predicted_outcome'], 'Over 2.5')

    def test_resolved_win(self):
        self._pred(800002, resolved=True)
        data = self.client.get('/api/proof/800002/').json()
        self.assertTrue(data['result']['resolved'])
        self.assertEqual(data['result']['was_correct'], True)
        self.assertEqual(data['result']['actual_score_home'], 2)
        self.assertEqual(data['result']['actual_score_away'], 1)

    def test_resolved_loss(self):
        self._pred(800003, resolved=False)
        data = self.client.get('/api/proof/800003/').json()
        self.assertTrue(data['result']['resolved'])
        self.assertEqual(data['result']['was_correct'], False)

    def test_non_recommended_returns_404(self):
        self._pred(800004, is_recommended=False, resolved=True)
        resp = self.client.get('/api/proof/800004/')
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(resp.json()['found'])

    def test_unknown_fixture_returns_404(self):
        resp = self.client.get('/api/proof/999999/')
        self.assertEqual(resp.status_code, 404)

    def test_confidence_normalised_to_percent(self):
        # Stored 0-1; payload should expose 0-100 for display.
        self._pred(800005, resolved=None, confidence=0.64)
        data = self.client.get('/api/proof/800005/').json()
        self.assertAlmostEqual(data['pick']['confidence'], 64.0, places=1)

    def test_record_matches_roi_simulation(self):
        self._pred(800006, resolved=True)   # 1 recommended resolved win
        from core.services.accuracy_calculator import AccuracyCalculator
        roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
        data = self.client.get('/api/proof/800006/').json()
        self.assertEqual(data['record']['wins'], roi['wins'])
        self.assertEqual(data['record']['losses'], roi['losses'])
        self.assertEqual(data['record']['roi_percent'], roi['roi_percent'])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python manage.py test core.tests.ProofCardEndpointTests -v 2
```

Expected: FAIL — 404 for every route (URL not registered yet) / `AttributeError` — the endpoint doesn't exist.

- [ ] **Step 3: Implement the view**

Append to `core/transparency_views.py` (it already imports `JsonResponse`, `PredictionLog`, `AccuracyCalculator`):

```python
def proof_card_data(request, fixture_id):
    """
    GET /api/proof/<fixture_id>/ — payload for a shareable proof card.

    Only recommended picks are eligible: we publish proof for the picks we
    actually recommended, nothing else. Returns the pick, the result (always
    present; {'resolved': False} while pending), and the cumulative record from
    the same source the public dashboard uses so the card and the site agree.
    """
    try:
        pred = PredictionLog.objects.get(fixture_id=fixture_id, is_recommended=True)
    except PredictionLog.DoesNotExist:
        return JsonResponse({'found': False}, status=404)

    resolved = pred.was_correct is not None
    result = {'resolved': bool(resolved)}
    if resolved:
        result.update({
            'actual_score_home': pred.actual_score_home,
            'actual_score_away': pred.actual_score_away,
            'was_correct': pred.was_correct,
        })

    # Normalise confidence to a 0-100 percent for display (stored as 0-1 or 0-100).
    conf = pred.confidence or 0.0
    confidence_pct = round(conf * 100, 1) if conf <= 1 else round(conf, 1)

    roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)

    return JsonResponse({
        'found': True,
        'pick': {
            'home_team': pred.home_team,
            'away_team': pred.away_team,
            'league': pred.league,
            'market_type': pred.market_type,
            'predicted_outcome': pred.predicted_outcome,
            'odds': pred.odds,
            'confidence': confidence_pct,
            'kickoff': pred.kickoff.isoformat(),
            'prediction_logged_at': pred.prediction_logged_at.isoformat(),
        },
        'result': result,
        'record': {
            'wins': roi['wins'],
            'losses': roi['losses'],
            'roi_percent': roi['roi_percent'],
        },
    })
```

- [ ] **Step 4: Register the URL**

In `core/urls.py`, add alongside the other `api/transparency/` and `api/fixture/` routes:

```python
    path('api/proof/<int:fixture_id>/', transparency_views.proof_card_data, name='proof_card_data'),
```

(Confirm `transparency_views` is already imported at the top of `core/urls.py`; the existing `api/transparency/...` routes reference it, so it is.)

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python manage.py test core.tests.ProofCardEndpointTests -v 2
```

Expected: 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add core/transparency_views.py core/urls.py core/tests.py
git commit -m "feat(proof): backend GET /api/proof/<fixture_id>/ endpoint + tests"
```

---

## Task 2: Font asset + opengraph-image route (the PNG)

**Files:**
- Create: `smartbet-frontend/app/proof/[fixtureId]/proofData.ts`
- Create: `smartbet-frontend/app/proof/[fixtureId]/Inter-Regular.woff` (downloaded binary)
- Create: `smartbet-frontend/app/proof/[fixtureId]/opengraph-image.tsx`

**Interfaces:**
- Consumes: `GET /api/proof/<id>/` from Task 1.
- Produces:
  - `proofData.ts`: `type ProofPayload` and `async function fetchProof(fixtureId: string): Promise<ProofPayload | null>` (returns `null` on 404/error). Consumed by Tasks 2 and 3.
  - `opengraph-image.tsx`: a Next image route returning a 1200×630 PNG. Also implicitly wires `og:image` for the page in Task 3 (Next file convention).

- [ ] **Step 1: Create the shared fetch helper + types**

Create `smartbet-frontend/app/proof/[fixtureId]/proofData.ts`:

```typescript
export interface ProofPayload {
  found: boolean
  pick: {
    home_team: string
    away_team: string
    league: string
    market_type: string
    predicted_outcome: string
    odds: number | null
    confidence: number
    kickoff: string
    prediction_logged_at: string
  }
  result:
    | { resolved: false }
    | { resolved: true; actual_score_home: number | null; actual_score_away: number | null; was_correct: boolean }
  record: { wins: number; losses: number; roi_percent: number }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchProof(fixtureId: string): Promise<ProofPayload | null> {
  try {
    const res = await fetch(`${API_BASE}/api/proof/${fixtureId}/`, {
      // Revalidate hourly: a pending pick becomes a result after full-time.
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    const data = (await res.json()) as ProofPayload
    return data.found ? data : null
  } catch {
    return null
  }
}

// Humanised "3h 28m before kickoff"; returns null if logged at/after kickoff.
export function beforeKickoffLabel(loggedAtIso: string, kickoffIso: string): string | null {
  const deltaMs = new Date(kickoffIso).getTime() - new Date(loggedAtIso).getTime()
  if (deltaMs <= 0) return null
  const mins = Math.floor(deltaMs / 60000)
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h > 0 ? `${h}h ${m}m before kickoff` : `${m}m before kickoff`
}
```

- [ ] **Step 2: Download a Satori-compatible font into the route directory**

Satori (behind `ImageResponse`) needs an explicit font and supports `ttf`/`otf`/`woff` (not `woff2`). Download Inter Regular (woff) from jsDelivr's fontsource mirror:

```bash
cd smartbet-frontend/app/proof/[fixtureId]/
curl -L -o Inter-Regular.woff "https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.16/files/inter-latin-400-normal.woff"
# Verify it is a real font file (> 30KB), not an HTML error page:
ls -l Inter-Regular.woff
```

Expected: `Inter-Regular.woff` is a binary of roughly 100–300 KB. If it is under 30 KB or looks like HTML, the URL failed — try the fallback:

```bash
curl -L -o Inter-Regular.woff "https://cdn.jsdelivr.net/fontsource/fonts/inter@latest/latin-400-normal.woff"
ls -l Inter-Regular.woff
```

Do not proceed until a valid `> 30KB` font file exists.

- [ ] **Step 3: Implement the image route**

Create `smartbet-frontend/app/proof/[fixtureId]/opengraph-image.tsx`. The card uses **styled elements, not emoji** (Satori-safe), a single font, and size/color hierarchy instead of font-weight.

```tsx
import { ImageResponse } from 'next/og'
import { fetchProof, beforeKickoffLabel, type ProofPayload } from './proofData'

export const runtime = 'nodejs'
export const alt = 'BetGlitch verified proof card'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

const NAVY = '#0B1220'
const CARD = '#111A2E'
const BLUE = '#3B82F6'
const GREEN = '#22C55E'
const RED = '#EF4444'
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

function RecordFooter({ record }: { record: ProofPayload['record'] }) {
  const roi = record.roi_percent
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', fontSize: 34, color: TEXT }}>
        Season: {record.wins}W – {record.losses}L · {roi >= 0 ? '+' : ''}{roi}% ROI
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
        borderRadius: 24, background: CARD, border: `1px solid #1E2A44`,
        justifyContent: 'space-between',
      }}>{children}</div>
      <div style={{ display: 'flex', marginTop: 22, fontSize: 24, color: MUTED }}>
        betglitch.com/track-record
      </div>
    </div>
  )
}

function PickCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  const oddsLabel = p.odds ? `@ ${p.odds}` : '@ n/a'
  const before = beforeKickoffLabel(p.prediction_logged_at, p.kickoff)
  const loggedUtc = new Date(p.prediction_logged_at).toISOString().slice(0, 16).replace('T', ' ') + ' UTC'
  return (
    <Shell badge="VERIFIED ANALYTICS">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', fontSize: 26, color: MUTED }}>{p.league} · {p.home_team} vs {p.away_team}</div>
        <div style={{ display: 'flex', fontSize: 56, color: TEXT }}>
          {p.predicted_outcome.toUpperCase()} {oddsLabel} · {Math.round(p.confidence)}%
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Pill text="LOGGED" bg={BLUE} />
          <div style={{ display: 'flex', fontSize: 28, color: TEXT }}>{loggedUtc}</div>
        </div>
        {before ? <div style={{ display: 'flex', fontSize: 26, color: GREEN }}>{before}</div> : null}
        <div style={{ display: 'flex', fontSize: 24, color: MUTED }}>Result auto-verifies after full-time</div>
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

function ResultCard({ data }: { data: ProofPayload }) {
  const p = data.pick
  const r = data.result as Extract<ProofPayload['result'], { resolved: true }>
  const oddsLabel = p.odds ? `@ ${p.odds}` : '@ n/a'
  const scoreLine = (r.actual_score_home != null && r.actual_score_away != null)
    ? `${p.home_team} ${r.actual_score_home} – ${r.actual_score_away} ${p.away_team}  (FT)`
    : `${p.home_team} vs ${p.away_team}  (FT)`
  return (
    <Shell badge="SPORTMONKS-VERIFIED">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', fontSize: 40, color: TEXT }}>{scoreLine}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', fontSize: 32, color: MUTED }}>
            Our pick: {p.predicted_outcome.toUpperCase()} {oddsLabel}
          </div>
          <Pill text={r.was_correct ? 'WON' : 'LOST'} bg={r.was_correct ? GREEN : RED} />
        </div>
      </div>
      <RecordFooter record={data.record} />
    </Shell>
  )
}

export default async function Image({ params }: { params: { fixtureId: string } }) {
  const data = await fetchProof(params.fixtureId)
  const fontData = await fetch(new URL('./Inter-Regular.woff', import.meta.url)).then((r) => r.arrayBuffer())
  const fontOpt = { fonts: [{ name: 'Inter', data: fontData, weight: 400 as const, style: 'normal' as const }], ...size }

  if (!data) {
    return new ImageResponse(
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: NAVY, color: MUTED, fontSize: 40, fontFamily: 'Inter' }}>
        Proof not found
      </div>, fontOpt)
  }
  const card = data.result.resolved ? <ResultCard data={data} /> : <PickCard data={data} />
  return new ImageResponse(card, fontOpt)
}
```

- [ ] **Step 4: Typecheck**

```bash
cd smartbet-frontend && npx tsc --noEmit
```

Expected: no output (clean). If `next/og` types complain, ensure `next` is 14+ (it is).

- [ ] **Step 5: Smoke-test the PNG locally against production data**

Start the dev server and request the image for a real recommended fixture id (pull one live):

```bash
# From repo root, get a real recommended, resolved fixture id:
curl -sk "https://api.betglitch.com/api/transparency/recent/?limit=1" | python -c "import json,sys; d=json.load(sys.stdin); print((d.get('predictions') or d.get('results') or d)[0].get('fixture_id'))"
```

Then in `smartbet-frontend`, `npm run dev`, and:

```bash
curl -s -o /tmp/card.png -w "%{content_type} %{size_download}\n" "http://localhost:3000/proof/<FIXTURE_ID>/opengraph-image"
```

Expected: `image/png` and a size > 10000 bytes. If it returns HTML or 0 bytes, the font load or fetch failed — inspect `npm run dev` console.

- [ ] **Step 6: Commit**

```bash
git add smartbet-frontend/app/proof/[fixtureId]/proofData.ts \
        smartbet-frontend/app/proof/[fixtureId]/Inter-Regular.woff \
        smartbet-frontend/app/proof/[fixtureId]/opengraph-image.tsx
git commit -m "feat(proof): opengraph-image route renders Pick/Result card PNG"
```

---

## Task 3: Proof page (embed PNG, OG metadata, controls, 404)

**Files:**
- Create: `smartbet-frontend/app/proof/[fixtureId]/page.tsx`

**Interfaces:**
- Consumes: `fetchProof` from `proofData.ts`; the `opengraph-image` route (embedded as `<img>`).
- Produces: the public page `betglitch.com/proof/<fixtureId>`. Next auto-wires `og:image` from the sibling `opengraph-image.tsx`; `generateMetadata` sets title/description + Twitter card type.

- [ ] **Step 1: Implement the page**

Create `smartbet-frontend/app/proof/[fixtureId]/page.tsx`:

```tsx
import Link from 'next/link'
import type { Metadata } from 'next'
import { fetchProof } from './proofData'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

export async function generateMetadata(
  { params }: { params: { fixtureId: string } }
): Promise<Metadata> {
  const data = await fetchProof(params.fixtureId)
  if (!data) {
    return { title: 'Proof not found · BetGlitch' }
  }
  const p = data.pick
  const outcome = p.predicted_outcome.toUpperCase()
  const title = data.result.resolved
    ? `${p.home_team} vs ${p.away_team} — ${outcome} · verified result`
    : `${p.home_team} vs ${p.away_team} — ${outcome} · logged before kickoff`
  const description = `Every pick timestamped before kickoff, every result verified. Season ${data.record.wins}W–${data.record.losses}L · ${data.record.roi_percent >= 0 ? '+' : ''}${data.record.roi_percent}% ROI. We post our losses too.`
  // Next auto-adds og:image from opengraph-image.tsx; we set the rest.
  return {
    title,
    description,
    openGraph: { title, description, type: 'website', url: `${APP_URL}/proof/${params.fixtureId}` },
    twitter: { card: 'summary_large_image', title, description },
  }
}

export default async function ProofPage({ params }: { params: { fixtureId: string } }) {
  const data = await fetchProof(params.fixtureId)
  const imageUrl = `${APP_URL}/proof/${params.fixtureId}/opengraph-image`
  const shareUrl = `${APP_URL}/proof/${params.fixtureId}`

  if (!data) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900">Proof not found</h1>
        <p className="mt-3 text-gray-600">This pick isn’t in our published, recommended track record.</p>
        <Link href="/track-record" className="mt-6 inline-block font-semibold text-blue-700 hover:text-blue-900">
          Review the full public track record →
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <img
        src={imageUrl}
        alt="BetGlitch verified proof card"
        width={1200}
        height={630}
        className="w-full rounded-2xl border border-gray-200 shadow-sm"
      />
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <a
          href={imageUrl}
          download={`betglitch-proof-${params.fixtureId}.png`}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Download PNG
        </a>
        <Link href="/track-record" className="text-sm font-semibold text-blue-700 hover:text-blue-900">
          See full track record →
        </Link>
      </div>
      <p className="mt-6 text-xs text-gray-500 break-all">Share link: {shareUrl}</p>
    </div>
  )
}
```

- [ ] **Step 2: Typecheck**

```bash
cd smartbet-frontend && npx tsc --noEmit
```

Expected: clean.

- [ ] **Step 3: Smoke-test the page + OG tags locally**

With `npm run dev` running:

```bash
curl -s "http://localhost:3000/proof/<FIXTURE_ID>" | grep -oE '<meta property="og:[^>]+>' | head
```

Expected: `og:title`, `og:description`, and an auto-injected `og:image` pointing at the `opengraph-image` route. Also confirm the page renders `200` and a known bad id renders the "Proof not found" state (`curl .../proof/999999`).

- [ ] **Step 4: Commit**

```bash
git add smartbet-frontend/app/proof/[fixtureId]/page.tsx
git commit -m "feat(proof): shareable proof page with OG unfurl + download"
```

---

## Task 4: ShareProofButton + placements

**Files:**
- Create: `smartbet-frontend/app/components/ShareProofButton.tsx`
- Modify: `smartbet-frontend/app/track-record/TrackRecordContent.tsx`
- Modify: `smartbet-frontend/app/prediction/[...slug]/PredictionContent.tsx`

**Interfaces:**
- Consumes: `NEXT_PUBLIC_APP_URL`; a `fixtureId` prop.
- Produces: `<ShareProofButton fixtureId={...} />` — client component: copies the proof link, shows a transient "Copied", and links to the PNG.

- [ ] **Step 1: Implement the button**

Create `smartbet-frontend/app/components/ShareProofButton.tsx`:

```tsx
'use client'

import { useState } from 'react'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

export default function ShareProofButton({
  fixtureId,
  className = '',
}: {
  fixtureId: number | string
  className?: string
}) {
  const [copied, setCopied] = useState(false)
  const shareUrl = `${APP_URL}/proof/${fixtureId}`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // Clipboard blocked (e.g. non-secure context) — open the proof page instead.
      window.open(shareUrl, '_blank')
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      title="Copy a shareable proof card link"
      className={`inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 ${className}`}
    >
      {copied ? '✓ Copied' : 'Share proof'}
    </button>
  )
}
```

- [ ] **Step 2: Add the button to each track-record row**

In `smartbet-frontend/app/track-record/TrackRecordContent.tsx`: import the component and render `<ShareProofButton fixtureId={row.fixture_id} />` in each results-table row. First locate the row-rendering map and the field name for the fixture id:

```bash
grep -n "fixture_id\|\.map(\|<tr" smartbet-frontend/app/track-record/TrackRecordContent.tsx | head
```

Add the import near the other component imports:

```tsx
import ShareProofButton from '../components/ShareProofButton'
```

Then, inside the per-row JSX (the last `<td>` of each row, so it reads as an action column), add:

```tsx
<td className="px-3 py-2 text-right">
  <ShareProofButton fixtureId={row.fixture_id} />
</td>
```

If the table has a header row, add a matching empty/`Share` `<th>` so columns align. Use the actual row variable name and fixture-id field discovered by the grep (adjust `row.fixture_id` accordingly).

- [ ] **Step 3: Add the button to the prediction detail page**

In `smartbet-frontend/app/prediction/[...slug]/PredictionContent.tsx`, near the existing `ProofCapturePanel` usage (around line 132), import and render the button with the page's fixture id:

```bash
grep -n "fixture_id\|ProofCapturePanel\|prediction\." smartbet-frontend/app/prediction/[...slug]/PredictionContent.tsx | head
```

```tsx
import ShareProofButton from '../../components/ShareProofButton'
```

Render it in the header/action area of the prediction, using the correct fixture-id field discovered by grep:

```tsx
<ShareProofButton fixtureId={prediction.fixture_id} className="mt-2" />
```

- [ ] **Step 4: Typecheck**

```bash
cd smartbet-frontend && npx tsc --noEmit
```

Expected: clean. Fix any prop/field-name mismatches surfaced.

- [ ] **Step 5: Commit**

```bash
git add smartbet-frontend/app/components/ShareProofButton.tsx \
        smartbet-frontend/app/track-record/TrackRecordContent.tsx \
        smartbet-frontend/app/prediction/[...slug]/PredictionContent.tsx
git commit -m "feat(proof): ShareProofButton on track-record rows + prediction page"
```

---

## Task 5: Deploy + visual verification

**Files:** none (verification only).

- [ ] **Step 1: Push and let Railway deploy**

```bash
git push origin master
```

Wait ~3 minutes for backend + frontend to deploy.

- [ ] **Step 2: Verify the backend endpoint live**

```bash
curl -sk "https://api.betglitch.com/api/transparency/recent/?limit=3" | python -c "import json,sys; d=json.load(sys.stdin); rows=d.get('predictions') or d.get('results') or d; [print(r.get('fixture_id'), r.get('was_correct')) for r in rows]"
# pick one resolved id, then:
curl -sk "https://api.betglitch.com/api/proof/<RESOLVED_FIXTURE_ID>/" | python -m json.tool
```

Expected: valid `{found:true, pick, result:{resolved:true,...}, record}` JSON. Also confirm a non-existent id returns 404.

- [ ] **Step 3: Generate the three card variants as PNGs for visual review**

Find one resolved WIN, one resolved LOSS, and one pending fixture id from the recent endpoint (or from `/api/transparency/recent/`). Then:

```bash
mkdir -p /tmp/proofcards
curl -sk -o /tmp/proofcards/win.png  "https://www.betglitch.com/proof/<WIN_ID>/opengraph-image"
curl -sk -o /tmp/proofcards/loss.png "https://www.betglitch.com/proof/<LOSS_ID>/opengraph-image"
curl -sk -o /tmp/proofcards/pick.png "https://www.betglitch.com/proof/<PENDING_ID>/opengraph-image"
for f in /tmp/proofcards/*.png; do echo "$f: $(file -b "$f")"; done
```

Expected: each file reports `PNG image data, 1200 x 630`. **The controller/human then visually reviews the three PNGs** (Read the image files) and confirms:
- Brand mark, league/match, pick, and record all render (no clipped or missing text).
- The **LOST** card shows the honest record + "we post our losses too" exactly like the WON card.
- The pick card shows the "logged … before kickoff" line.
- No `tofu`/missing-glyph boxes (font loaded correctly).

- [ ] **Step 4: Validate the Telegram/Twitter unfurl**

Paste `https://www.betglitch.com/proof/<WIN_ID>` into:
- Telegram (any Saved Messages chat) — confirm the card image unfurls with title/description.
- The Twitter/X Card Validator or opengraph.xyz — confirm `summary_large_image` renders the card.

Expected: the branded card appears as the link preview. (Note: if a preview looks stale after a pick resolves, that's platform OG caching — acceptable for v1 per the spec.)

- [ ] **Step 5: Confirm the on-site entry point**

Open `https://www.betglitch.com/track-record`, confirm a **Share proof** button appears on rows, click it, confirm the link is copied (or the proof page opens), and that the copied link resolves to a working proof page.

**HUMAN CHECKPOINT** — this task's deliverable is the founder confirming the cards look trustworthy and shareable. Once confirmed, the manual community-seeding experiment can begin.

---

## Self-review (executed by author)

**Spec coverage.** Every spec section maps to a task:
- §3 Pick/Result card content → Task 2 (`PickCard`, `ResultCard`).
- §3.3 state selection (resolved → Result) → Task 1 (`result.resolved`) + Task 2 (`data.result.resolved ? ResultCard : PickCard`).
- §4.1 backend endpoint + payload shape + 404 + record source → Task 1.
- §4.2 proof page + opengraph-image + runtime nodejs + 1200×630 → Tasks 2, 3.
- §4.3 ShareProofButton + placements → Task 4.
- §5 YAGNI (no auto-post, no templates, no analytics, no model) → nothing in the plan adds these.
- §6 testing (backend unit tests + visual pass + edge cases) → Task 1 tests, Task 5 visual, edge cases (null odds `@ n/a`, logged-after-kickoff omit line) handled in Task 2 card code + `beforeKickoffLabel`.
- §8 risks (Satori font/emoji) → Task 2 bundles a font and uses styled pills, no emoji glyphs.

No gaps.

**Placeholder scan.** No TBD/TODO. `<FIXTURE_ID>` / `<WIN_ID>` etc. in Task 5 are runtime values the operator fills from the live endpoint (verification commands, not code) — acceptable. All code steps contain complete code.

**Type consistency.**
- `ProofPayload` (Task 2 `proofData.ts`) is the single shared type; `opengraph-image.tsx` and `page.tsx` both import it. Keys match the backend JSON in Task 1 exactly (`pick.predicted_outcome`, `pick.odds`, `pick.confidence`, `result.resolved`, `result.was_correct`, `record.wins/losses/roi_percent`).
- `fetchProof(fixtureId: string)` signature consistent across Tasks 2 and 3.
- `ShareProofButton` prop `fixtureId: number | string` accepts both the numeric row id and string route param.

All consistent.

---

## Human checkpoints

1. **After Task 1, Step 5** — 7 backend tests green before any frontend work.
2. **After Task 2, Step 5** — the PNG endpoint returns a real `image/png` > 10KB locally; if it returns HTML/0 bytes the font or fetch failed — fix before proceeding.
3. **After Task 5** — the founder visually confirms the three cards (especially the LOST card) look trustworthy and the Telegram unfurl works. This gates the start of community seeding.
