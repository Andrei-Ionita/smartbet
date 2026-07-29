# Deployment runbook — verified pricing record

**Status:** PREPARED, **NOT EXECUTED**. Blocked on founder approval of
`docs/audit/public-copy-proposal-2026-07-29.md`.

**Goal:** deploy the corrected odds pipeline, establish a validated cutoff, and
begin accumulating a verified pricing record.

**Explicitly out of scope:** gem-selector ranking, `/gems`, public gem cards,
any public performance claim.

---

## Preconditions

| # | Check | Command / expectation |
|---|---|---|
| P1 | Copy approved | Founder sign-off on the copy proposal |
| P2 | Clean tree, migration committed | `git status --short` empty; `0026_*.py` present |
| P3 | Backend tests pass | `python manage.py test core` → 120 passed |
| P4 | Frontend tests pass | `npm test` → 59 passed |
| P5 | Typecheck clean | `npx tsc --noEmit` → exit 0 |

> **Note on the local build.** `npm run build` fails on this Windows/OneDrive
> workstation at the standalone file-copy step (`UNKNOWN: copyfile` on
> `font-data.json`) — an environment fault, not a code fault: compilation
> completes and `.next/BUILD_ID` is emitted. Railway builds in Linux Docker.
> **Step 4 is therefore the first real build verification and is a hard gate.**

## Sequence

### Phase A — deploy the code

1. **Confirm clean git status and the committed migration.**
   `git status --short` → empty. `ls core/migrations/0026_*.py` → present.
2. **Run the full suite.** Backend `python manage.py test core`; frontend
   `npm test` and `npx tsc --noEmit`. All green, no skips.
3. **Deploy to Railway** (push to `master`; backend and frontend auto-deploy).
   **Do not set `PRICING_INTEGRITY_CUTOFF` yet** — unset means far-future, so
   nothing is verified and no claim can be made while the build settles.
4. **Confirm the Linux production build succeeds.** Railway build logs show a
   successful `next build` for the frontend and a healthy backend release.
   **STOP if this fails** — everything downstream assumes a deployed build.

### Phase B — migrate and verify schema

5. **Apply migration 0026.** `railway run python manage.py migrate core`
   Expect: `Applying core.0026_predictionlog_odds_provenance_and_more... OK`.
6. **Verify the schema.** Read-only:
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name='core_predictionlog'
     AND column_name IN ('odds_provenance','prediction_run_id','pricing_integrity_status');
   SELECT to_regclass('core_publishedclaim');
   ```
   Expect 3 columns and a non-null table reference.

### Phase C — validate the corrected pipeline on real data

7. **Process one controlled live fixture.** Trigger a single recommendations
   run and let it log. Pick one `over_under_2.5` row it wrote.
8. **Inspect the stored selection.**
   ```sql
   SELECT fixture_id, market_type, predicted_outcome, odds,
          odds_provenance, prediction_run_id, pricing_integrity_status
   FROM core_predictionlog WHERE prediction_run_id = '<run id>' LIMIT 5;
   ```
   Expect `odds_market_id` ∈ {80, 7}, `odds_line = 2.5`, `odds_label = 'Over'`
   (or `'Under'`), a bookmaker id **and** name, a capture timestamp, and
   `odds_selection_policy = 'lower_median_v1'`.
9. **Manually compare against the source payload.** Fetch
   `/v3/football/fixtures/<id>?include=odds;odds.bookmaker`, filter to
   `market_id ∈ {80,7} AND total = 2.5 AND label = <side>`, sort the prices, and
   confirm the stored odds equal the **lower median**. **This is the decisive
   check** — it is the exact comparison that exposed the original defect.
   **STOP if it does not match.**

### Phase D — set the cutoff

10. **Set `PRICING_INTEGRITY_CUTOFF`** to the UTC timestamp validated in step 9,
    as ISO-8601 (e.g. `2026-07-30T14:05:00+00:00`). Railway variable on the
    **backend** service.
    *The cutoff is environment-configured, so this needs no code commit.*
11. **Restart the backend** so the value is read (Railway restarts on variable
    change; confirm the new release is live).

### Phase E — classify

12. **Dry run.** `railway run python manage.py classify_pricing_integrity --dry-run`
13. **Review projections.** Expect approximately:
    | status | expected |
    |---|---|
    | `legacy_unverified` | ~760 |
    | `audit_excluded` | ~35 |
    | `verified` | 0, plus any row written after the cutoff in step 7 |
    **STOP if `verified` includes anything logged before the cutoff.**
14. **Run for real.** `railway run python manage.py classify_pricing_integrity`
15. **Record final counts** from the command output.

### Phase F — verify public surfaces

16. **Verify every public surface** — run the smoke tests below.
17. **Confirm no old ROI is visible** anywhere (see S6).
18. **Confirm the mutable proof fallback is gone** (see S11).
19. **Confirm new rows can become verified** (see S12).
20. **Record the deployment** in `docs/audit/deployment-log-verified-pricing.md`:
    deployment timestamp, cutoff, migration result, counts by status, smoke
    results, and who approved the copy.

## Rollback

| Failure point | Action |
|---|---|
| Step 4 (build) | Revert the deploy commit; nothing else has changed. |
| Step 5 (migration) | Migration is purely additive; roll back the release and `migrate core 0025`. |
| Step 9 (wrong price) | **Do not proceed.** Leave `PRICING_INTEGRITY_CUTOFF` unset — every row stays `legacy_unverified` and no claim is published. Diagnose, fix, redeploy. |
| Step 14 (bad classification) | Statuses are recomputable: correct the cutoff and re-run the command. It is idempotent and touches only the status column. |

**Safety property:** with `PRICING_INTEGRITY_CUTOFF` unset, the system publishes
nothing and claims nothing. Every failure mode above degrades to "empty record",
never to "false claim".

---

## Production smoke tests

Run after step 15. Each has an explicit pass condition.

| # | Test | Pass condition |
|---|---|---|
| **S1** | Railway build | Frontend and backend releases healthy; `/api/health/` 200 |
| **S2** | Correct market selected | A known full-match O/U 2.5 row has `odds_market_id ∈ {80,7}`, `odds_line = 2.5`, label matching the pick; **never** market 53/28/37/86/105/107 |
| **S3** | Order independence | Re-run the same fixture; stored odds and bookmaker id are unchanged |
| **S4** | Provenance complete | `missing_provenance_fields(prov, market_type)` returns `[]` for every row written after the cutoff |
| **S5** | Missing odds → non-verified | A fixture with no exact-market quote yields no recommendation, or a row that is **not** `verified` |
| **S6** | Legacy excluded | `/api/transparency/dashboard/` → `roi_simulation.total_bets` counts **only** post-cutoff verified rows; the old +10.61% appears nowhere |
| **S7** | Quarantined excluded | The 8 `is_audit_excluded` rows appear in no public aggregate |
| **S8** | Cross-surface consistency | A verified resolved row yields the **same** counts on dashboard, accuracy, leagues and proof record |
| **S9** | Leagues deduplicated | `/api/transparency/leagues/` → `total_leagues` equals the distinct league count (was 241 for 25) |
| **S10** | Monitoring aligned | `/api/predictions/monitoring/` money figures use verified rows only; each row carries `pricing_integrity_status` |
| **S11** | No mutable public proof | `/api/proof/<id>/` for a fixture with no claim → `published: false`, **no `pick` key**; `/preview/` → 401/403 anonymously |
| **S12** | New rows can verify | A post-cutoff row with complete provenance classifies `verified`; confirms the record can actually start |
| **S13** | Zero-sample display | `/track-record` shows "No verified results yet", **not** a green `+0%` |

**S6, S11 and S13 are the credibility-critical three.** If any fails, the
deployment has not achieved its purpose and public surfaces should be
considered unsafe to promote.

## Post-deployment state (expected)

- Public ROI: **no verified results yet** (correct, not a bug).
- Legacy rows: visible, preserved, excluded from price-dependent reporting.
- Proof URLs: every one is `unpublished` until `PublishedClaim` creation ships.
- Verified record: accumulates as post-cutoff picks settle.

## Remaining blockers after this deployment

1. **Nothing creates `PublishedClaim`** — the publication path lives in the
   unbuilt `/gems` selector. Until then every proof URL is `unpublished`.
2. **Gem selector not implemented** and must be recalibrated on clean data; its
   evidence cells were built on contaminated prices.
3. **First verified results are weeks away** — fixture volume is in the
   pre-season lull; a meaningful sample needs roughly 40+ settled picks.
