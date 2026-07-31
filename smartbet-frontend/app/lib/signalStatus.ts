/**
 * The public status vocabulary, as pure data.
 *
 * Kept out of the badge component so it can be tested without a DOM, and so
 * server code can classify a claim without importing React.
 */

export type SignalStatus =
  | 'live'
  | 'published_pending'
  | 'won'
  | 'lost'
  | 'void'
  | 'cancelled'
  | 'legacy'

/**
 * Map a backend claim/result status onto the public badge vocabulary.
 *
 * A settled outcome is authoritative: once a claim has a result, that is what
 * the public sees, regardless of the claim row's own status field.
 */
export function statusFromClaim(
  claimStatus?: string | null,
  outcome?: string | null,
): SignalStatus {
  const o = (outcome || '').toLowerCase()
  if (o === 'won' || o === 'win') return 'won'
  if (o === 'lost' || o === 'loss') return 'lost'
  if (o === 'void') return 'void'
  if (o === 'cancelled' || o === 'canceled') return 'cancelled'

  const s = (claimStatus || '').toLowerCase()
  if (s === 'legacy_unverified' || s === 'legacy') return 'legacy'
  if (s === 'pending' || s === 'published') return 'published_pending'
  return 'live'
}
