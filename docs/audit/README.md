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

# 3. Load into local sqlite. First export the table as CSV via Railway:
railway run --service Postgres python -c "
import os, csv, sys, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_PUBLIC_URL'])
cur = conn.cursor()
cur.execute('SELECT * FROM core_predictionlog')
cols = [d[0] for d in cur.description]
w = csv.writer(sys.stdout, quoting=csv.QUOTE_MINIMAL)
w.writerow(cols)
for row in cur:
    w.writerow(row)
" > /tmp/prediction_log.csv

# Then convert CSV to sqlite:
python -c "
import sqlite3, csv
conn = sqlite3.connect('docs/audit/snapshot-YYYY-MM-DD.sqlite')
cur = conn.cursor()
with open('/tmp/prediction_log.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f); cols = next(reader)
    col_defs = ', '.join(f'\"{c}\" TEXT' for c in cols)
    cur.execute('CREATE TABLE prediction_log (' + col_defs + ')')
    placeholders = ','.join('?' * len(cols))
    cur.executemany('INSERT INTO prediction_log VALUES (' + placeholders + ')', reader)
conn.commit()
print('rows loaded:', cur.execute('SELECT COUNT(*) FROM prediction_log').fetchone()[0])
"
rm /tmp/prediction_log.csv
```

## Running an audit

```bash
python docs/audit/roi-audit-YYYY-MM-DD.py \
  --snapshot docs/audit/snapshot-YYYY-MM-DD.sqlite \
  --out docs/audit/roi-audit-YYYY-MM-DD.md
```
