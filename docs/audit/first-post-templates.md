# First external post — caption TEMPLATES

**Status:** DRAFT TEMPLATES. **Nothing published.** Final copy is populated from
the chosen claim and returned for founder approval before any external post.

Placeholders: `[HOME]`, `[AWAY]`, `[LEAGUE]`, `[SELECTION]`, `[ODDS]`,
`[BOOKMAKER]`, `[KICKOFF_UTC]`, `[PROOF_URL]`.

**Banned throughout:** guaranteed, lock, sure bet, proven winner, profitable
system, "the market is definitely wrong", any ROI or profitability figure, any
claim of a proven edge.

---

## 1. Founder / record-building

> BetGlitch's verified public record starts here — with pick #1.
>
> Every published pick is frozen before kickoff and remains visible after
> full-time, whether it wins or loses.
>
> No reconstructed history. No deleted losses. The record starts at zero and is
> built in public.
>
> [LEAGUE] · [HOME] vs [AWAY]
> [SELECTION] — recorded at [ODDS] with [BOOKMAKER]
>
> [PROOF_URL]

## 2. Hidden fixture

> A fixture most bettors will overlook.
>
> [HOME] vs [AWAY]
> [SELECTION] — recorded at [ODDS] with [BOOKMAKER]
>
> Published before kickoff. The result will be added automatically after
> full-time — win or lose.
>
> [PROOF_URL]

## 3. Concise (X)

> BetGlitch verified pick #1
>
> [HOME] vs [AWAY]
> [SELECTION] · recorded odds [ODDS]
>
> Frozen before kickoff. Result added after full-time — win or lose.
>
> [PROOF_URL]

---

## Population rules

- `[ODDS]` uses the two-decimal public format (`1.80`), taken from
  `PublishedClaim.odds` — the frozen price, never a live re-quote.
- `[SELECTION]` uses the public market wording (`BTTS — YES`), not the stored
  strings.
- `[BOOKMAKER]` uses public casing (`Bet365`).
- `[PROOF_URL]` is the canonical claim URL: `/proof/claim/<claim_uuid>`.
- Every value is read from the immutable claim, so the caption cannot drift from
  the card.

## A note on the recorded price

The caption says **recorded at**, not "available at". By the time an audience
sees a post the price may have moved; the claim records what we recorded, when
we recorded it. Choosing a fixture inside a 6–24h window keeps that gap small —
which is the entire purpose of the queue's ordering.
