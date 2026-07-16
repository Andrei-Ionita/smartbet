# BetGlitch Audit Artifacts

## What lives here

- `roi-audit-YYYY-MM-DD.md` — human-readable audit reports.
- `roi-audit-YYYY-MM-DD.py` — reproducible analysis scripts. Idempotent; re-run on a fresh snapshot to regenerate a report.
- `test_roi_audit_helpers.py` — pytest suite for the pure helpers (bootstrap CI, bucketizer).
- `snapshot-YYYY-MM-DD.sqlite` — frozen data snapshots (git-ignored; see below).

## Regenerating a snapshot

Requires Railway CLI logged in with production access. Snapshot lives outside git; anyone with prod access can rebuild:

```bash
# 1. Dump prediction_log table from Railway Postgres
railway connect Postgres <<'SQL' > /tmp/prediction_log.sql
COPY (SELECT * FROM core_predictionlog) TO STDOUT WITH CSV HEADER;
SQL

# 2. Alternative: use pg_dump for full schema fidelity
railway run --service smartbet-backend \
  bash -c 'pg_dump "$DATABASE_URL" -t core_predictionlog --data-only --column-inserts' \
  > /tmp/prediction_log_inserts.sql

# 3. Load into local sqlite (see the load_snapshot helper in the audit script)
python docs/audit/roi-audit-YYYY-MM-DD.py --build-snapshot /tmp/prediction_log_inserts.sql \
  --out docs/audit/snapshot-YYYY-MM-DD.sqlite
```

## Running an audit

```bash
python docs/audit/roi-audit-YYYY-MM-DD.py \
  --snapshot docs/audit/snapshot-YYYY-MM-DD.sqlite \
  --out docs/audit/roi-audit-YYYY-MM-DD.md
```
