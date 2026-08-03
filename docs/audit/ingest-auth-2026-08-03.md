# Recommendation ingest — server-to-server authentication

**Date:** 2026-08-03
**Endpoint:** `POST /api/log-recommendations/`

**Unchanged:** prediction-selection logic, odds-selection policy, snapshot
semantics, published-claim rules, settlement grading, verified public-universe
logic, commercial mode, gem ranking.

---

## 1. Audit

**View:** `core.api_views.log_recommendations` — was `@csrf_exempt`,
`@require_http_methods(["POST"])`, **no authentication, no permission class**.

**Caller:** `smartbet-frontend/app/api/recommendations/route.ts`, a Next.js
server route (`runtime = 'nodejs'`), fire-and-forget POST.

**Second, non-HTTP caller:** `core/management/commands/log_recommendations_from_homepage.py`
built a fake request with `RequestFactory` and invoked the view in-process.

### Fields accepted

`fixture_id`, `home_team`, `away_team`, `league`, `kickoff`,
`predicted_outcome`, `confidence`, `expected_value`/`ev`, `odds`,
`probabilities{home,draw,away}`, `odds_data{home,draw,away,bookmaker}`,
`odds_provenance`, `best_market{type,type_id,odds,bookmaker,market_score,original_ev,odds_provenance}`,
`ensemble_info{model_count,consensus,variance,strategy}`,
`revenue_vs_risk_score`, `debug_info{market_type_id}`.

### Writes triggered

* `PredictionSnapshot` — appended per row via `snapshot_recording.record_snapshot`.
* `PredictionLog` — **created OR updated**. Update path does
  `for key, value in prediction_data.items(): setattr(existing, key, value)`.
* `pricing_integrity_status` — computed by `public_universe.status_for`.

### What that meant

1. **Injection.** Anyone could create predictions and snapshots.
2. **Overwrite.** The row is looked up by `fixture_id` alone and every field is
   overwritten. An anonymous caller could rewrite the recorded odds, market or
   outcome of a **real** existing pick.
3. **Escalation to `verified`.** `status_for` returns `PRICING_VERIFIED` when
   the row is post-cutoff, has odds, and `missing_provenance_fields` is empty.
   Provenance is entirely caller-supplied, so a crafted
   `odds_selection_policy: 'lower_median_v1'` plus the other required fields
   produced a **verified** row — which is exactly what the publication queue
   offers as publishable evidence.

`prediction_run_id` was `uuid.uuid4().hex` per request, so **retries were not
idempotent**: a retry produced a new run id and therefore a second set of
snapshots. No batch limit, no body limit, no transaction (partial writes on
failure), and `except Exception: return str(e)` — which for a `requests`
failure carries the SportMonks URL **including `api_token`**.

### Duplicate ingestion (pre-existing, reported not changed)

The scheduler GETs the Next route, which itself fire-and-forgets a POST, and
the scheduler then ingests the returned recommendations in-process. Each cycle
therefore ingested the same run **twice under two different random run ids**,
producing two snapshot sets. Deriving the run id from the request id fixes
retry duplication but not this; the two paths remain genuinely distinct runs.
See "Remaining" below.

---

## 2. HMAC contract

```text
X-BetGlitch-Timestamp     unix seconds
X-BetGlitch-Request-ID    unique per logical request, stable across retries
X-BetGlitch-Signature     hex HMAC-SHA256
```

Signed input:

```text
<timestamp>.<request_id>.<sha256(raw_request_body)>
```

`hmac.compare_digest` for comparison. The loop over accepted secrets does not
short-circuit, so it cannot leak which secret matched. Window is ±300s.
Request ids must be alphanumeric and ≤64 chars.

**Fails closed.** No secret configured ⇒ `401`, nothing written. There is no
anonymous fallback and no transition mode.

Rejection body is always:

```json
{"code": "recommendation_ingest_unauthorized",
 "detail": "The recommendation ingest request was not authorized."}
```

Never which header failed, never `str(e)`, never a traceback, provider URL, SQL
or token. The reason goes to the log only.

---

## 3. Payload schema

Validated as a batch, before any write:

| Field | Rule |
|---|---|
| `fixture_id` | positive int, unique per (fixture, market, outcome) in batch |
| `home_team` / `away_team` / `league` | non-empty, ≤100 chars |
| `kickoff` | ISO-8601, **must be in the future** |
| `best_market.type` | one of `1x2`, `btts`, `over_under_2.5`, `double_chance` |
| `predicted_outcome` | non-empty string |
| `odds` | number, `1.01 ≤ odds ≤ 1000` |
| `confidence` | number, 0–100 |
| `odds_provenance` | dict, complete per `public_universe.missing_provenance_fields` |
| `odds_captured_at` | present, not future, ≤48h old |

Batch ≤200 rows, body ≤2 MB. **A malformed row rejects the whole batch** and
ingestion runs inside a transaction, so no run is ever half-written.
`pricing_integrity_status` is always computed and never read from the payload.

The kickoff rule is the important one: it is what stops a backdated pick being
presented as foresight.

---

## 4. Replay vs retry

`IngestRequest` records `request_id`, `body_sha256`, derived
`prediction_run_id` and the response.

| Case | Behaviour |
|---|---|
| same id, same body | **legitimate retry** — stored result returned, nothing written twice |
| same id, different body | **replay** — `409`, refused |
| new id | new run |

`prediction_run_id = sha256(request_id)[:32]`, so a retry reuses the run id and
the snapshot uniqueness key `(run_id, fixture_id, market_type,
predicted_outcome)` dedupes. Genuinely different runs have different request
ids and therefore distinct snapshots.

---

## 5. Abuse protections

Batch cap, body cap, transactional boundary, replay ledger, and a warning log
on every rejected attempt (with the reason, for rate-limit tooling later).
Rate limiting is not implemented — it is defence in depth and must not stand in
for authentication, which is now present.

Railway private networking was **not** adopted: the frontend service reaches
the backend over its public hostname today, and the spec is right that IP
allowlisting is not dependable. HMAC does not depend on network topology.

---

## 6. Secret configuration

Server-side only, on **both** Railway services:

```text
RECOMMENDATION_INGEST_SECRET
```

or, for rotation:

```text
RECOMMENDATION_INGEST_SECRET_CURRENT
RECOMMENDATION_INGEST_SECRET_PREVIOUS
```

Never `NEXT_PUBLIC_*` — that prefix inlines the value into the client bundle at
build time. Verified: 0 occurrences in `.next/static`, 1 in `.next/server`.

Generate one locally (do not paste it into a chat or a commit):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Rotation

1. Set `_PREVIOUS` = current value, `_CURRENT` = new value on the **backend**.
2. Set `_CURRENT` = new value on the **frontend**.
3. Confirm a successful signed run.
4. Remove `_PREVIOUS`.

The backend accepts both while rotating and never reveals which matched.

---

## 7. Deployment sequence

No unauthenticated compatibility window was needed, because the frontend
**skips** ingest when unconfigured rather than sending an unsigned request, and
the scheduler ingests the same run in-process regardless:

1. Deploy both services. Backend enforces immediately; frontend has no secret
   yet, so it skips ingest and logs a warning. **The hourly scheduler continues
   to ingest in-process — no logging gap.**
2. Set the secret on both Railway services.
3. Both restart; signed ingest begins.
4. Verify a signed run and confirm unsigned requests are still refused.

At no point is the endpoint reachable without a signature.

---

## 8. Cross-language contract check

The signer is TypeScript and the verifier is Python, so a mismatch would be
silent until production. Verified directly: a signature produced by
`app/lib/ingestSignature.ts` is accepted by `core.services.ingest_auth.verify`,
and the same envelope with a one-character body change is rejected
(`signature mismatch`).

---

## Remaining

* **Double ingestion per scheduler cycle** (pre-existing). The scheduler GETs
  the Next route, which POSTs, and then ingests in-process — two runs, two
  snapshot sets, same recommendations. Deciding which path should own logging
  is a product call, not a security fix, so it is left as-is and flagged.
* **No `DEFAULT_PERMISSION_CLASSES`** in DRF settings, so any view that does
  not state a permission is `AllowAny`. That is the reason both this endpoint
  and the two removed earlier today were public by default rather than by
  decision. Fixing it touches every endpoint and belongs in its own change.
