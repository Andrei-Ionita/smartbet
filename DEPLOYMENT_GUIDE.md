# BetGlitch Railway deployment

Railway is the only production hosting and deployment platform for BetGlitch.
The source project is `Andrei-Ionita/smartbet`; every application service tracks
the `master` branch.

The detailed, non-secret production topology and recovery instructions live in
[`docs/RAILWAY_PRODUCTION_ARCHITECTURE.md`](docs/RAILWAY_PRODUCTION_ARCHITECTURE.md).

## Production services

| Railway service | Source root | Role |
|---|---|---|
| `smartbet` | repository root | Scheduler and sole owner of ingestion, result updates and claim settlement |
| `smartbet-backend` | repository root | Django API at `api.betglitch.com` |
| `smartbet-frontend` | `/smartbet-frontend` | Next.js site at `www.betglitch.com` |
| PostgreSQL services | Railway images | Production databases |

## Release procedure

1. Run the backend and frontend test suites.
2. Run `npx tsc --noEmit` in `smartbet-frontend`.
3. Merge the reviewed release into `master`.
4. Railway builds all three application services from the new `master` commit.
5. Confirm every deployment reports `SUCCESS` before treating the release as live.
6. Smoke-test `https://www.betglitch.com/`,
   `https://www.betglitch.com/api/recommendations/`, and
   `https://api.betglitch.com/api/health/`.
7. Confirm the scheduler heartbeat and inspect each stage in the scheduler logs.

## Build configuration

- The frontend uses `smartbet-frontend/Dockerfile` and Next.js standalone output.
- The scheduler and backend use the root Python project and `railpack.json`.
- Do not delete `railpack.json`; its empty runtime apt-package override prevents
  known cold-build failures.
- The scheduler build command is `chmod +x ./build.sh && sh ./build.sh`.
- The scheduler start command is
  `python manage.py run_scheduler --interval 60 --run-now`.

## Required configuration

Never commit secret values. Variable names and service ownership are documented
in `docs/RAILWAY_PRODUCTION_ARCHITECTURE.md`. In particular, all application
services that call SportMonks must receive the same current API token, and the
Python services require `MISE_PYTHON_GITHUB_ATTESTATIONS=false`.

## Rollback

Railway retains the previous successful image when a build fails. For an
intentional rollback, redeploy the last known-good deployment in the Railway
dashboard. Verify the public site, API health endpoint and scheduler stages
again after rollback.
