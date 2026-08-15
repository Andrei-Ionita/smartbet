# Romanian SuperLiga activation

Status: **selected, configured and payload-verified in production**
Verified: **2026-08-13**

## Provider identity

SportMonks' official football coverage catalog lists Romania's top division as:

- Provider name: `Liga 1`
- SportMonks league ID: `474`
- BetGlitch public name after activation: `Romanian SuperLiga`
- Country: `Romania`

Official source: https://www.sportmonks.com/football-api/coverage/

The following IDs are not Romania:

- `271` — Danish Superliga
- `486` — Russian Premier League
- `609` — Ukrainian Premier League

## Public price evidence

SportMonks' published monthly prices on 2026-08-13 are:

- Starter: from €29/month for any 5 leagues
- Growth: from €99/month for any 30 leagues
- Pro: from €249/month for any 120 leagues
- Extra leagues: from €4/month
- Odds & Predictions bundle: advertised separately, starting at €15/month

Official source: https://www.sportmonks.com/football-api/plans-pricing/

BetGlitch currently configures 30 searchable competitions. The production
account is on the Growth plan, with 30 available league slots:

1. Replacing Russian Premier League #486 with Liga 1 #474 was confirmed on
   2026-08-13 at **€0 incremental monthly cost**.
2. Keeping all current selections and adding Romania as an extra league starts
   at **€4/month**. SportMonks must confirm the exact checkout price for #474.
3. BetGlitch already depends on odds and predictions. Do not assume the existing
   bundle covers #474 until real #474 payloads prove that both products are
   entitled for this league.

## Activation gate

Do not add `474` to active coverage merely because the fixture endpoint works.
Activate it only after all of these checks pass in the production account:

- [x] Liga 1 #474 is selected in My.SportMonks; Russian Premier League #486 was
      removed without changing the €132.75/month subscription total.
- [x] Upcoming fixtures return real Romanian clubs and the current season.
- [x] `participants`, `league`, `predictions`, and `odds` includes
      used by BetGlitch return data without entitlement errors.
- [x] The 1X2 prediction types required by the signal engine are populated.
- [x] Canonical pre-match prices include bookmaker and freshness provenance.
- [x] Explore cards and the full fixture workspace work for at least three
      Romanian fixtures.
- [x] Romania replaces Russia in both searchable and signal coverage in
      `smartbet-frontend/app/lib/coverage.ts`.
- [x] Public competition counts and competition-identity tests pass.

The activation gate passed against production on 2026-08-15. The 14-day Explore
index returned 22 Romanian fixtures; three fixture payloads were sampled for
model probabilities, verified prices, bookmaker and timestamp provenance, form,
venue and archived context.
