# Settlement endpoint hardening + scheduler heartbeat

**Date:** 2026-08-03
**Scope:** close unauthenticated settlement triggers; make the scheduler observable.

**Untouched:** prediction logic, odds selection, pricing-integrity rules,
snapshots, publication, settlement grading, commercial mode, UX.

---

## 1. What was open, and why

### `/api/update-fixture-results/` — the serious one

```python
@csrf_exempt
@require_http_methods(["POST"])
def update_fixture_results(request):
```

A plain Django view with **no authentication, no permission class and no CSRF
protection**. Per call it selected up to 50 pending predictions from the last
seven days, issued **one SportMonks request per prediction**, and wrote
`actual_outcome`, `actual_score_home/away` and `match_status`. On failure it
returned `str(e)`.

**It had a live public caller.** `/monitoring` is a public page. It renders
`RecommendedPredictionsTable`, which POSTed to a Next.js proxy route
(`app/api/django/update-results/route.ts`) **on every mount** — `if (forceUpdate
|| isLoading)` is true on first load — and again on every manual refresh.

So any anonymous visitor could:

* trigger up to 50 third-party API calls by loading a page;
* cause production writes to `PredictionLog`;
* overlap arbitrarily with other visitors and with the scheduler, since there
  was no lock of any kind.

It also duplicated `ResultUpdaterService` with a **divergent inline
implementation**, so results could be written by two different code paths with
different behaviour.

### `/api/transparency/update-results/`

```python
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_result_update(request):
```

`AllowAny`, csrf_exempt, ran `ResultUpdaterService().update_all_pending_results(
max_predictions=50)`, returned `str(e)`. Its only caller — an "Update Results"
button on the public track-record page — was removed on 2026-08-03.

### Historical purpose

Both date from the pre-scheduler era, when results were refreshed by whoever
happened to open the page. `docs`-era `TRANSPARENCY_SYSTEM_COMPLETE.md` still
describes the transparency one as a "Manual trigger". Once
`worker: run_scheduler --interval 60` existed, they became redundant — but
neither was withdrawn.

### Exceptions reachable through `str(e)`

`requests` failures (`ConnectionError`, `HTTPError`, `Timeout` — carrying the
full SportMonks URL **including `api_token`**), `django.db` errors (carrying SQL
and connection detail), `KeyError`/`TypeError` from provider payload shape
changes.

---

## 2. Resolution: removed, not protected

Neither had a legitimate non-staff caller, so both **routes and both view
functions are deleted**. There is now no HTTP trigger for result recording at
all — for anyone, staff included. Recording has exactly one path:

```text
run_scheduler → update_results → settle_published_claims
```

Manual operation is `python manage.py update_results --max N`, and settlement
is `python manage.py settle_published_claims`.

Callers removed: the Next.js proxy route, and the fetch in
`RecommendedPredictionsTable`. That component now only reads.

**Error handling:** no public surface can reach these code paths any more, so
there is no `str(e)` to leak. The heartbeat stores a short exception **type
name** only (e.g. `RuntimeError`); the full traceback goes to the application
log correlated by `run_id`.

---

## 3. Scheduler heartbeat

Removing the last public trigger creates a new failure mode: the worker is now
the only thing that can settle anything, so **a dead worker is indistinguishable
from a healthy one with nothing to do** — claims would sit PENDING forever and
no surface would say why.

`SchedulerHeartbeat` is a single-row operational gauge recording last run
started / completed / succeeded / failed, status, duration, per-run deltas for
snapshots, results and claims, a short failure code, `run_id`, interval and
version.

Counts are measured as **table deltas** around the cycle rather than parsed from
command output, so they stay correct however individual commands report
themselves.

Health is **derived, not stored**:

| state | meaning |
|---|---|
| `never_run` | no cycle has ever started |
| `failed` | the last cycle raised |
| `delayed` | no cycle has **started** within `2 × interval + 5 min` |
| `healthy` | otherwise |

`delayed` keys off *start*, not completion, so a hung run cannot keep reporting
healthy on the strength of the previous success. The grace is two intervals so a
single slow or skipped cycle is not a false alarm.

### Concurrency

`record_run` claims the row under `select_for_update` inside a transaction and
refuses a second concurrent run with `SchedulerAlreadyRunning`, so a manual
invocation cannot interleave with the worker on the same fixtures. A run
abandoned by a hard-killed worker is taken over after 90 minutes rather than
wedging the lock forever.

### Observability must never block settlement

On a fresh deploy the worker boots with `--run-now` while the **web** process is
still running `migrate`, so the heartbeat table may not exist for the first
cycle. Recording therefore **degrades**: if the heartbeat cannot be claimed or
written, the cycle runs anyway and the failure goes to the logs. A missing
heartbeat surfaces as `delayed` — a much cheaper failure than a scheduler that
refuses to run. `SchedulerAlreadyRunning` is deliberately re-raised through the
degradation path so the concurrency guard still holds.

### Where staff read it

```text
GET /api/internal/scheduler-health/     (IsAdminUser; JWT or session auth)
Django admin → Core → Scheduler Heartbeat   (read-only, no add/delete)
```

Anonymous gets `401` and learns nothing. Non-staff gets `403`. Nothing about
scheduler state, counts, failure codes or provider diagnostics is public.

---

## 4. Verification

| Check | Result |
|---|---|
| `/api/update-fixture-results/` POST/GET/PUT | 404 |
| `/api/transparency/update-results/` POST/GET/PUT | 404 |
| Frontend proxy `POST /api/django/update-results` | 404 |
| Result-update trigger in any `/monitoring` chunk | none |
| `/api/internal/scheduler-health/` anonymous | 401, no state leaked |
| Cardiff `20adfb1e…` | published, `integrity_ok: true`, `superseded: false`, odds 1.8, hash `0c1aa8c6b2d066a3` |
| Checkout | 403 `payments_disabled` |
| Public performance | `total_bets: 0`, `has_verified_results: false` |
| Backend tests | 267 pass, 2 pre-existing loader errors (269 ran) |
| Frontend tests | 187 pass |

---

## 5. Note for a later pass

DRF has no `DEFAULT_PERMISSION_CLASSES` in this project, so **every view that
does not state a permission is `AllowAny`**. That is what made both endpoints
public by default rather than by decision. Setting a restrictive default and
opting public views in explicitly would prevent the next instance of this, but
it touches every endpoint and belongs in its own reviewed change.
