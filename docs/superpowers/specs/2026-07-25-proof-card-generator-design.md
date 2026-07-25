# Proof-Card Generator — Design Spec

**Date:** 2026-07-25
**Status:** Approved for planning
**Author:** Andrei + Claude
**Parent context:** First concrete build of the growth thread. The strategic
reframe (see §1) is: grow the *transparency / research-tool brand*, not the
*betting edge* (which is thin and unvalidated). The chosen growth motion is
**lean community validation** — the founder manually seeds transparent picks and
verified results into existing betting communities (Telegram, Reddit, Discord)
to test whether anyone cares. This spec covers the one thing we *build* to power
that motion: a **proof-card generator** that turns any pick or result into a
clean, branded, shareable image + link.

---

## 1. Purpose

Give the founder a one-click way to produce a **branded, screenshot-perfect
"proof card"** for any BetGlitch pick or result, as both a shareable link (that
unfurls into the card image on Telegram/Twitter/Discord) and a downloadable PNG.

The card's job is to make BetGlitch's one real differentiator — **radical
transparency** — visible and shareable in a betting-tips ecosystem saturated
with scam channels that delete losing picks and fake screenshots. The card is a
self-contained trust artifact:

- **Pick cards** prove *foresight* — the pick was timestamped and logged before
  kickoff (a locked-in, falsifiable claim).
- **Result cards** prove *honesty* — the outcome is third-party-verified and the
  honest cumulative record (wins **and losses**) is shown.

Success = the founder can grab a clean card in one click from `/track-record`,
it unfurls correctly in Telegram, and the loss card renders honestly. This
unblocks the manual community-seeding experiment (the founder's labor, not a
build).

**Explicit non-goal for the whole thread:** this does NOT claim or imply
guaranteed profit. Cards present *transparent data*, not a profit promise —
consistent with the legal/reputational posture that the edge is unproven.

## 2. Scope & context

### What we build
- Two card layouts (Pick, Result) in a shared "Receipt" aesthetic, rendered
  server-side as 1200×630 PNGs via Next.js native `next/og` `ImageResponse`
  (no new npm dependency).
- A shareable proof page per fixture that carries OpenGraph meta so links
  unfurl, and offers copy-link / download-PNG controls.
- One lean backend endpoint returning the exact card payload in a single call.
- "Share proof" affordances on `/track-record` rows and prediction detail pages.

### What already exists (reuse, do not rebuild)
- `PredictionLog` model has every field the card needs, including
  `prediction_logged_at` (commented in-code as *"PROOF: logged before match"*),
  `odds`, `confidence`, `actual_score_home/away`, `was_correct`, `market_type`.
- `/api/transparency/dashboard/` returns `stats.roi_simulation` = the cumulative
  record (`wins`, `losses`, `roi_percent`) — already unified onto the
  recommended-bets universe.
- `/api/fixture/<int:fixture_id>/` (`get_fixture_details`) exists; the new proof
  endpoint may reuse its query logic but returns a card-shaped payload.
- `ProofCapturePanel` is an email-capture CTA (misleadingly named) — unrelated;
  leave it alone.

### Tech stack
Next.js 14 App Router (frontend, `next/og` for image generation), Django REST
(backend, one new function view), existing Railway deploy pipeline.

## 3. The two cards (Receipt aesthetic)

Both cards are 1200×630, BetGlitch-branded (⚡ logo, brand colors), with a
`betglitch.com/track-record` footer URL. The throughline is the
receipt/verification aesthetic: every card looks auditable.

### 3.1 Pick card (pre-kickoff) — hero: the pre-kickoff timestamp
Content, in priority order:
1. Brand header: `⚡ BETGLITCH` + a small `verified analytics` tag.
2. Match line: `<league> · <home_team> vs <away_team>`.
3. The pick (prominent): `▸ <predicted_outcome> @ <odds>  ·  <confidence>% conf`.
   - `predicted_outcome` rendered human-readably (e.g. "OVER 2.5 GOALS").
   - If `odds` is null, render `@ n/a` rather than a broken value.
4. **Proof block (the hero):**
   - `🔒 Logged <prediction_logged_at, UTC>`
   - `— <delta> before kickoff` where delta = `kickoff − prediction_logged_at`,
     humanized (e.g. "3h 28m before kickoff"). If the pick was logged after
     kickoff (legacy/edge data), omit the "before kickoff" line rather than
     show a negative delta.
   - `⏳ Result auto-verifies after full-time`.
5. Cumulative record footer: `Season: <wins>W – <losses>L · <roi_percent:+.1f>% ROI`.

### 3.2 Result card (post-match) — hero: the verified badge + honest record
Content, in priority order:
1. Brand header: `⚡ BETGLITCH` + `✓ SportMonks-verified`.
2. Match result: `<home_team> <actual_score_home> – <actual_score_away> <away_team>  (FT)`.
3. Pick + outcome (prominent): `Our pick: <predicted_outcome> @ <odds>` and a
   bold `✅ WON` or `❌ LOST` derived from `was_correct`.
4. **Honest-record block (the hero):**
   - `Season: <wins>W – <losses>L · <roi_percent:+.1f>% ROI`
   - `── we post our losses too ──`
   - This block MUST render identically on a `❌ LOST` card — the differentiator
     is showing losses, so the loss card is the most important one to get right.
5. Footer URL.

### 3.3 State selection
`/proof/[fixtureId]` renders the **Result card** when the fixture is resolved
(`actual_outcome` present / `was_correct` non-null), otherwise the **Pick card**.
The `opengraph-image` route applies the same rule so the unfurl matches the page.

## 4. Architecture & routes

### 4.1 Backend — one new endpoint
`GET /api/proof/<int:fixture_id>/` → JSON:
```json
{
  "found": true,
  "pick": {
    "home_team": "...", "away_team": "...", "league": "...",
    "market_type": "over_under_2.5",
    "predicted_outcome": "Over 2.5", "odds": 1.85, "confidence": 64.0,
    "kickoff": "2026-06-20T18:00:00Z",
    "prediction_logged_at": "2026-06-20T14:32:00Z"
  },
  "result": {
    "resolved": true,
    "actual_score_home": 2, "actual_score_away": 1,
    "was_correct": true
  },
  "record": { "wins": 61, "losses": 41, "roi_percent": 9.6 }
}
```
- `result` is always present; it is `{"resolved": false}` when the fixture is
  pending (other result keys omitted) and the full object when resolved. Never
  `null` — keeps the frontend branch on a single boolean.
- `found: false` with HTTP 404 when the fixture_id is unknown.
- `record` is computed from `AccuracyCalculator().get_roi_simulation()` — the
  same source the dashboard uses, so the card and the site always agree.
- Only fixtures that are `is_recommended=True` are eligible for a proof card
  (we only publish proof for picks we actually recommended). Unknown or
  non-recommended fixture_ids → 404.

### 4.2 Frontend — proof page + image route
- **`app/proof/[fixtureId]/page.tsx`** — server component. Fetches
  `/api/proof/<id>/`. Renders the card visually (HTML/CSS mirror of the PNG),
  a "See full track record" CTA linking `/track-record`, and two controls:
  "Copy share link" and "Download PNG". Sets `generateMetadata` with OpenGraph
  + Twitter card tags pointing `og:image` at the `opengraph-image` route so the
  link unfurls. On 404, render a friendly "proof not found" state.
- **`app/proof/[fixtureId]/opengraph-image.tsx`** — Next file-convention route.
  `export const size = { width: 1200, height: 630 }`, `contentType =
  'image/png'`. **Default `runtime = 'nodejs'`** — the route fetches an internal
  Django API and node runtime is the reliable choice; edge is a later
  optimization only if warranted. Fetches `/api/proof/<id>/`, chooses Pick vs
  Result layout, returns `new ImageResponse(<Card/>, size)`. This single
  endpoint serves both the unfurl preview and the PNG download.

### 4.3 Share affordances
- A small reusable `ShareProofButton` component (`{ fixtureId }` prop) that,
  on click, copies `<APP_URL>/proof/<fixtureId>` to clipboard and shows a
  "link copied" confirmation, with a secondary "Download PNG" link to the
  image route.
- Placed on: each `/track-record` table row (`TrackRecordContent.tsx`) and the
  prediction detail page (`prediction/[...slug]/PredictionContent.tsx`).

### 4.4 Data flow
```
Community post (founder)  ─────────────┐
                                       ▼
        betglitch.com/proof/<id>  (unfurl → card image via opengraph-image)
                                       │  click
                                       ▼
        proof page → "See full track record" → /track-record → funnel
```

## 5. Deliberate non-goals (YAGNI)

- **No auto-posting to Telegram/social.** Phase-2 automation; premature before
  the manual experiment proves anyone cares. The founder posts by hand.
- **No card templates / customization / theming.** One Pick layout, one Result
  layout.
- **No share analytics / UTM machinery.** May add lightweight tracking later;
  not now.
- **No new database model or migration.** Reuse `PredictionLog` +
  `AccuracyCalculator`.
- **No daily-digest / multi-pick cards.** One card per fixture.
- **No changes to `ProofCapturePanel`** (the unrelated email CTA).

## 6. Testing

- **Backend unit tests** (`core/tests.py`): `/api/proof/<id>/` returns the
  correct shape for (a) a pending recommended pick (`result.resolved == False`),
  (b) a resolved win (`was_correct == True`, scores present), (c) a resolved
  loss (`was_correct == False`), and (d) 404 for a non-recommended or unknown
  fixture_id. Assert `record` matches `get_roi_simulation()` output.
- **Visual verification:** render Pick, Result-WON, and Result-**LOST** cards
  for real fixtures; confirm 1200×630 layout, brand styling, no clipped text,
  and honest loss rendering. Validate an unfurl in the Telegram and Twitter
  card validators.
- **Edge cases:** null odds → `@ n/a`; pick logged after kickoff → omit the
  "before kickoff" line; draw/void outcomes render coherently.
- **No frontend unit-test framework exists** — the card layout is verified
  visually (documented in the plan), not via a new test harness (out of scope).

## 7. Success criteria

1. From any `/track-record` row, one click yields a shareable proof link + a
   downloadable PNG.
2. Pasting the link into Telegram unfurls the correct branded card.
3. The Result-LOST card renders the honest record and "we post our losses too"
   exactly as the win card does.
4. The card's cumulative record equals the `/track-record` dashboard numbers.
5. Backend proof tests pass; existing suite stays green.
6. The founder can begin manual community seeding immediately after ship.

## 8. Risks

- **`ImageResponse` font/emoji rendering.** Satori (behind `ImageResponse`)
  needs fonts provided explicitly and has limited emoji support. Mitigation:
  use a bundled web font and prefer simple glyphs / text labels over decorative
  emoji where rendering is uncertain; verify the ✅/❌/⚡/🔒 glyphs render or
  substitute text/inline SVG.
- **Image-route runtime.** Defaulting to `runtime = 'nodejs'` (§4.2) sidesteps
  the finicky case of an edge runtime reaching an internal Django API. Edge is
  only a later optimization if PNG latency ever matters; not a v1 concern.
- **Unfurl caching.** Telegram/Twitter aggressively cache OG images. Mitigation:
  the image is deterministic per fixture state; when a pick resolves, its card
  changes pick→result — acceptable, and cache-busting is out of scope for v1.
- **Thin-edge reputational exposure.** Cards make BetGlitch more visible while
  the edge is unproven. Mitigated by the entire design: cards sell transparency,
  not profit, and the honest-losses framing is the shield, not a liability.

## 9. Next step after user approval

Invoke `superpowers:writing-plans` to produce a task-by-task implementation
plan (backend proof endpoint + tests → image route → proof page + metadata →
ShareProofButton + placements → visual verification).
