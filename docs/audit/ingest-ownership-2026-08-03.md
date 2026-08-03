# Ingestion ownership and API permission safety

**Date:** 2026-08-03
**Scope:** make scheduler ingestion canonical; classify every API view explicitly.

**Unchanged:** recommendation calculations, odds selection, snapshot semantics,
publication, settlement, commercial mode, gem ranking.

---

## 1. Canonical ingestion

### Before

```text
scheduler
  → GET Next.js /api/recommendations
       → Next.js background POST /api/log-recommendations/    (run A)
  → scheduler ingests the returned payload in-process          (run B)
```

Two prediction runs and two snapshot sets for one calculation, under two
different random run ids.

The worse property: that background POST fired on **any** request to the route,
so a browser loading the homepage created and updated prediction records as a
**side effect of a GET**.

### After

```text
scheduler
  → fetch recommendation payload
  → core.services.recommendation_ingest.ingest_recommendations()   (one run)
  → PredictionLog updated, PredictionSnapshot appended
```

The Next.js route is read/computation-only. Nothing a public request can reach
creates or updates a prediction record.

---

## 2. HMAC endpoint: dormant, retained

`POST /api/log-recommendations/` has **no production caller**. It is kept for a
future explicit server-to-server integration and remains fully armed:

* fails closed with no secret configured (verified: 401 with none set)
* rejects unsigned and mis-signed requests
* strict validation, replay protection, absent from browser code

**`RECOMMENDATION_INGEST_SECRET` is NOT required for normal operation.** The
scheduler does not use it. Do not configure a secret to preserve a duplicate
call path — there is no longer one to preserve.

---

## 3. Prediction run identity

`prediction_run_id` is now **derived from the payload content**
(`sha256(json.dumps(recs, sort_keys=True))[:32]`) instead of `uuid4()`:

| Case | Result |
|---|---|
| retry of the same run | same id → snapshot uniqueness key absorbs it → nothing appended |
| genuinely new run | differs by at least `odds_captured_at` → new id → new immutable snapshots |
| dict key ordering differs | same id (`sort_keys`) — ordering can never split one run in two |

All snapshots from one calculation share one run identity.

The HTTP boundary keeps its own rule — run id derived from the request id — so
a signed retry is idempotent there too.

### Snapshot counts

Measured in test, deterministically:

| Scenario | Snapshots before | Snapshots after |
|---|---|---|
| One cycle, 2 fixtures | 0 | **2** (1 run id) |
| Same payload ingested twice (the old duplicate) | 0 | **2, not 4** — second appended 0 |
| Re-priced second run | 2 | **3** — new run appended 1 |

Production snapshot totals are not exposed publicly by design; the per-cycle
delta is on the staff heartbeat as `snapshots_created`. Before this change a
cycle recorded roughly double what one calculation produced.

---

## 4. API permission inventory

DRF has no `DEFAULT_PERMISSION_CLASSES` here, so a view that says nothing is
**public**. That is how five operational endpoints came to be anonymous.

### DRF views — all now explicit

| Permission | Views |
|---|---|
| `AllowAny` | `public_accuracy_dashboard`, `accuracy_summary`, `league_accuracy`, `recent_predictions_with_results`, `quick_stats`, `proof_by_claim`, `register`, `login`, `refresh_token`, `upgrade_tier`*, `create_bankroll`, `get_bankroll`, `update_bankroll`, `get_stake_recommendation`, `record_bet`, `settle_bet`, `get_transactions`, `get_bankroll_stats` |
| `IsAuthenticated` | `logout`, `get_user` |
| `IsAdminUser` | `publication_queue`, `publish_snapshot_view`, `publish_claim_view`, `proof_preview`, `scheduler_health` |

\* `upgrade_tier` is `AllowAny` at the DRF layer but refuses before any other
check while `COMMERCIAL_MODE` is `public_beta`, and otherwise requires
`INTERNAL_API_SECRET`.

The six bankroll views previously relied on the implicit default. They are
session-scoped — every row is keyed by a client-generated `session_id` — so
`AllowAny` is correct, but it is now **stated**, with the rationale in the
module. Session ids are bearer capabilities; that is existing product design.

### Non-DRF views — inventoried with their mechanism

| View | Protection |
|---|---|
| `get_recommendations`, `get_fixture_details`, `get_recommended_predictions_with_outcomes`, `search_fixtures` | `read_only` |
| `log_recommendations` | `hmac` |
| `subscribe_email`, `track_marketing_event` | `public_write` (intentional, no prediction impact) |
| `marketing_webhook` | `secret_header` — **see Remaining** |

### Regression test

`core/tests_api_permissions.py` fails when:

* a DRF view is added without `@permission_classes`;
* a non-DRF view is added without being inventoried with its mechanism;
* an unrecognised permission class is used;
* a public GET view contains a write call.

The global default is deliberately **not** switched to `IsAuthenticated`: the
inventory contains genuinely public endpoints that it would break.

---

## 5. Side-effecting GET audit

Two removed, both unauthenticated, neither with any caller:

* **`GET /api/fix-performance/`** — iterated **every** settled prediction and
  called `calculate_performance()`, rewriting `profit_loss` and `roi_percent`
  across the table. Self-described as "temporary". Returned `str(e)`.
* **`POST /api/mark-recommended/`** — set/cleared `is_recommended` on arbitrary
  fixture ids. `core/management/commands/restore_stripped_recommendations.py`
  exists because this endpoint once stripped `is_recommended=True` from live
  rows.

Remaining GET routes verified read-only. Two notes:

* `GET /api/checkout` (Next.js) creates a Polar checkout session and redirects.
  A GET with an external side effect, but it is the intended payment UX, writes
  nothing to our database, and is currently disabled by `COMMERCIAL_MODE`.
* `DELETE /api/metrics` (Next.js) resets an in-process performance monitor.
  Unauthenticated, but in-memory observability only — no database, provider,
  settlement or prediction impact, and it resets on deploy anyway. Reported,
  not changed.

---

## 6. Verification

| Check | Result |
|---|---|
| `/api/fix-performance/` GET & POST | 404 |
| `/api/mark-recommended/` GET & POST | 404 |
| `/api/update-fixture-results/` | 404 |
| `/api/transparency/update-results/` | 404 |
| `/api/log-recommendations/` unsigned | 401 (no secret configured) |
| **3 × public GET `/api/recommendations`** | **200, rows 320 → 320, newest timestamp unchanged** |
| Public transparency reads (5) | 200 |
| `/api/internal/scheduler-health/`, `/api/proof/queue/` anonymous | 401 |
| Cardiff `20adfb1e…` | published, `integrity_ok: true`, `superseded: false`, odds 1.8, hash `0c1aa8c6b2d066a3` |
| Checkout | 403 `payments_disabled` |
| Public performance | 0 / 0 |
| Row statuses | verified 5, legacy 307, audit_excluded 8 — unchanged |
| Backend tests | 326 pass, 2 pre-existing loader errors (328 ran) |
| Frontend tests | 193 pass |

---

## Remaining

* **`marketing_webhook` fails open.** The check is
  `if expected_secret and provided_secret != expected_secret` — when
  `MARKETING_WEBHOOK_SECRET` is unset, it is skipped entirely and anyone can
  post marketing events. Same defect class as the ingest secret, but fixing it
  blind could break a live Brevo integration, so it is reported rather than
  changed. **Confirm the secret is set, then drop the `expected_secret and`
  guard** so it fails closed.
* `DELETE /api/metrics` is an unauthenticated in-memory metrics reset.
* Bankroll session ids remain bearer capabilities.
