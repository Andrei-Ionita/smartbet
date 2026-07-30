# Deployment log — verified pricing record

**Executed:** 2026-07-30
**Runbook:** `docs/audit/deployment-runbook-verified-pricing.md`
**Copy approved by:** founder (Andrei), 2026-07-30, per
`docs/audit/public-copy-proposal-2026-07-29.md` with final revisions
(hash wording, third-party wording, price-audit wording, single claim-based
universe).

---

## Facts

| Item | Value |
|---|---|
| Commit deployed | `f5e5c3f` |
| Migrations applied | `0026_predictionlog_odds_provenance_and_more`, `0027_publishedclaim_correction_reason_and_more` |
| **Cutoff (UTC)** | **`2026-07-30T08:32:00+00:00`** |
| Cutoff configured via | `PRICING_INTEGRITY_CUTOFF` env var on `smartbet-backend` |
| Backend build | ✅ live ~45s after push |
| Frontend build | ✅ live (Linux Docker; the local Windows/OneDrive `copyfile` failure did not reproduce) |
| Tests at deploy | 137 backend + 59 frontend = **196 passing** |

## Classification result

| Status | Rows |
|---|---|
| `legacy_unverified` | 760 |
| `audit_excluded` | 35 |
| `verified` | **0** |
| `missing_provenance` | 0 |
| **Total** | **795** |

35 rows changed (previously-default statuses corrected to `audit_excluded`).
No pre-cutoff row was classified verified. `PublishedClaim` rows: **0**.

## Step-9 hard gate — independent price verification

Production selections were recomputed from the raw SportMonks payload,
independently of application code:

| Fixture | Market | Books | Prices | Independent lower median | Stored | Match |
|---|---|---|---|---|---|---|
| 19726943 Cardiff v Swindon | 14 (Both Teams to Score) | 1 | 1.80 | 1.80 | 1.80 | ✅ |
| 19716420 York v Crawley | 14 (Both Teams to Score) | 8 | 1.63–1.75 | **1.70** | 1.70 | ✅ |

**Over/Under 2.5 verification** (fixture 19714700, the fixture that exposed the
defect): correct markets 80/7 at line 2.5 label Over offered 5 books
(1.58–1.63) → selected **1.60**. The collision markets were present in the same
payload and correctly rejected — including `market_id 53` "2nd Half Goals" at
**3.50**, which is exactly the value production previously stored.

## Smoke tests

| # | Test | Result |
|---|---|---|
| S1 | Railway build / health | ✅ backend 200, frontend 200 |
| S2 | Correct market for O/U 2.5 | ✅ 1.60 from market 80/7, not 3.50 from market 53 |
| S3 | Payload order independence | ✅ 50-shuffle test suite + production median matched independent calc |
| S4 | Provenance complete | ✅ market id, description, line, label, bookmaker id **and name**, capture time, policy `lower_median_v1` |
| S5 | Missing exact odds → non-verified | ✅ typed unavailable reasons; recommendation pool shrank 4 → 2 as loose matches were rejected |
| S6 | Legacy excluded from public ROI/accuracy | ✅ `total_bets=0`, `accuracy total=0`, `has_verified_results=false` |
| S7 | Quarantined excluded | ✅ 35 `audit_excluded` rows in no public aggregate |
| S8 | Cross-surface consistency | ✅ dashboard, accuracy, leagues, by-confidence, monitoring all report 0 |
| S9 | Leagues deduplicated | ✅ 0 rows / 0 distinct (was **241 rows for 25 leagues**) |
| S10 | Monitoring aligned | ✅ `verified_public.accuracy = null`; legacy 57.7% on 291 moved to `legacy_diagnostics`, labelled |
| S11 | No mutable public proof | ✅ every fixture returns `published=false`, `state=unpublished`, **no `pick` key**; `/preview/` → HTTP 401 anonymously |
| S12 | New rows can become verified | ⚠️ logic verified by test; **awaiting first genuinely new fixture** (see below) |
| S13 | Zero-sample display | ✅ homepage renders "Building verified record"; no `0%`/`+0%`; old claims absent |

## Public copy now live

- Homepage: **"Building verified record"** (zero-sample state). Removed
  "100% Transparent", "proven accuracy", "Verified Smart Picks".
- Pricing: **"Everything in Free, plus full access."**
- Dashboard methodology: corrected selection criteria (55%/60%), SHA-256
  integrity + separate-corrections wording, third-party settlement policy
  wording, price audit-trail wording, `pricing_standard` disclosure naming the
  cutoff date.

## Important nuance — why the 2 current picks stay legacy

Both live recommendations (Cardiff, York) now carry **correct** provenance from
the new selector, yet remain `legacy_unverified`. Their `prediction_logged_at`
is 2026-07-20 / 2026-07-25 because they are **pre-existing rows updated** by the
new pipeline (`auto_now_add` never moves).

This is the correct outcome. Pairing a 10-day-old "logged before kickoff"
timestamp with a price captured today would itself be a false claim. Only
genuinely new predictions — created after the cutoff, with their price captured
at creation — can be verified. The verified record therefore starts clean.

## State after deployment

- Public accuracy **and** ROI both begin from the verified record: both are
  currently empty, by design.
- Legacy data preserved (795 rows, nothing deleted), classified, and excluded
  from every public performance surface.
- No mutable public proof path remains.
- No legacy ROI is publicly accessible.

## Remaining blockers

1. **Nothing creates `PublishedClaim`.** The publication path lives in the
   unbuilt `/gems` selector, so every proof URL is `unpublished` and public
   performance stays empty until it ships.
2. **Gem selector not implemented**, and must be recalibrated on clean data —
   its evidence cells were built on contaminated prices.
3. **First verified results need new fixtures.** Pre-season volume is thin; a
   defensible sample needs roughly 40+ settled published claims.
