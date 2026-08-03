# Live production verification pass

**Date:** 2026-08-03
**Target:** https://betglitch.com (production)
**Method:** driving the deployed site, not reading source.

Follows `first-impression-ux-2026-07-31.md`. That phase shipped the changes;
this one checked whether they actually hold up in production, and found seven
things that source review had not.

**Untouched, as required:** prediction logic, odds selection, pricing-integrity
rules, snapshots, published claims, settlement, verified-record definitions,
commercial-mode architecture, gem ranking.

---

## How real breakpoint testing was finally done

The previous phase reported that viewport testing was impossible:
`resize_window` returns success but the viewport stays pinned (measured 1536px;
`outerWidth` reads 0, so the tab is not in a resizable OS window).

**Resolution:** render each page in a same-origin iframe sized to exact CSS
pixels. Media queries, layout and `100vh` all evaluate against the iframe's own
viewport, so the breakpoints are genuinely exercised. Every measurement below
was taken with the frame's own `innerWidth` confirmed, e.g. `innerWidth: 320`,
`matchMedia('(min-width:768px)').matches === false`.

Confirmed widths: **320, 360, 375, 390, 768, 1024, 1120, 1280, 1440**.

Not covered: touch input, real device DPR, iOS/Android browser chrome. This is
correct CSS-viewport testing, not device testing.

---

## Findings

### 1. Legacy rows published price-dependent performance (highest impact)

Every legacy row on `/track-record` rendered:

* **expected value** in green with a leading `+` (e.g. `+13.9%`)
* **profit/loss** as a green/red dollar figure (e.g. `+$10.10`)

Both are computed *from* the recorded price. A legacy row's price could not be
verified against the exact market and bookmaker — that is the whole reason it
is excluded from the record. Publishing figures derived from it contradicted
the `LEGACY — NOT IN VERIFIED RECORD` badge sitting in the same row.

Captured before the fix:

| badge | model score | EV | P/L |
|---|---|---|---|
| LEGACY — NOT IN VERIFIED RECORD | 62.4% | +6.0% | +$7.00 |
| LEGACY — NOT IN VERIFIED RECORD | 56.7% | +13.9% | +$10.10 |

Now both read **Not verified**, with supporting copy. Match, selection and
actual outcome remain visible — those do not depend on the price. Verified
live: 610 `Not verified` cells across 305 rows.

Aggregates were already correct (`total_bets: 0`, `has_verified_results:
false`) — the defect was per-row rendering only.

### 2. An empty record rendered as 0% performance

`/track-record` showed a large **0%** overall accuracy, a **0%** win rate, and
three 0% tiles for home/draw/away. Zero settled picks is "no results yet", not
measured failure. ROI already had a zero-state branch; accuracy, win rate and
the breakdown did not.

### 3. A settlement trigger was exposed to anonymous visitors

The public "Update Results" button POSTed to
`/api/transparency/update-results/`, which is **unauthenticated**, runs
`ResultUpdaterService().update_all_pending_results(max_predictions=50)` against
production, calls the SportMonks API, and returns `str(e)` to the client on
error. Reported through a blocking `alert()`.

The button is removed. **The endpoint itself is still open** — see
Recommendations; changing its auth is settlement behaviour and out of scope
for this pass.

### 4. The desktop nav overflowed every width below 1280px

The bar switched on at `md` (768px), but the full row — logo, five links, EN/RO
toggle, two auth buttons — needs **~1215px in Romanian**, where
"Autentificare"/"Înregistrare" are far longer than "Login"/"Sign Up".

Measured: at 768px the document was **1199px wide in a 753px viewport**. Also
overflowed at 1024 and 1120. Moved to `xl` with tighter spacing.

### 5. Romanian broke /track-record at 320px

`Actualizează Rezultate` would not wrap, forcing the page to 350px against a
305px viewport. Fixed by removing that button (see 3).

### 6. /about overflowed at 320px

A three-item `flex` stat row with `gap-6` and no `flex-wrap` forced the page to
410px. Added wrapping.

### 7. The age gate was not a dialog

It fronts every page, so it is the first thing a screen-reader user meets:

* no `role="dialog"`, no `aria-modal`, no accessible name
* focus never entered it — `document.activeElement` stayed `BODY`
* Tab escaped to the page behind
* its `<h1>` competed with each page's own `<h1>` (every page reported two)
* consent checkboxes measured **13×20px** (`w-5` squeezed by flex)

Now a labelled modal, focus moved in, Tab trapped, `h2`, checkboxes 24×24.
**Deliberately no Escape handler** — a legal acknowledgement must not be
dismissible.

### Also fixed

* `<html lang>` stayed `"en"` while rendering Romanian (WCAG 3.1.1).
* Escape did not close the mobile menu; now closes and restores focus.
* No `autoComplete` on any auth field — password managers could not fill or
  offer to save. Added `username` / `email` / `new-password` /
  `current-password`.
* Register validation errors rendered in a banner above the form, off screen on
  a phone. Now beside the field, with `aria-invalid`, `aria-describedby` and
  focus moved. Length is checked before match, so a short password is not first
  reported as a mismatch. Login's error region gained `role="alert"`.
* Unlabelled controls: six track-record filters, Explore search + league, three
  email inputs.
* Two footer links pointed at a bare fragment — dead ends on every page.
* Sub-44px targets: footer icon (20×20), mobile auth links (38), register/login
  inputs (42), track-record filters (32–36), share-proof buttons (42),
  back-to-home links (17).
* `/explore` and `/about` metadata still described the old product in title,
  description and OG.

---

## Test configuration: production fail-closed vs deterministic tests

Production and tests need **opposite** things from `PRICING_INTEGRITY_CUTOFF`.

**Production must fail closed.** Unset ⇒ far-future sentinel ⇒ every prediction
classifies `legacy_unverified` and nothing publishes as verified. An
unconfigured deployment under-claims. This is a safety property.
**There is still no default in production and that must not change.**

**Tests must be deterministic.** The same fail-closed default made ~54
claim/pricing tests fail for a reason unrelated to what they assert, purely
because the variable was missing from a developer's `.env`. A suite that is red
for an unrelated reason trains people to ignore red.

Resolution — `smartbet/settings.py`:

```python
TEST_PRICING_INTEGRITY_CUTOFF = '2026-07-30T08:32:00+00:00'
RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.modules or ...
if RUNNING_TESTS:
    os.environ.setdefault('PRICING_INTEGRITY_CUTOFF', TEST_PRICING_INTEGRITY_CUTOFF)
```

`setdefault`, not assignment, so CI or a developer investigating a specific
cutoff still wins. `core/tests_pricing_integrity_config.py` pins all of it:
tests run configured; the value is the centralised one; unset still yields year
2999; a malformed value raises `ImproperlyConfigured` naming the variable; an
explicit value overrides the test default.

Result: `python manage.py test core` now passes with the variable unset —
**241 ran, 239 pass, 2 pre-existing loader errors** (`test_fixtures_api`,
`test_suggestion_engine` — management commands the test loader picks up by
name, unrelated to this work).

---

## Verification results

| Check | Result |
|---|---|
| Horizontal overflow, 9 widths × 11 surfaces, EN + RO | none |
| Banned phrases, 11 pages × 15 phrases | 0 |
| Legacy price-dependent figures public | 0 (610 `Not verified`) |
| Age gate dialog semantics + focus | correct |
| `<html lang>` follows EN/RO | correct |
| Checkout / upgrade-tier | 403 `payments_disabled` |
| `/pricing` | beta page; 0 sitemap entries |
| Cardiff claim `20adfb1e…` | `integrity_ok: true`, `superseded: false`, odds `1.8` |
| Public performance | `total_bets: 0`, `has_verified_results: false` |
| Frontend tests | 180 pass (was 145) |
| Backend tests | 239 pass, 2 pre-existing loader errors |

---

## Recommendations (not actioned — outside this pass)

1. **Authenticate `/api/transparency/update-results/`.** Still an open,
   unauthenticated POST that runs settlement and leaks `str(e)`. The public
   caller is gone, but the endpoint is reachable directly.
2. **Expose a scheduler heartbeat.** There is no endpoint reporting worker
   liveness, so the `worker: run_scheduler --interval 60` process cannot be
   confirmed alive from outside. Evidence is consistent with it running (five
   verified pending picks logged across four separate days to 2026-08-02), but
   that is inference, not confirmation.
3. Desktop nav links are 36px tall — fine for pointer input, below the 44px
   touch floor. Only reachable at ≥1280px where touch is unlikely.
