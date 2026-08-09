# Provider-native value strategy v2

Date introduced: 2026-08-09

## Why the old rule was retired

The old route converted the provider's leading score into `score × odds - 1`,
filtered on that derived number and globally ranked the top ten. BetGlitch had
not calibrated the score, so this was not a defensible expected-value test. It
also treated the mere presence of prediction type 33 as confirmation for an
Over 2.5 selection even though type 33 is the provider's 1X2 value-bet object.

Strategy v2 does not fit a new rule to the six August results. It replaces the
invalid decision boundary with provider-owned, timestamped evidence.

## Provider capabilities rechecked

Official SportMonks documentation confirms the following pre-match sources:

- fixture prediction-status metadata (`predictable`);
- probabilities for 20+ markets, including Fulltime Result, Correct Score,
  Double Chance, BTTS and goal totals;
- per-league/per-market Historical Log Loss, Model Hit Ratio, Model
  Predictability, Predictive Power and Current Model Log Loss;
- a dedicated Value Bet model containing direction, active flag, bookmaker
  odd, fair odd and stake;
- point-in-time pre-match odds with bookmaker and update timestamps;
- expected lineups, sidelined players, referees, weather reports, trends,
  formations and pre-match news when the subscription and fixture support them.

References:

- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/predictions
- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/predictions/get-predictability-by-league-id
- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/predictions/get-value-bets-by-fixture-id
- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures
- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/premium-expected-lineups
- https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/pre-match-odds

The local development token returned HTTP 403 during this audit. Therefore the
implementation treats unavailable premium/report-card data as missing evidence,
never as a positive value.

## Exact eligibility rule

A row can enter the value-selection feed only when all conditions hold:

1. Market is Fulltime Result (1X2). Other markets remain in the evidence feed.
2. Provider leading probability is at least 0.55.
3. Gap to the second outcome is at least 0.12 for Home/Away or 0.15 for Draw.
4. Fixture metadata explicitly says `predictable=true`.
5. League/market predictability is `good` or `high`.
6. Predictive power is present and is not `down`.
7. Native Value Bet is active and points to the same 1X2 outcome.
8. Native offered odd is above the provider fair odd.
9. BetGlitch's conservative lower-median quote remains at least 2% above that
   fair odd. This prevents a single exceptional bookmaker quote from creating
   a recommendation that is not broadly obtainable.
10. At least three bookmakers quote the exact market and outcome.
11. Relative quote spread is no more than 15%.
12. The recorded quote is no more than 12 hours old.
13. Aggregating the provider's Correct Score distribution into Home/Draw/Away
    produces the same leading outcome.
14. The provider's leading Double Chance leg contains the selected outcome.

Eligible rows are ordered lexicographically by league predictability,
predictive-power trend, fair-odds buffer, hit ratio and price dispersion. No
synthetic “quality probability” is created. At most three rows are surfaced in
one run.

## Why only 1X2 is live

The native Value Bet payload supplies `1`, `X` or `2`; it is not confirmation
for BTTS or a goal total. Promoting those markets would repeat the old semantic
error. They can become eligible only after a market-specific price/value source
and enough forward evidence exist.

## Shadow features, not live filters

Expected lineups, sidelined players, referee histories, weather, historical xG,
news and odds movement may add information. They are not assigned hand-written
weights. First they must be captured before kickoff and evaluated on future
fixtures by strategy version and decision horizon.

Regular fixture `statistics`, final `lineups`, `events`, `formations`, scores and
post-match xG must never be joined into a pre-match backtest unless an archived
observation proves they existed at decision time. Using the completed-fixture
response would be target leakage.

## Evaluation protocol

- Every provider context is appended to `SignalObservation`; updates append a
  new row rather than rewriting history.
- One fixture, not one outcome row, is the independence unit.
- `audit_value_strategy --horizon 6 --tolerance 4` evaluates the frozen rule at
  a fixed pre-kickoff horizon.
- The command reports hit rate with a Wilson interval, flat-stake ROI and an
  earlier/later time split.
- Fewer than 30 settled eligible fixtures is pipeline validation only.
- A new filter must be proposed from an earlier training period and judged on a
  later untouched period. The same sample cannot be used both to invent and to
  validate the filter.
