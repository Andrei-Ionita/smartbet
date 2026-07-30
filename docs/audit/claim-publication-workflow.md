# Claim publication workflow

**Implemented:** 2026-07-30 (commit `3ec5b2e`)
**Scope:** manual staff publication only. The gem selector is deliberately NOT
implemented and `/gems` is not exposed.

---

## Lifecycle

```
verified live prediction
  -> staff preview            GET  /api/proof/<fixture_id>/preview/   (staff)
  -> explicit publication     POST /api/proof/<prediction_id>/publish/ (staff)
  -> immutable public proof   GET  /proof/claim/<claim_uuid>           (public)
  -> third-party settlement   settle_published_claim(claim)
  -> immutable result card    same URL, now WON / LOST / VOID / CANCELLED
```

## Architecture

```
PredictionLog  (mutable, engine-owned)
      |
      |  optional selector  OR  manual staff review
      v
publish_prediction_claim()      <-- core/services/claim_publication.py
      v
PublishedClaim  (insert-only, hashed)
      |                                  \
      v                                   v
PublishedClaimResult (insert-only)    public proof endpoint / card
```

Claim-creation logic lives **only** in `claim_publication.py`. The future
selector chooses a candidate and calls the same function:

```python
candidate = select_best_gem(...)
claim = publish_prediction_claim(candidate.prediction_id, published_by=user)
```

It must never re-implement eligibility, snapshotting, hashing, immutability, or
permissions.

## Publication contract

`publish_prediction_claim(prediction_id, published_by=None, now=None)`
→ `PublishedClaim`, or raises `PublicationError(reason, detail)`.

Runs inside a transaction with `select_for_update()` on the source row, so two
concurrent publishes cannot both insert.

**Eligibility** (all must hold; `check_publication_eligibility()` returns the
machine-readable failures and is what the preview surfaces):

| Rule | Failure code |
|---|---|
| source exists | `prediction_not_found` |
| is a recommendation | `not_recommended` |
| not quarantined | `audit_excluded` |
| pricing status is `verified` | `pricing_not_verified:<status>` |
| odds present | `no_odds` |
| provenance complete (authoritative validator) | `incomplete_provenance:<fields>` |
| fixture has a kickoff | `no_kickoff` |
| fixture has not started | `fixture_already_started` |
| prediction generated before kickoff | `prediction_generated_after_kickoff` |
| price captured before kickoff | `odds_captured_after_kickoff` |
| price captured coherently with the prediction (±6h) | `odds_captured_before_prediction` |

Every claim field is **snapshotted** at publication. The claim never reads a
mutable source field at render time.

## Uniqueness and idempotency

Claim identity is the **source prediction**, not the fixture:

```
(prediction, market_type, predicted_outcome), non-superseded
```

`PredictionLog` is unique per fixture today, but the product is expected to
support several markets per fixture, so a `fixture_id`-only key would wrongly
block a second legitimate claim.

- Already published → the existing claim is **returned unchanged**.
- Source has since changed → still returns the original. Never rewritten.
- To change a published claim, `claim.correct(reason, **changes)` inserts a NEW
  superseding claim (`supersedes` + `correction_reason`); the original stays
  readable with its hash intact, and only the current claim counts.

Each claim also carries its own immutable `claim_id` UUID — the stable public
identifier.

## Canonical hash

`claim_hash_version = 'v1'`. SHA-256 over `canonical_payload()`, serialised with
`json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=False)`.

- **Deterministic ordering** — sorted keys, so provenance insertion order is
  irrelevant.
- **Normalised timestamps** — UTC, `isoformat(timespec='microseconds')`.
- **Stable decimals** — `Decimal(str(v)).normalize()`, so `1.80` and `1.8` hash
  identically.

Covered fields: `claim_hash_version`, `source_prediction_id`, `fixture_id`,
`home_team`, `away_team`, `league`, `league_id`, `kickoff`, `market_type`,
`predicted_outcome`, `confidence`, `odds`, `odds_market_id`,
`odds_market_description`, `odds_line`, `odds_label`, `odds_bookmaker_id`,
`odds_bookmaker_name`, `odds_selection_policy`, `odds_captured_at`,
`prediction_generated_at`, `published_at`, `prediction_run_id`, `model_version`,
`supersedes`, `correction_reason`.

Settlement is **deliberately excluded**, so recording a result can never alter a
hash.

`verify_integrity()` is the one authoritative check. On failure the claim is
logged as an error, excluded from all public performance, and the public
endpoint returns `integrity_ok: false` with a safe `integrity_error` message —
it never renders as valid.

## Settlement design — why a separate record

`PublishedClaimResult` is a one-to-one, insert-only record rather than
result columns on `PublishedClaim`. Justification:

1. **Structural immutability.** `PublishedClaim.save()` can refuse *every*
   update. With result columns it would have to permit some writes, leaving the
   invariant resting on a field allowlist someone must remember.
2. **Hash isolation.** Settlement cannot enter the hashed payload by accident.
3. **Settlement has its own metadata** — `settled_at`, `result_source`,
   `result_reference` — meaningless at publication time.
4. **Honest domain model:** what we claimed, and separately, what happened.

Transitions: `PENDING` (no row) → `WON` | `LOST` | `VOID` | `CANCELLED`.
Idempotent for an identical status; a contradictory status raises
`SettlementError('contradictory_settlement')`. There is no path back to
`PENDING` and no path between terminal states. The result row is itself
insert-only. Settlement re-reads the source from the database so it always
reflects current third-party data.

A corrected (superseding) claim is settled **in its own right** — a correction
never inherits a stale result row.

## Performance universe

| State | Counts? |
|---|---|
| `PENDING` | no |
| `WON` / `LOST` | **yes**, when integrity-valid and provenance-complete |
| `VOID` / `CANCELLED` | **no** — excluded from BOTH numerator and denominator |
| tampered (hash mismatch) | no |
| quarantined / superseded / legacy | no |

**VOID/CANCELLED policy:** no stake was ever settled, so counting such a claim
either way would misstate the record. It stays publicly visible with its own
status; it simply does not score.

At zero resolved claims every public surface shows **"Building verified
record"** / **"No verified results yet"** — never `0%` or `+0%`.

## Public proof identity

- **Stable/canonical:** `/proof/claim/<claim_uuid>` — a fixture may later carry
  several claims for different markets.
- **Compatibility:** `/proof/<fixture_id>` resolves that fixture's current
  (non-superseded) claim and canonicalises onto the claim URL via
  `alternates.canonical` and its share link.

Both read exclusively from `PublishedClaim`; neither ever falls back to
`PredictionLog`.

## Card states

| State | Badge / pill | Notes |
|---|---|---|
| `PICK — PENDING` | blue `LOGGED`, "PUBLISHED BEFORE KICKOFF" | "The result will be shown here after settlement — win or lose" |
| `RESULT — WON` | green `WON`, "THIRD-PARTY SETTLED" | identical layout to LOST |
| `RESULT — LOST` | red `LOST`, "THIRD-PARTY SETTLED" | identical layout to WON |
| `VOID / CANCELLED` | grey pill | "No result — excluded from our record entirely" |

Cards show the frozen fixture, league, kickoff, market and selection, recorded
odds **with bookmaker**, model score (labelled as a score, not a calibrated
probability), the logged-before-kickoff timestamp, and the record footer. No
legacy ROI, no profit claims, no "proven accuracy", and no current odds
presented as the recorded price.

## Tests

44 new tests in `core/tests_claim_publication.py` covering eligibility (legacy,
quarantined, incomplete provenance, started fixture, non-recommended, pre-cutoff
row updated after the cutoff), publication (staff / anonymous / non-staff, GET
cannot create, repeated POST idempotent, source mutation after publication,
duplicate prevention, no partial claim on failure), integrity (determinism, key
order, decimal stability, per-field tamper detection, settlement preserving the
hash, tampered claims excluded from performance), settlement (all four
transitions, idempotency, contradiction rejection, no-settle-to-pending,
immutable result row, third-party source recorded, VOID/CANCELLED exclusion,
claim fields surviving, wins and losses treated identically), and the stable
claim URL (frozen fields only, unknown UUID, restrained pending language,
provenance exposure, safe integrity-error state).

**Total: 181 backend + 59 frontend = 240 passing.**
