# Railway production architecture

Operational reference for the BetGlitch production environment. Non-secret
information only — variable **names** are listed, never values.

Project `confident-renewal`, environment `production`, region `us-west2`.

## Active services

| Service | Source | Responsibility |
|---|---|---|
| `smartbet` | repo, root dir | **The scheduler.** Long-running worker. Sole owner of prediction ingestion, result updates and claim settlement. |
| `smartbet-backend` | repo, root dir | Django API behind `api.betglitch.com`. Serves reads; holds no scheduled work. |
| `smartbet-frontend` | repo, `/smartbet-frontend` | Next.js site at `www.betglitch.com`. Dockerfile builder. Calls SportMonks to price fixtures and exposes `/api/recommendations`, which the scheduler consumes. |
| `Postgres` | image | PostgreSQL 17. |
| `smartbet-db` | image | PostgreSQL 17. |

All three application services deploy from `Andrei-Ionita/smartbet` @ `master`;
a push to `master` builds all of them.

## Scheduler service (`smartbet`)

**Builder:** Railpack.

**Build Command** — set in the dashboard under Settings → Build. It cannot be
set from the CLI (see *Known CLI limitation* below):

```
chmod +x ./build.sh && sh ./build.sh
```

**Start Command:**

```
python manage.py run_scheduler --interval 60 --run-now
```

One replica, restart policy `ON_FAILURE`. The interval sleeps from the *end* of
each cycle, so start-to-start is 60 min plus the previous run's duration.

### Cycle stages

`run_scheduler` runs four management commands in this fixed order, then writes
the heartbeat:

1. `log_recommendations_from_homepage` — fetches `/api/recommendations` and
   ingests it in-process. This is the **only** prediction write path.
2. `update_results` (`max=100`, `hours_after` defaults to 3)
3. `mark_recommended_predictions` (`min_confidence=60.0`, `min_ev=15.0`)
4. `settle_published_claims` — **must** run after `update_results`, which is
   what grades the underlying predictions.
5. Heartbeat write (`SchedulerHeartbeat`, key `scheduler`).

Note: `run_task()` catches per-stage exceptions and continues, and the heartbeat
still reports `success`. A cycle in which every stage failed would still show
`health() == healthy`. **Heartbeat status alone is not proof the stages did
work** — check the per-stage log lines.

## Required environment variables (names only)

| Name | smartbet | smartbet-backend | smartbet-frontend |
|---|:--:|:--:|:--:|
| `DATABASE_URL` | ✓ | ✓ | |
| `DJANGO_SECRET_KEY` | ✓ | ✓ | |
| `ALLOWED_HOSTS` | ✓ | ✓ | |
| `CORS_ALLOWED_ORIGINS` | ✓ | ✓ | |
| `CSRF_TRUSTED_ORIGINS` | ✓ | ✓ | |
| `DEBUG` | ✓ | ✓ | |
| `PRICING_INTEGRITY_CUTOFF` | ✓ | ✓ | |
| `PYTHON_VERSION` | ✓ | ✓ | |
| `SPORTMONKS_API_TOKEN` | ✓ | ✓ | ✓ |
| `MISE_PYTHON_GITHUB_ATTESTATIONS` | ✓ | ✓ | |
| `FRONTEND_URL` | | ✓ | |
| `INTERNAL_API_SECRET` | | ✓ | |
| `NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED=disabled` | | ✓ | ✓ |

| `BREVO_API_KEY` | | required | |
| `BREVO_SENDER_EMAIL` | | required | |
| `BREVO_SENDER_NAME` | | recommended | |
| `BREVO_SANDBOX_MODE` | | required | |

Neither database service carries the SportMonks token, by design.

`NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED` defaults closed. Keep it `disabled` on
both the backend and frontend during the accountless public beta. Only the exact
value `enabled` restores registration, authentication, bankroll, newsletter and
pricing routes; reactivation also requires the Brevo and legal checks below.

`BREVO_API_KEY` and `BREVO_SENDER_EMAIL` are required only when account
registration is re-enabled: the password-recovery endpoint fails closed with
503 when transactional email is not configured. `BREVO_SANDBOX_MODE` must be
`False` in that phase or Brevo will accept and deliberately drop reset emails.

Railway terminates public TLS and forwards the original scheme. Django trusts
that forwarded scheme, enforces HTTPS again at the application boundary, marks
cookies secure and emits a one-hour HSTS header. `/api/health/` is the only
redirect exemption so Railway's internal deployment probe still receives the
required 200. Extend HSTS only after every subdomain has been audited; do not
enable preload during the public beta.

### `MISE_PYTHON_GITHUB_ATTESTATIONS=false` — required, not optional

Both Python services need this. Without it the build dies here:

```
mise ERROR Failed to install core:python@3.11.9:
      No GitHub artifact attestations found for python@3.11.9
```

mise downloads the interpreter successfully and then refuses to install it
because GitHub returns no artifact attestations for that release. Any new
Python service cloned from this repo needs the variable before its first build.

## `railpack.json`

Committed at the repo root (`199f2f0`):

```json
{
  "$schema": "https://schema.railpack.com",
  "deploy": { "aptPackages": [] }
}
```

Railpack's Python provider adds `libpq5` to the runtime image whenever
`usesPostgres()` is true, and one of that predicate's three branches is a plain
string scan of the Django settings for `django.db.backends.postgresql`
(`smartbet/settings.py:115`). It therefore fires despite `requirements.txt`
pinning `psycopg2-binary`, which the provider otherwise excludes by name.

The package is unused — `psycopg2` links its own vendored
`libpq-e8a033dd.so.5.16` (libpq 16) out of `psycopg2_binary.libs`, never
`/usr/lib/x86_64-linux-gnu/libpq.so.5` (the apt copy, 15.18); no module under
the venv links the system library at all. The apt step was also what killed
every cold build with exit 137. `deploy.aptPackages` is the documented override
for the runtime apt list and file config *replaces* slice values, so the empty
array clears the provider's entry.

Do not delete this file. Without it, cold builds fail again.

## Removed: `motivated-rejoicing`

Deleted 2026-08-04. It was a cron service running result updates:

```
builder        RAILPACK
buildCommand   pip install -r requirements.txt
startCommand   python manage.py update_results --hours-after 3
cronSchedule   0 */3 * * *
restartPolicy  NEVER
variables      DATABASE_URL, SPORTMONKS_API_TOKEN
```

It was strictly redundant: the scheduler calls the same command hourly with
`max=100`, and `--hours-after` already defaults to 3 — a superset in both
frequency and coverage. It also could not settle claims, which `run_scheduler`
does immediately afterwards. It had no volumes, no domains, no inbound
references, and zero successful deployments in its entire history (it had been
failing the mise attestation error described above).

To recreate it, use the block above **plus**
`MISE_PYTHON_GITHUB_ATTESTATIONS=false`, without which it cannot build. Doing so
would reintroduce a second scheduled result-update owner; prefer leaving
`smartbet` as the sole owner.

## Known CLI limitation

`railway environment edit --service-config <SERVICE> <PATH> <VALUE>` appears in
`--help` on CLI 4.58.0 and 5.30.4 but is **inert** — it returns

```json
{"committed":false,"message":"No changes to apply","staged":false}
```

for every dot-path, including creating a variable that does not exist.
`railway service scale <region>=0` likewise does not persist. Build commands,
cron schedules and replica counts must be changed in the dashboard.

`railway variable set` works normally, and by default triggers a redeploy — pass
`--skip-deploys` to avoid one.

`railway logs` takes the deployment ID **positionally**; `-d` and `-b` are
boolean flags selecting deploy or build logs, not ID options:

```bash
railway logs <DEPLOYMENT_ID> --build --lines 200 -s <SERVICE> -e production
```

## Recovery and rollback

**Health check, no writes.** `SchedulerHeartbeat` key `scheduler` — read it with
`filter().first()`, never `get_or_create()`, or the act of checking creates the
row. Expect `status=success`, `health()=healthy`, `last_run_completed_at` within
the last ~60 min.

**If cycles have stopped:**

1. `railway service status --service smartbet -e production` — is it Online?
2. `railway logs <deployment-id> -d -s smartbet -e production` — look for
   `⏰ Starting scheduled tasks`, the four `▶️ Running …` lines, `completed in`,
   and `Waiting 60 minutes until next run...`. More than one
   `Starting Container` means it is restart-looping.
3. `railway service restart --service smartbet -e production` restores the loop
   without rebuilding.

**If a build fails**, check in this order — these are the two failures that
caused the ~10-week outage:

- `apt-get install -y libpq5` → `railpack.json` is missing or reverted.
- `No GitHub artifact attestations` → `MISE_PYTHON_GITHUB_ATTESTATIONS` is unset.

**Rollback.** Railway keeps the previous image serving when a build fails, so a
failed deploy is not an outage. To go back deliberately, redeploy the last known
good deployment from the dashboard. Do not roll back past `199f2f0` on
`smartbet` — earlier commits lack `railpack.json` and cannot build cold.

**Credential rotation.** Update `SPORTMONKS_API_TOKEN` on `smartbet`,
`smartbet-backend` and `smartbet-frontend`. A running container holds the value
it started with, so each service must redeploy or restart to pick up a new one.
To verify without exposing the value, compare
`printf %s "$SPORTMONKS_API_TOKEN" | sha256sum` inside each container against
the stored config, then confirm the provider accepts it — pass the token as the
`api_token` **query parameter** (the form the app uses); an invalid token
returns `401 Invalid token provided`.
