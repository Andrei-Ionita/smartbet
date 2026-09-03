/**
 * Public performance is deliberately paused while selection engine v3 is
 * validated. Evidence continues to be recorded and settled server-side; this
 * flag controls only public discovery and presentation. Existing immutable
 * receipt URLs remain valid so previously issued evidence is never erased.
 *
 * Re-enable this only in a new commit that also declares the locked engine
 * version and the public record's forward start timestamp.
 */
export const PUBLIC_RESULTS_VISIBLE = false
