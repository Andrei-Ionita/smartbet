# Provider strategy Generation 3

Generation 3 keeps all Generation 2 qualification gates and changes only how
the survivors are ordered and explained publicly.

## Qualification

A fixture is eligible only when the provider marks it predictable; league 1X2
performance is good or high and not trending down; the active provider value
signal points to the selected outcome; correct-score and double-chance outputs
agree; the verified quote is at least 2% above the provider baseline; at least
three bookmakers quote the selection; relative dispersion is at most 15%; and
the price is no more than 12 hours old.

## Gem ordering

For each eligible fixture:

1. `p_provider = 1 / provider_baseline_price`
2. `verified_price = provider_baseline_price × (1 + verified_price_advantage)`
3. `probability_payout_balance = (p_provider × verified_price − 1) / (verified_price − 1)`

The balance is used only to rank already-qualified candidates. It is equivalent
to a Kelly growth fraction mathematically, but BetGlitch does not publish or use
it as stake advice. It limits the tendency to favour a longshot merely because
its payout or raw price difference is larger.

Ties are resolved by league predictability, predictive-power trend, verified
price advantage, provider implied chance, league hit ratio and lower price
dispersion. At most three Gems are displayed per run.

## Public proof

The public API allowlists the Gem rank, provider implied chance, provider
baseline price, verified price advantage, league report-card fields,
bookmaker count, price spread and age, and the two cross-market agreement flags.
Internal ranking objects and stake fields remain private. The full ranking
policy is hashed into the ranking version stamped on every committed record.
