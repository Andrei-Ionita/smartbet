# Phase 6 — Public copy proposal (NOT PUBLISHED — awaiting founder approval)

**Status:** DRAFT. Nothing in this file has been deployed. Per the execution
boundaries, the corrected copy is proposed here for approval rather than
published automatically.

**Why this is needed:** every public claim below is either contradicted by the
code or based on the contaminated historical record
(`docs/audit/gem-selector-diagnostics-2026-07-29.md`).

---

## 1. Claims that must change

Source: `core/transparency_views.py` lines 37–43 and 100 (the `methodology`
block returned by `/api/transparency/dashboard/`, public and unauthenticated).

| # | Current live text | Problem | Proposed replacement |
|---|---|---|---|
| 1 | "Minimum 60% confidence AND positive Expected Value" | **False.** `over_under_2.5` ships at 0.55; 54 published rows sit in 0.55–0.60. | "Minimum 55% confidence for Over/Under 2.5 and 60% for all other markets, plus positive expected value at the recorded price." |
| 2 | "Historical data never deleted or edited" | **False as written.** The pipeline overwrote odds, confidence and the selection on every re-run, and there is no `updated_at`, so past edits are unprovable. | "Published claims are immutable: each one is snapshotted with a SHA-256 hash when it goes public and is never rewritten. Our live model keeps improving; the claim you were shown does not change. Nothing is ever deleted." |
| 3 | "Third-party API - results cannot be manipulated" | **Misleading.** True of *results*; the *prices* were mis-captured until 2026-07-29. | "Match results come from a third-party API and cannot be edited by us. Prices are recorded with their exact market, line, bookmaker and capture time, so any quote we publish can be independently checked." |
| 4 | "All predictions logged BEFORE matches start" | 99.4% true — 2 of 315 rows were logged after kickoff. | "Every published pick is timestamped before kickoff." *(True once publication requires a pre-kickoff `PublishedClaim`; the two late rows are legacy and excluded.)* |
| 5 | Published ROI (+9.6% / +10.6%) | **False.** Defensible figure was −4.90%; the positive number came from mis-captured prices and quarantined rows. | Remove entirely until verified results accumulate. Replace with the disclosure in §2. |
| 6 | "We show both wins and losses - complete transparency" | True, and worth keeping. | Keep unchanged. |

Also update line 100 (`'criteria': 'Minimum 60% confidence + Positive Expected
Value'`) to match #1 — it is a second copy of the same claim.

## 2. Proposed disclosure for the record restart

To appear wherever ROI or the track record is shown.

> **Our verified pricing record begins 29 July 2026.**
> Before that date a fault in how we captured bookmaker odds meant some picks
> were recorded against the wrong betting market. Match results were never
> affected, but any profit figure calculated from those prices is unreliable.
>
> Historical predictions have not been deleted — you can still see every one of
> them — but they are excluded from profit and ROI reporting, because their
> original prices cannot be reconstructed to a standard we are willing to
> publish. We chose to restart the record rather than estimate the missing
> prices.

**Shorter variant** for compact surfaces (cards, footers):

> Verified pricing record begins 29 July 2026. Earlier predictions are shown but
> excluded from ROI — their original prices could not be verified.

**Empty-state copy** while no verified results have settled yet:

> No verified results yet. Our pricing record restarted on 29 July 2026 and
> fills in as matches settle. We would rather show you nothing than a number we
> cannot stand behind.

## 3. Language rules going forward

**Banned:** guaranteed, lock, banker, sure bet, easy money, "the market is
wrong" stated as fact, any profit promise, win-only framing, and any ROI figure
not computed from `public_universe.priced_qs()`.

**Required:** model probability always presented alongside the bookmaker's
implied probability, never as a bare probability — `confidence` is a
provider-derived score and is **not** empirically calibrated (audit finding F3).

## 4. Claims verified as accurate (no change needed)

- "Real match results from SportMonks API" — grading verified correct across all
  13 audited longshots.
- "Top 10 best value bets updated daily" — confirmed in `route.ts`.
- "We track only what we recommend to you" — confirmed; `is_recommended` gate.
- No user-count or guaranteed-profit claims were found on any audited surface.

## 5. Sequencing

This copy must ship **with or before** the corrected dashboard. Publishing the
new (empty) record without the disclosure would look like a bug or a cover-up;
publishing the disclosure without the fix would leave the false ROI on screen.

The founder should approve or edit the wording in §2 before any of it goes live.
