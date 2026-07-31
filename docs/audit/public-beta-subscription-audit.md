# Subscription-surface audit — public beta

**Date:** 2026-07-31
**Goal:** hide every commercial surface behind ONE flag and present BetGlitch as
a free public beta. Nothing is deleted; the subscription architecture stays
intact and dormant.

---

## Complete surface inventory

### Public-facing UI (must be hidden)

| # | Location | Reference | Action |
|---|---|---|---|
| 1 | `components/Navigation.tsx:24` | `/pricing` in the desktop nav array | hidden by flag |
| 2 | `components/Navigation.tsx:95-99` | "Upgrade to Pro" CTA (desktop) | hidden by flag |
| 3 | `components/Navigation.tsx:206-210` | "Upgrade to Pro" CTA (mobile) | hidden by flag |
| 4 | `components/Footer.tsx:66-67` | "Pricing" footer link | hidden by flag |
| 5 | `app/pricing/PricingContent.tsx` | full pricing table, plans, FAQ, money-back guarantee | replaced by a beta page |
| 6 | `app/pricing/page.tsx` | pricing metadata / OG tags | replaced |
| 7 | `app/components/BettingCalculatorModal.tsx:192-226` | "Pro Feature" lock, "Upgrade to Pro — €14.99/month", "Sign Up for Pro — €14.99/month", `/pricing` link | unlocked during beta |
| 8 | `app/components/ProofCapturePanel.tsx:28-29` | "See the premium roadmap" → `/pricing` | copy replaced |
| 9 | `app/components/ProGate.tsx` | premium lock + upgrade prompt | dormant (already unused — no call sites) |
| 10 | `app/components/CheckoutButton.tsx` | "Subscribe" button → `/api/checkout` | dormant (no call sites) |
| 11 | `app/sitemap.ts:15` | `/pricing` in the sitemap | removed while disabled |
| 12 | `app/track-record/TrackRecordContent.tsx:588` | "…subscribe for the free picks and premium launch updates" | copy replaced |
| 13 | `app/prediction/[...slug]/PredictionContent.tsx:138` | "…premium launch notices" | copy replaced |
| 14 | `app/locales/translations.ts` | `nav.pricing`, `nav.upgradeToPro`, pricing strings | kept; unreferenced while disabled |

### Routes / API (must fail closed)

| # | Location | Reference | Action |
|---|---|---|---|
| 15 | `app/api/checkout/route.ts` | creates a Polar checkout session | rejects with `payments_disabled` |
| 16 | `app/api/webhooks/polar/route.ts` | Polar webhook → `upgrade-tier` | remains reachable, refuses to grant tier |
| 17 | `core/auth_views.py:270` `upgrade_tier` | grants `pro` tier | refuses while disabled |
| 18 | `/pricing` route | old pricing table | becomes the beta page |

### Backend data / entitlement (preserved, untouched)

| # | Location | Reference | Action |
|---|---|---|---|
| 19 | `core/models.py:1272-1300` `UserProfile` | `tier`, `TIER_FREE`/`TIER_PRO`, Polar subscription id | **preserved** |
| 20 | `core/migrations/0025_userprofile.py` | billing migration | **preserved, no destructive migration** |
| 21 | `core/auth_views.py:24-35` | `tier` in the auth payload | **preserved** |
| 22 | `app/contexts/AuthContext.tsx` | `isPro`, `tier`, `upgradeToPro()` | **preserved**; `isPro` no longer gates anything |

### Not commercial — deliberately untouched

These matched the keyword scan but are unrelated:

- `app/page.tsx:374` — "Upgrade your SportMonks subscription plan" (an internal
  data-provider error hint, not a user offer).
- `app/page.tsx:465`, `app/explore/ExploreContent.tsx:132` — **Pro League**, a
  Belgian football competition.
- `app/page.tsx:617`, `app/about/page.tsx:85` — "premium sports data providers",
  describing our data sourcing.
- `core/views.py` — `premium_model_v1.0`, an internal model identifier.
- Everything under `smartbet/Lib/` — a stray local virtualenv, not app code.
- "pricing integrity" / "verified pricing record" throughout — this is the
  odds-pricing audit vocabulary, unrelated to commerce. **Left exactly as is.**

### Legal / responsible-gambling copy

`app/terms/`, `app/privacy/`, `app/disclaimer/`, `app/responsible-gambling/`
retained in full. Reviewed for paid-subscription assumptions — see §Legal below.

---

## Legal review notes (not legal advice)

Areas a Romanian legal/accounting professional should review before payments are
re-enabled — flagged, not resolved here:

1. **Terms of Use** references to subscription, billing and refunds now describe
   a facility that is not offered. They remain accurate for the future paid
   product but should be re-read against the beta framing.
2. **Refund / money-back language** was the strongest commercial promise on the
   site. It is removed from public view while nothing is sold.
3. **Age eligibility, jurisdiction restrictions and responsible-gambling
   copy** are unaffected by the payment change and must stay in place — removing
   payments does not reduce these obligations.
4. **Data-processing basis** for account creation is unchanged (free accounts
   were already supported).

---

## Public-beta access policy

Deliberately a **distinct beta policy**, not "everyone is secretly Pro" — no
user is given fake paid status.

| Capability | Beta access |
|---|---|
| Public proof pages (`/proof/claim/<uuid>`, `/proof/<fixtureId>`) | anonymous |
| Transparency + track record | anonymous |
| Homepage recommendations | anonymous |
| Core app after registering (dashboard, predictions, explore) | free account |
| Betting calculator | free account (was Pro-gated) |
| Bankroll tools | free account |
| Staff-only: `/api/proof/queue/`, `/preview/`, publish endpoints | **staff only, unchanged** |
| Checkout / billing | **disabled** |
| `upgrade_tier` | **refuses while disabled** |

`UserProfile.tier` keeps its real value (`free` for everyone) — entitlement
checks simply are not applied during the beta.

---

## Feature-flag design

**One authoritative setting, read identically by both halves.**

| | Frontend | Backend |
|---|---|---|
| File | `smartbet-frontend/app/lib/commercialMode.ts` | `core/services/commercial_mode.py` |
| Variable | `NEXT_PUBLIC_COMMERCIAL_MODE` | `COMMERCIAL_MODE` |
| Enabled when | value is exactly `commercial` | value is exactly `commercial` |

**Fail closed.** Anything else — unset, empty, `true`, `1`, `COMMERCIAL`,
`commercial ` — resolves to `public_beta`. Both sides compare **strictly** and
neither normalises case, so they cannot disagree about whether BetGlitch is
selling anything. A test asserts the two implementations stay in step.

Everything else derives from this:
`PAYMENTS_ENABLED`, `IS_PUBLIC_BETA`, `shouldGateOnSubscription()`,
`hasBetaAccess()`, `PAYMENTS_DISABLED_ERROR`, `BETA_COPY`.

## Checkout and API protection

| Path | Behaviour while disabled |
|---|---|
| `GET /api/checkout` | `403 {"code":"payments_disabled","detail":"BetGlitch is currently operating as a free public beta."}` — returned **before** any credential is read or any provider request is made |
| `POST /api/webhooks/polar` | `200 {received,ignored,reason:"payments_disabled"}` — stays reachable so the provider does not disable the endpoint, but never grants a tier |
| `POST /api/auth/upgrade-tier/` | `403 payments_disabled`, checked **before** the shared-secret comparison — defence in depth |
| `/pricing` | serves the public-beta page; the pricing table is unreachable by any URL |

A hidden URL cannot start a checkout, and no payment-provider request is
generated at all.

## Reactivation plan

Re-enabling is **one configuration change**, not a code change.

**Business prerequisites (outside this repo):**

1. Company registration complete
2. Business bank account available
3. Tax and invoicing setup
4. Payment-provider approval for BetGlitch's business model
5. Terms and refund policy approved by a Romanian legal professional
6. Final pricing approved

**Technical checklist:**

7. Production payment credentials set: `POLAR_ACCESS_TOKEN`,
   `POLAR_WEBHOOK_SECRET`, `NEXT_PUBLIC_POLAR_PRODUCT_ID`, `INTERNAL_API_SECRET`
8. Webhook signature verification confirmed against a live provider event
9. Checkout smoke test end to end
10. Subscription-entitlement tests pass with the flag on
11. **Flip the flag** — set `COMMERCIAL_MODE=commercial` (backend service) and
    `NEXT_PUBLIC_COMMERCIAL_MODE=commercial` (frontend build ARG + service).
    The frontend value is inlined at build time, so the frontend must be
    **rebuilt**, not just restarted.
12. Verify: pricing nav link returns, upgrade CTAs return, `/pricing` serves the
    pricing table, `/api/checkout` creates a session, `/pricing` reappears in the
    sitemap.

Nothing was deleted, so no code is written to reactivate — see
`core/tests_commercial_mode.py` and `UpgradeTierEndpointTests`, which run with
the flag ON and prove the commercial routes still work.
