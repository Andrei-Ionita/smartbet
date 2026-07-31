# Hardening backlog — non-blocking

Items deliberately deferred. None blocks launch readiness.

---

## H1 — Validate the OG `state` token against the claim's canonical version

**Status:** deferred (not trivial — see below). Recorded 2026-07-31.

**Today:** `/proof/claim/<uuid>/opengraph-image?state=<token>` ignores the token
entirely and renders the claim's CURRENT state. The token exists only to give
each rendered state a distinct cache identity (see
`PublishedClaim.card_cache_version`), which is what fixes crawler caching.

**Desired:** the endpoint should verify the supplied `state` matches the claim's
current `card_cache_version`, rather than serving the current card for an
arbitrary token.

**Why it is deferred rather than done now.** Next's `opengraph-image` file
convention passes **only `params`** to the handler — never `searchParams`.
Verified against the deployed route signature:

```ts
export default async function Image({ params }: { params: { claimId: string } })
```

Reading the query string would mean replacing the file-convention route with a
custom Route Handler (`route.ts`) that constructs the `ImageResponse` itself.
That changes how Next generates, registers and caches the image — exactly the
machinery the 2026-07-31 cache-invalidation work depends on — so it is not an
isolated change and carries real deployment risk.

**Risk while deferred: low.** Serving the current card for an unknown token is
not a correctness or integrity problem — the image always reflects the claim's
true present state, and the claim's own integrity hash is unaffected. The
practical consequence is only that a stale token does not produce a 404. Nothing
false is ever published.

**When to pick this up:** alongside any future work that already touches the
image route's generation strategy, so the risk is absorbed rather than taken on
its own.
