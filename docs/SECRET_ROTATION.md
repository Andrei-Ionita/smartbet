# Secret rotation

Manual procedures. Nothing here is automated, and nothing here contains a
credential — not the value, not a digest, not a prefix.

---

## Why the SportMonks token needs rotating

On **2026-08-06** the live token was printed to stdout during a backend test run:

```
SportMonks API error: HTTPSConnectionPool(host='api.sportmonks.com', port=443):
Max retries exceeded with url: /v3/football/fixtures/between/...?api_token=<TOKEN>&...
```

No line of code printed the token deliberately. SportMonks authenticates with
the token as a **query parameter**, and `requests` embeds the fully resolved
request URL in its exception message — so `print(f"...{e}")` around any provider
call discloses the credential the moment the provider is unreachable.

The disclosure surface was: local terminals, CI logs, and — via
`core/api_views.py` — an **HTTP response body** returned to the caller.

The code paths are fixed (see `core/services/redaction.py`), but **a credential
that has been written to a log is compromised and must be replaced.** Redaction
prevents the next leak; it does not undo this one.

Treat the current token as exposed until this procedure is completed.

---

## SportMonks API token — rotation procedure

**Prerequisites:** SportMonks dashboard access; Railway access to the project
`confident-renewal`; ability to watch a scheduler cycle.

**Expected downtime:** none, if the order below is followed. SportMonks permits
the old and new token to be valid simultaneously during the overlap.

### Affected Railway services

| Service | Uses the token for |
|---|---|
| `smartbet` (Next.js frontend) | The recommendation engine's fixture, odds and prediction calls |
| `smartbet-backend` (Django + scheduler worker) | `result_updater`, `result_evidence`, backfill and audit commands |

Both read `SPORTMONKS_API_TOKEN`. Some legacy code also reads `SPORTMONKS_TOKEN`
as a fallback — check whether it is set on either service and rotate it too, or
remove it if unused.

### Steps

1. **Create the replacement.** SportMonks dashboard → API tokens → create a new
   token with the same subscription scope. Do **not** delete the old one yet.

2. **Confirm the new token works before it is load-bearing.** From a machine
   that is not a production service, call a cheap endpoint (for example
   `/v3/football/leagues`) with the new token and confirm HTTP 200. Do not paste
   the token into a shared terminal, a chat, or a ticket.

3. **Update `smartbet-backend` first.** The backend tolerates a brief provider
   failure — a failed stage marks the cycle `degraded` and settlement continues
   — so it is the safer place to discover a bad value.

   Railway dashboard → `smartbet-backend` → Variables → edit
   `SPORTMONKS_API_TOKEN` → deploy.

4. **Update `smartbet`.** Same procedure. The frontend's recommendation engine
   returns a 500 with `API configuration error` if the token is missing entirely,
   and provider 401s surface as empty recommendations — both are visible fast.

5. **Verify live provider authentication.**
   - Public endpoint returns recommendations:
     `curl -s https://www.betglitch.com/api/recommendations | python -c "import sys,json;print(len(json.load(sys.stdin)['recommendations']))"`
     A non-zero count means the frontend authenticated successfully.
   - Watch one scheduler cycle (see below) and confirm the
     `log_recommendations_from_homepage`, `update_results` and
     `capture_signal_evidence` stages all report `ok`.

6. **Revoke the old token** in the SportMonks dashboard, only after step 5
   passes on both services.

7. **Record the rotation date** in this file's log at the bottom. Do not record
   the token.

### Rollback

If step 5 fails:

1. Restore the previous value on the affected service and redeploy. The old
   token is still valid until step 6.
2. If the old token was already revoked, generate another new one and repeat
   from step 3 — there is no way to un-revoke.
3. A scheduler cycle that failed during the window needs no repair: ingestion is
   idempotent (the run id is content-derived), settlement inserts rather than
   overwrites, and evidence capture is append-only with a content hash. The next
   cycle catches up on its own.

### What NOT to do

- Do not `railway variables --json` on a shared screen, and do not paste its
  output anywhere: it prints every secret in plaintext. That command is how the
  token was first exposed in this project, before the test-run incident.
- Do not put the token in a URL you then paste into a browser, an issue, or a
  commit message.
- Do not set a real token in any test environment. `smartbet/settings.py`
  replaces known secret variables with fakes when `manage.py test` runs, and
  `core/tests_secret_redaction.py` fails if a production-shaped token is
  readable during a test run.

---

## Internal shared secret (`INTERNAL_API_SECRET`)

Authenticates `/api/internal/recommendations` and `/api/internal/evidence`.

The value must be **identical** on `smartbet` and `smartbet-backend`. A mismatch
does not fail loudly at the transport layer — the request is simply refused —
so rotate both together:

1. Generate a new random value (32+ bytes, URL-safe).
2. Set it on **both** services.
3. Redeploy both. A cycle that runs mid-rotation fails its ingestion stage and
   marks the cycle `degraded`; the next cycle recovers.
4. Confirm: `curl -s -o /dev/null -w "%{http_code}" https://www.betglitch.com/api/internal/recommendations`
   must return `401` without credentials.

The ingestion command validates the payload shape it receives and aborts if the
EV fields are absent, so a mismatch cannot silently write null-EV predictions.

---

## Watching one scheduler cycle

```
railway logs --service smartbet-backend
```

A healthy cycle prints each stage in order and ends with
`✅ All tasks completed successfully.` A failed stage prints
`❌ Error running <stage>` (redacted) and the cycle ends
`⚠️ Cycle DEGRADED — stages failed: …`.

---

## Rotation log

| Date | Secret | Reason | By |
|---|---|---|---|
| _pending_ | `SPORTMONKS_API_TOKEN` | Exposed in test stdout and an HTTP body, 2026-08-06 | — |
