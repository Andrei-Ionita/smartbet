/**
 * THE activation boundary for unvalidated model behaviour.
 *
 * WHY THIS EXISTS
 * ---------------
 * Repairing the provider-form parser on 2026-08-05 had a side effect nobody
 * asked for: the form multiplier had been silently stuck at 1.0 for its entire
 * production life, so fixing the parser made the public route start applying a
 * heuristic that has never been validated against a single settled fixture.
 *
 * A correctness fix must not smuggle in a behaviour change. The parser stays
 * repaired — the evidence layer needs the real numbers — but the public route
 * keeps using the raw provider probability until the A-vs-B experiment says
 * otherwise.
 *
 * DELIBERATELY NOT NEXT_PUBLIC_
 * -----------------------------
 * Unlike COMMERCIAL_MODE, this must never be inlined into a browser bundle or
 * be reachable from the client. It governs how server-side ranking is computed;
 * a value the browser could read is a value someone could reason about
 * client-side, and there is no legitimate reason for the page to know.
 *
 * FAIL SAFE: anything other than the exact string 'true' means the heuristic is
 * OFF. Unset, empty, malformed, 'TRUE', '1', 'yes' — all resolve to disabled.
 * Enabling it is an explicit deployment change, never an accident.
 */

/** Exact opt-in string. Anything else disables. */
const ENABLED_VALUE = 'true'

/**
 * Is the form heuristic allowed to affect PUBLIC recommendation output?
 *
 * Read at call time rather than module load so tests can vary it and so a
 * config change takes effect on the next request rather than the next build.
 */
export function isFormHeuristicLive(): boolean {
  return process.env.FORM_HEURISTIC_LIVE_ENABLED === ENABLED_VALUE
}

/**
 * The activation state recorded alongside every evidence observation, so a row
 * can always be read back as "was this heuristic public when we captured it?".
 */
export function formHeuristicActivationState(): 'live' | 'shadow' {
  return isFormHeuristicLive() ? 'live' : 'shadow'
}

/**
 * Pipeline version stamped on evidence rows.
 *
 * Distinguishes three genuinely different regimes so old rows never have to be
 * rewritten to be understood:
 *
 *   evidence-v1        — inert parser: multiplier was always 1.0
 *   evidence-v2-shadow — repaired parser, heuristic NOT public
 *   evidence-v2-live   — repaired parser, heuristic public
 */
export function pipelineVersion(): string {
  return isFormHeuristicLive() ? 'evidence-v2-live' : 'evidence-v2-shadow'
}
