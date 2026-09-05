# Market selection portfolio v5

## Product contract

The scheduler evaluates every stored, currently observed side and line for twelve market families: 1X2, BTTS, totals 1.5/2.5/3.5, double chance, correct score, half-time result, half-time/full-time, Asian handicap, Asian goal lines and team totals. A market needs its required probability and price evidence to produce a selection. First-team-to-score, corners, cards and player props are explicitly unavailable until their model/result contracts are implemented. Correct-score comparisons require the residual outcomes to be priced too; incomplete books do not produce a fabricated no-margin baseline.

`/markets` displays up to five per market. The homepage displays up to five different fixtures from that same published set. There is no diversity quota. Strategy explanation pages use the same market board. Every public card has an existing immutable `PublicSelection` receipt before it is served.

## Qualification and ranking

Policy and its hash live in `core/services/selection_portfolio.py`. These are initial research rules, not a demonstrated profit-maximizing strategy. A policy change under an already published version is rejected; change the version explicitly.

- Kickoff 1–72 hours away; actual quote timestamp no older than two hours.
- At least three bookmakers, exact market/line identifiers, at most 20% price dispersion.
- Decimal odds 1.30–12 (correct score up to 30).
- Complete probability vectors, complete price vectors, valid mass and matched selection identity. Double chance uses a complete 1X2 book to derive overlapping probabilities.
- Model EV of at least 3%; estimates above 50% are held out as potential data/model anomalies.
- Direct markets rank by a market-shrunk empirical probability lower bound multiplied by the current odds, minus one. Calibration uses all available outcomes from observations since 26 August, one pre-match observation per fixture/outcome, and only results captured before the current decision. Missing market comparisons exclude a candidate.
- Asian and team-total markets use return bounds from the captured score distribution, with at least 97.5% probability mass and a 10-percentage-point EV stress deduction. This stress deduction is an unvalidated policy assumption, **not** a statistical confidence interval. It is shown as such on the card. Push/half-win/half-loss payouts remain explicit; `(EV + 1) / odds` is never shown as their win probability.
- Conservative return orders candidates, then bookmaker coverage, dispersion and kickoff. Each market gets at most one side/line per fixture. Homepage gets at most one selection per fixture.

Positive raw model EV can qualify a clearly labeled research selection even when conservative EV is negative. Both estimates are displayed. A `price_edge` label additionally requires 30 local calibration observations and positive conservative EV. Neither label claims proven profitability. A 60% win-rate target is not applied to every market.

Context includes captured lineup status, form and absence availability. A known unpredictable fixture is excluded. Missing context is disclosed. No untested multiplier is added for facts that may already be included in the model. xG, player strength, weather, referee effects and injury-adjusted forecasts are not newly modeled by this change; they require separately tested features and verified subscription coverage.

## Evidence and results

One `PublicSelection` per version/market/fixture. Later scans cannot switch its side/line or rewrite its odds. Current quotes and current EV are labeled separately from original receipt terms. Disappearing from a live board never removes a published result.

`SelectionBoard` atomically publishes all market IDs, homepage IDs, current evidence and the policy hash. Its hash is checked on reads. `HomepageSelectionAppearance` references the same receipt as the market entry; the overall record never counts a homepage appearance as another stake. A fixture may have correlated selections in different markets; that is disclosed in Results.

Results use only this portfolio version. Every individual pending/settled row is visible immediately. Headline and per-market ROI/accuracy summaries require 30 settled rows in the relevant cohort. Thirty is a display milestone, not validation of an edge. ROI uses a one-unit flat stake, correct split payouts, and excludes void/cancelled stakes. Binary accuracy is withheld for cohorts containing partial settlements or pushes.

Older receipts and research observations remain intact. The old public-performance promotion flag remains false; the new Results component is a dedicated view of this version. Gems keep their independent, stricter publication rules and record. The portfolio does not promote research selections into Gems.

## Cost and freshness

Visitor GETs read stored boards and never run a scan. The existing evidence sweep writes one replaceable `portfolio_input` cache containing its latest candidates. This allows unchanged-but-rechecked odds to remain fresh without appending thousands of duplicate observations. Published boards freeze the quote evidence they used. Missing/expired input causes the publication command to fail visibly; no old candidate set is treated as a fresh successful scan.

The evidence endpoint follows pagination for subscribed leagues and fixture pages, without a silent first-50-fixtures or first-30-leagues cutoff. Requests remain scoped to subscription coverage; additional pages can increase scan time and API requests. No new paid plan or service is enabled. The current scan still handles a failed league by omitting that league; feed-wide success is not a guarantee of exhaustive provider coverage during outages.

## Deployment and verification

1. Deploy backend migration `0046_selection_portfolio` before the new frontend.
2. Run the existing `capture_signal_evidence` scheduler stage successfully.
3. Run `publish_public_selections`, then the existing settlement stage.
4. Verify `/api/selection-portfolio/` returns `ready`, inspect per-market rejection counts and compare homepage receipt IDs with market IDs.
5. Verify `/api/selection-portfolio/?view=results` counts each receipt once. An empty valid board is distinct from a delayed board.

The new rules have not yet been validated against future results. No positive ROI or accuracy improvement is claimed by this deployment.

Checks: backend publication/settlement/freshness/calibration contracts; frontend tests and production build; desktop English and mobile Romanian UI smoke with synthetic local responses. `scripts/portfolio-ui-smoke.cjs` accepts a path to an installed Playwright module and uses localhost only. Screenshots are local ignored artifacts.
