# SportMonks Utilization Audit — 2026-07-23

**Question:** we pay for SportMonks monthly — are we extracting a fair fraction of what the API returns, or leaving predictive signal on the table?

**Answer:** we are using roughly **10–15% of what SportMonks returns per fixture**. There are 8+ concrete, unused signals with plausible ROI value, ranked below. Two potentially high-value fields (`xg` / `weather`) require a plan upgrade.

---

## Methodology

- Pulled one representative post-fix fixture: **Atalanta vs Bologna, 2026-05-17** (id=19425241, in our current recommendation universe).
- Requested every valid SportMonks include for a football fixture: `odds, predictions, participants, venue, sidelined, metadata, statistics, lineups, referees, league, season, scores, state, events, formations, coaches, periods`.
- API rejected two: `weather` (not a valid include) and `xgfixture` (plan tier gate).
- Response size: **1,946,493 bytes** (~1.9 MB per fixture).
- Cross-referenced with `smartbet-frontend/app/api/recommendations/route.ts` and `core/*.py` to determine which fields we actually consume.

## Current request pattern

Our production fixture-fetch (`route.ts:308`) requests:
```
include=participants;league;metadata;predictions;odds;odds.bookmaker
```

We also make two supplementary calls:
- `/standings/seasons/{id}?include=form` (line 860) — used for form data
- `/teams/{id}?include=form` (line 906) — used for form data

**We do NOT request:** `statistics`, `lineups`, `events`, `sidelined`, `referees`, `formations`, `coaches`, `venue`, `state`, `scores`.

## Field-by-field usage

### 1. `predictions` — 28 items returned, we consume ~4

**Consumed type_ids:**
- 231 (BTTS), 235 (O/U 2.5), 239 (Double Chance), 238 (1X2 home/away/draw)

**Unused type_ids (24 total):**
- **1585, 1679, 1683, 1684**: single-value ML signals from other SportMonks models (unknown semantics without documentation lookup)
- **1685, 1686, 1687, 1688, 1689, 1690**: ML predictors returning `{yes, no, equal}` triplets. Example values from Atalanta v Bologna: `1685={80.4, 11.6, ...}` — these look like high-conviction directional signals we're totally ignoring.
- **232, 233, 234, 236, 237, 240**: likely variations on goal-total predictions (Over/Under at other lines: 1.5, 3.5)
- **326, 327, 328**: possibly correct-score or HT/FT models
- **330, 331, 332, 333, 334**: additional predictor slots (332 in our sample gave `{yes: 32.17, no: 67.83}` — looks like a binary signal)

**Highest-leverage opportunity:** enumerate what these 24 type_ids represent (SportMonks docs lookup or one API call to `/predictions/probabilities/fixtures/types`) and see if any correlate with post-hoc win rates. Some are almost certainly **ensemble ML outputs from different SportMonks models** — we're using one when we could ensemble 5.

### 2. `statistics` — 12 items returned, we consume 0

Sample data from Atalanta v Bologna:
- `type_id=34, value=5 (away), value=2 (home)` — likely shots on target
- `type_id=45, value=55 (away), value=45 (home)` — possession %
- `type_id=52, value=1 (away)` — corners / fouls / etc.

These are **historical stats attached to the fixture** — a team's average or recent shot/possession numbers relevant to the match. Useful for:
- Team offensive/defensive strength baseline
- Over/Under 2.5 correlation (high combined shot averages ⇒ more goals)

Currently completely ignored.

### 3. `sidelined` — 7 injury/suspension records returned, we consume 0

**Home team (Atalanta):** 3 players sidelined. **Away team (Bologna):** 4 players sidelined.

Each record has `player_id`, `participant_id`, and `type_id` (indicating injury type / suspension). Cross-reference with `lineups.position_id` to identify which positions are affected — a missing striker signals fewer goals; a missing goalkeeper signals more.

Zero cost to add — data is already in the response we're already paying for.

### 4. `referees` — 4 referee IDs returned, we consume 0

Match had 4 referees (main + 2 assistants + 4th official). SportMonks exposes `/referees/{id}` with historical stats. Referee tendencies matter for O/U 2.5:
- **High-carding refs** interrupt attacking play → fewer goals
- **VAR-permissive refs** disallow goals more often
- Some refs statistically preside over higher-scoring matches

Would require one additional API call per fixture (main ref only) + a `RefereeStat` cache table. Medium-effort, potentially meaningful for the market we bet on.

### 5. `formations` — 2 formations returned, we consume 0

Our sample: **Atalanta 3-4-2-1** (attacking, 3 forwards behind striker) vs **Bologna 4-3-3** (attacking, 3 forwards). Two attacking formations = O/U 2.5 OVER more likely.

Formation counts as a **discrete categorical feature** — encode it as attacking/defensive score, add to O/U 2.5 EV computation. Zero API cost.

### 6. `metadata` — 11 items returned, we consume the file (`fixture.metadata`) but never read individual fields

**Highest-value unused metadata:**
- **`type_id=37072, values={"predictable": True}`** — SportMonks' OWN meta-signal about whether this fixture is predictable. **We should filter out fixtures where `predictable=False`.** Zero-cost win.
- **`type_id=97352, values={"computable": True}`** — related quality signal.
- `type_id=572, values={"confirmed": True}` — lineup confirmation status. Fixture with unconfirmed lineups → we're guessing at team composition.
- `type_id=35, values={"neutral": False}` — neutral venue flag (matters for home advantage).
- `type_id=578, values={"attendance": 22140}` — atmosphere proxy (weak signal).

### 7. `venue` — dict with lat/long returned, we consume 0

Latitude/longitude enables weather lookups from a third-party API (since SportMonks doesn't include it on our tier). Also: altitude affects match dynamics (Andes leagues).

### 8. `lineups` — 46 player entries returned, we consume 0

Full starting XI + subs with `position_id`. Enables:
- Detection of key player rotation (rested striker = fewer goals)
- Formation-position interaction
- Cross-reference with `sidelined` to identify positional gaps

### 9. Other includes returned but unused

- `events` (12) — in-match events; only useful for post-match analysis (goals scored at what minutes)
- `scores` (8) — post-match scoreline (we already fetch this via `actual_score_home/away`)
- `state` (dict) — fixture state (upcoming / in progress / finished)
- `periods` (2) — half timings; only useful live
- `coaches` (2) — coach IDs; could tap /coaches/{id} for tactical history
- `season` (dict) — season metadata (finished, current). We use it.

### 10. NOT available on current plan

- **`xg` / `xgfixture`** — expected goals. Would be the single most predictive feature for O/U 2.5. **Blocked by plan tier.**
- **`weather`** — not a valid include (rejected by API). May need third-party enrichment via venue lat/long.

---

## Additional SportMonks endpoints we could call

Beyond the fixture endpoint, SportMonks exposes:
- `/predictions/value-bets` — SportMonks' dedicated value-bets service (finds bets where their probability > market implied). Worth checking.
- `/predictions/probabilities/fixtures/{id}` — dedicated probability endpoint (may have richer data than what's bundled in fixture response).
- `/teams/{id}/statistics/seasons/{id}` — season-long team stats
- `/referees/{id}/statistics/seasons/{id}` — referee stat cards
- `/leagues/{id}/schedules` — league-wide baselines for calibration

---

## Ranked backlog of experiments

Each opportunity ranked by **expected ROI lift × implementation cost**.

### Tier 1 — Free (data is already in the response, ~30 min–2 hr each)

| # | Signal | Rationale | Effort |
|---|---|---|---|
| **1** | **Filter `predictable=True`** | SportMonks itself telling us which fixtures are predictable. Zero-cost. Should immediately trim garbage picks. | 30 min |
| **2** | **Formations as feature** | Attacking-vs-defensive formation classification into O/U 2.5 EV. Data in response. | 1–2 hr |
| **3** | **Sidelined count as feature** | Simple: home_sidelined_count and away_sidelined_count as adjustment factors. Ignore player positions initially. | 1 hr |
| **4** | **Cross-market confluence filter** | Only take O/U 2.5 OVER if BTTS also says YES AND 1X2 doesn't favor a defensive team. Multi-signal agreement gate. | 3 hr |
| **5** | **Enumerate unused prediction type_ids** | Document lookup + one-off analysis: which of the 24 unused type_ids correlate with post-hoc win rates on our snapshot? Might reveal 2-3 "hidden" high-signal features. | 2–3 hr |

### Tier 2 — Additional API calls (need caching, ~4–8 hr each)

| # | Signal | Rationale | Effort |
|---|---|---|---|
| **6** | **Referee tendencies** | `/referees/{id}` for main referee's historical avg goals/cards per game. High-carding refs = fewer goals. Cache per referee. | 4–6 hr |
| **7** | **SportMonks value-bets endpoint** | Dedicated API SportMonks provides for value bet detection. Compare their picks to ours. | 3–4 hr |
| **8** | **Team historical statistics** | `/teams/{id}/statistics` for shots-per-game, possession, xG-if-included, defensive stats. Cache per team. | 6–8 hr |
| **9** | **Lineups × sidelined interaction** | Match sidelined player_ids against lineup position_ids: is the missing player a striker (bad for OVER) or defender (bad for UNDER)? | 4–6 hr |

### Tier 3 — Plan upgrade required

| # | Signal | Rationale |
|---|---|---|
| **10** | **xG (expected goals)** | Single strongest predictor for O/U 2.5 goals. SportMonks Advanced plan (~2x current cost) unlocks. **Consider a cost-benefit analysis: if xG lifts ROI from 5-8% to 10-15%, doubling the SportMonks bill pays back on the first ~€500/mo of bet volume.** |
| **11** | **Weather (venue-based)** | Third-party (OpenWeatherMap) using SportMonks' venue lat/long. Rain/wind → fewer goals. Free tier likely sufficient. |

---

## Recommended first move

**Tier 1, item #1 — Filter on `predictable=True`.**

Reasoning:
- **Data is already in the response we already fetch** — zero API cost, zero new dependencies
- Direct effect: excludes fixtures where SportMonks itself is signaling low confidence in its own predictions
- Backtestable on the existing 275-row snapshot: subset the rows where `metadata` contains `predictable=True`, compare ROI to the full universe
- Blast radius: tiny (one line in the recommendation filter)
- Time: 30 min including the backtest + deploy

If this alone lifts ROI meaningfully (say +2-3pp), it's a proof-of-concept that the SportMonks-squeeze thesis is real, and unlocks the appetite for Tier 1 items 2-5.

**Alternative if you want to swing bigger:** Tier 1, item #5 (enumerate the 24 unused prediction type_ids). Higher upfront work (2-3 hrs), but if it reveals even one strong signal, it fundamentally reshapes the model without new infrastructure.

---

## Non-goals of this audit

- No production changes made — this is diagnostic only.
- No formal experiment run yet — every "ROI lift" number cited above is a hypothesis, not a measurement.
- No cost-benefit analysis of the SportMonks plan upgrade (would need a separate spec).
- No comparison against other data providers (Opta, StatsPerform, Bet-Genius) — out of scope.

---

*Audit generated by manual API introspection + codebase grep. Raw fixture response persisted at `tmp/fixture_full.json` (git-ignored).*
