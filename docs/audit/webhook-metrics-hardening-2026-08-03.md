# Final cleanup — marketing webhook and metrics endpoint

**Date:** 2026-08-03

**Unchanged:** prediction logic, recommendation ingestion, snapshots, claim
publication, settlement, commercial mode, bankroll behaviour, gem ranking.

---

## 1. `marketing_webhook` audit

* **Route/view:** `POST /api/marketing/webhook/` → `core.api_views.marketing_webhook`
* **Expected caller:** Brevo. The whole integration is documented *Optional* in
  `env.example` and gated by `MARKETING_SYNC_ENABLED=False` (default).
* **Auth (before):** compared `X-Marketing-Webhook-Secret` to
  `MARKETING_WEBHOOK_SECRET` **only when a secret was configured**.

### It was unset in production

Probed 2026-08-03: a request with **no** secret and a request with a **wrong**
secret returned byte-identical `404 Subscriber not found`. Both had passed the
auth check and reached subscriber lookup. The endpoint was fully public.

### Side effects reachable by anyone who knew a subscriber's email

| Action | Effect |
|---|---|
| `unsubscribe` | `is_active=False`, status `unsubscribed` |
| `reactivate` | `is_active=True` + 2 MarketingEvent rows |
| `paid_converted` | **`email_platform_status='paid'`** + MarketingEvent |
| `weekly_picks_sent` / `email_clicked` | MarketingEvent row |

No prediction, money or verified-record impact — but arbitrary mass
unsubscription and false "paid" marking were both possible.

### Error handling (before)

`print(f"Marketing webhook error: {e}")` and a free-text 500 body. The secret
was never echoed, but exception text went to stdout rather than the logger.

---

## 2. Treatment: secured, fails closed

Kept — `MARKETING_SYNC_ENABLED` can be turned on later and the route is Brevo's
only inbound path. Now:

* **Absent secret ⇒ every request rejected**, no side effects, and a concise
  `logger.error` server-side.
* Wrong secret ⇒ same opaque response, so a caller **cannot tell whether the
  secret is configured**.
* `hmac.compare_digest` — response timing no longer leaks length or prefix.
* `logger.exception` instead of `print`; 500 body is a controlled code.

```json
{"code": "webhook_unauthorized",
 "detail": "The webhook request was not authorized."}
```

**Two existing tests were passing BECAUSE of the fail-open behaviour** — they
posted with no secret at all. Both now authenticate.

### If Brevo is live

It has never been able to authenticate (the secret was never set), so any
webhooks it sent were succeeding *by accident*. To (re)enable: generate a
secret outside source control, set `MARKETING_WEBHOOK_SECRET` on the backend
and the same value as a custom header in Brevo's webhook config.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 3. `/api/metrics` — removed

* **Purpose:** performance dashboard feed.
* **Callers:** only `app/components/PerformanceDashboard.tsx`, which is **not
  mounted anywhere**.
* **What it reset:** nothing real. `performanceMonitor` is a stub —
  `getDetailedReport()` returns hard-coded zeros, `reset()` only `console.log`s.
* **Verified live before removal:** anonymous `DELETE` returned **200**.

Removed the route and the orphaned component. GET went too: serving fabricated
zeros as "performance metrics" is inconsistent with the standard applied to the
public record.

---

## 4. Write-route inventory (re-run)

16 state-changing endpoints:

| Protection | Endpoints |
|---|---|
| `IsAdminUser` | `publish_snapshot_view`, `publish_claim_view` |
| `IsAuthenticated` | `logout` |
| HMAC | `log_recommendations` |
| Secret header, constant-time | `marketing_webhook` |
| `AllowAny`, session-scoped | `create_bankroll`, `update_bankroll`, `record_bet`, `settle_bet`, `get_stake_recommendation` |
| `AllowAny`, credential flows | `register`, `login`, `refresh_token` |
| `AllowAny` + commercial-mode/INTERNAL_API_SECRET | `upgrade_tier` |
| **Intentionally public** | `subscribe_email`, `track_marketing_event` |

**No endpoint remains where a missing environment secret silently enables
anonymous access.**

`core/tests_webhook_hardening.py` statically scans every view module for a
secret comparison guarded on the secret existing, and fails if one reappears.

---

## 5. Verification

| Check | Result |
|---|---|
| Webhook, no secret | **401** `webhook_unauthorized` |
| Webhook, invalid secret | **401**, byte-identical |
| Unsubscribe attempt on a real address, no secret | **401**, no side effect |
| `DELETE /api/metrics` | **404** (was 200) |
| `GET /api/metrics` | **404** |
| `log-recommendations` unsigned | 401 |
| `scheduler-health`, `proof/queue` anonymous | 401 |
| 4 previously-removed endpoints | 404 |
| Public transparency reads | 200 |
| Public `GET /api/recommendations` | 200, **rows 320 → 320, newest unchanged** |
| Checkout | 403 `payments_disabled` |
| Cardiff `20adfb1e…` | published, `integrity_ok: true`, `superseded: false`, odds 1.8, hash `0c1aa8c6b2d066a3` |
| Rows | verified 5, legacy 307, audit_excluded 8 |
| Backend tests | 337 pass, 2 pre-existing loader errors (339 ran) |
| Frontend tests | 193 pass |

---

## Remaining unauthenticated write surfaces

Two, both intentional and inventoried as `public_write`:

* `POST /api/subscribe/` — newsletter signup; a public form by definition.
* `POST /api/marketing/events/` — its telemetry.

Blast radius is `EmailSubscriber` / `MarketingEvent` rows only: spammable, no
prediction, money or verified-record impact. Rate limiting would be the
proportionate next step, not authentication.
