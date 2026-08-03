/**
 * Diacritic-insensitive matching for club names.
 *
 * Most of the covered competitions have accented club names — Malmö FF,
 * Fenerbahçe, Beşiktaş, Bodø/Glimt, Universitatea Craiova. Explore matched on a
 * plain lowercase substring, so someone typing "Malmo" on an English keyboard
 * was told "No fixtures found" for a club playing that week. Verified against
 * production on 2026-08-03: "Malmo" and "Fenerbahce" both returned zero.
 *
 * Folding is applied to the indexed name and to the query alike, so it is the
 * comparison that changes — never what is displayed back to the user.
 */

/** Letters that carry no combining mark and so survive NFD unchanged. */
const STANDALONE: Array<[RegExp, string]> = [
  [/ø/gi, 'o'],
  [/ł/gi, 'l'],
  [/đ/gi, 'd'],
  [/ß/gi, 'ss'],
  [/æ/gi, 'ae'],
  [/œ/gi, 'oe'],
  [/ı/gi, 'i'],
]

export function foldForSearch(value: string): string {
  let out = value.normalize('NFD').replace(/[̀-ͯ]/g, '')
  for (const [pattern, replacement] of STANDALONE) {
    out = out.replace(pattern, replacement)
  }
  return out.toLowerCase()
}
