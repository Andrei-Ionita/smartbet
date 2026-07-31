# First-impression and onboarding audit

**Date:** 2026-07-31
**Scope:** public copy, information architecture, navigation, onboarding, empty
states, metadata, analytics, responsive behaviour, accessibility.
**Explicitly out of scope and untouched:** odds-selection policy,
pricing-integrity classification, snapshot integrity, claim publication rules,
settlement rules, the verified public-universe definition, commercial-mode
architecture, scheduler behaviour, gem ranking.

---

## 1. Audit findings

### Unsupported or misleading claims

| Where | Claim | Why it fails |
|---|---|---|
| `translations.ts` hero | "The only platform combining AI power with total transparency… we promise you'll bet mathematically correctly" | Unverifiable superlative plus a promise about the user's own behaviour |
| `page.tsx` CTA | "Ready to Start Winning?" | Promises the outcome the record cannot support |
| `page.tsx` CTA | "Join thousands of users who trust BetGlitch" | No verified user count |
| `translations.ts` | "Save Time, Bet Smart" | Instructs a bet; not model-analysis language |
| `ExploreContent.tsx` | "3. Bet Smart" | Same |
| `about/page.tsx` | "shows every call we have ever made" | False — only published picks enter the record |
| `about/page.tsx` | "Every prediction is public… includes every prediction, win or loss" | False for the same reason |
| `track-record/page.tsx` metadata | "every prediction BetGlitch has ever made. Real results, real ROI" | Claims a proven history that does not exist post-cutoff |
| `translations.ts` transparency | "impossible to fake", "we cannot manipulate them" | Absolute claims |
| `translations.ts` transparency | "Complete history — every recommendation we made is here, you can audit everything" | False |
| `EmailCapture.tsx` | "Get Our Best Picks Every Week", "Join bettors receiving…" | Unsupported quality claim + vague social proof |
| `ProofCapturePanel.tsx` | "Get weekly Smart Picks… and launch updates" | Old vocabulary; "launch updates" is commercial-adjacent |

### Structural problems

- **Nine competing homepage sections** and **three peer CTAs** in the hero
  (Explore / Track Record / Learn More), then "View All Predictions", then
  "Explore Predictions" again in a second CTA block.
- **A 26-league wall**, each card stamped `PRODUCTION` — an internal deployment
  state with no user meaning.
- **`/track-record` was not in the navigation at all**, despite being the trust
  surface the product rests on and the hero's secondary destination.
- **`nav.monitoring` was labelled "Results"**, colliding with the actual
  results page.
- **Registration gave no reason to register** ("Join BetGlitch for AI-powered
  predictions") and dropped the user on the marketing homepage afterwards, with
  no acknowledgement that anything had happened.
- **Every page invented its own vocabulary** for the same objects:
  "recommendations", "smart picks", "top quality bets", "predictions", "calls".
- **Mutable signals and immutable claims looked identical** on screen.

### Defects found (not merely copy)

1. **A new account could never reach the dashboard.** Registration calls
   `localStorage.removeItem('smartbet_session_id')`; the dashboard redirected
   anyone without that key to `/bankroll`. Fixed: authentication decides access.
2. **The mobile menu close button rendered a rotated `LogOut` icon** as a
   stand-in for `X` — which was already imported. The one control every mobile
   user must press read as "sign out".
3. **The prediction log read as the verified record.** Found by reading the
   deployed page, not the source: the stats panel correctly reported 0 settled
   published picks while the table below listed 299 pre-cutoff rows with
   confidence, EV and dollar P/L. Fixed by exposing `pricing_integrity_status`
   as a read-only display field, badging each non-verified row, and stating the
   count in a banner.
4. **Language toggles were 24×32px**, below the 44px touch-target floor, in
   both the desktop bar and the mobile menu.

---

## 2. Terminology system

`smartbet-frontend/app/lib/terminology.ts` is the single source. Bilingual in
one module — the EN/RO switcher is user-reachable, and a structural-parity test
fails if the two shapes diverge.

| Concept | Meaning | In public performance? |
|---|---|---|
| **Live model signal** | Current model output for an upcoming fixture; changes when models rerun, odds move, new data arrives or a newer snapshot is generated | **No** |
| **Published pick** | An immutable `PublishedClaim` frozen before kickoff with its selection, model score, recorded odds, bookmaker, timestamps and provenance | Once settled |
| **Verified record** | Resolved, integrity-valid published claims only | **This is the universe** |

---

## 3. Visual language

`app/components/StatusBadge.tsx`. The encoding is structural, not decorative:

- **Dashed border = mutable.** Deliberately the only dashed badge in the
  product; a test asserts exactly one exists.
- **Solid border = frozen** before kickoff, cannot change again.
- **Filled = settled.**

`LIVE SIGNAL · PUBLISHED — PENDING · RESULT — WON · RESULT — LOST · VOID ·
CANCELLED · LEGACY — NOT IN VERIFIED RECORD`

Status is carried by label text and icon as well as colour, so it survives
greyscale and colour-blindness. WON and LOST share identical weight, size and
treatment — a test compares their class strings with the hue substituted out.

---

## 4. Known gaps

- **Real breakpoint testing was not possible in this environment**:
  `resize_window` reports success but the rendered viewport stays at 1280px.
  Responsive behaviour was addressed through layout classes and verified by a
  programmatic tap-target and overflow audit, not by viewport screenshots at
  320/375/390/768px.
- **No analytics provider is installed.** `app/lib/analytics.ts` is a
  dependency-free seam that emits to `window.gtag`/`window.plausible` when
  present and no-ops otherwise. Wiring a provider is a separate decision.
- **The age-verification gate fronts every page**, so the five-second
  explanation is gated behind a modal. Legally necessary; left in place.
- **Backend tests require `PRICING_INTEGRITY_CUTOFF`** in the environment. It
  is not in `.env`; without it ~54 claim and pricing tests fail misleadingly.
