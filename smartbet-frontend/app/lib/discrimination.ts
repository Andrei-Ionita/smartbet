/**
 * How well does the signal score actually separate right calls from wrong ones?
 *
 * A reviewer computed this from our own public monitoring rows on 2026-08-08
 * and used it against us: mean score 62.0 when correct versus 60.7 when
 * incorrect, a 1.3-point gap. They were right to two decimals, and the point
 * lands — a prominent 0-100 number implies discriminating power the evidence
 * does not show.
 *
 * The response is not to hide the number. It is to compute it ourselves, in
 * public, from the same rows the page displays, and let a visitor see exactly
 * how weak the separation is before they read anything into a score. If the
 * separation improves, this panel improves with it; if it degrades, it says so.
 *
 * AUC here is the Mann-Whitney statistic: the probability that a randomly
 * chosen CORRECT call scored higher than a randomly chosen INCORRECT one.
 * 0.50 means the score carries no ranking information whatsoever.
 */

export interface ScoredOutcome {
  confidence: number | null | undefined
  was_correct: boolean | null | undefined
}

export interface DiscriminationBucket {
  label: string
  correct: number
  incorrect: number
  hitRate: number | null
}

export interface Discrimination {
  /** Graded rows that carried a usable score. */
  sample: number
  correct: number
  incorrect: number
  meanCorrect: number
  meanIncorrect: number
  /** meanCorrect − meanIncorrect, in score points. */
  separation: number
  /** Mann-Whitney AUC, or null when one class is empty. */
  auc: number | null
  buckets: DiscriminationBucket[]
}

const BUCKETS: Array<{ label: string; min: number; max: number }> = [
  { label: 'Below 55', min: -Infinity, max: 55 },
  { label: '55 – 59', min: 55, max: 60 },
  { label: '60 – 64', min: 60, max: 65 },
  { label: '65 and above', min: 65, max: Infinity },
]

const mean = (xs: number[]) =>
  xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0

/**
 * Rank-based AUC. Ties take the average rank, which is what keeps a score
 * that is constant across every row at exactly 0.5 rather than flattering it.
 */
function computeAuc(positives: number[], negatives: number[]): number | null {
  if (!positives.length || !negatives.length) return null

  const all = [...positives.map((v) => ({ v, pos: true })), ...negatives.map((v) => ({ v, pos: false }))]
  all.sort((a, b) => a.v - b.v)

  const ranks = new Array<number>(all.length)
  let i = 0
  while (i < all.length) {
    let j = i
    while (j + 1 < all.length && all[j + 1].v === all[i].v) j++
    const avgRank = (i + j + 2) / 2 // 1-based ranks
    for (let k = i; k <= j; k++) ranks[k] = avgRank
    i = j + 1
  }

  let rankSumPositive = 0
  all.forEach((row, idx) => {
    if (row.pos) rankSumPositive += ranks[idx]
  })

  const n1 = positives.length
  const n2 = negatives.length
  return (rankSumPositive - (n1 * (n1 + 1)) / 2) / (n1 * n2)
}

export function computeDiscrimination(rows: ScoredOutcome[]): Discrimination | null {
  const graded = rows.filter(
    (r) => typeof r.confidence === 'number' && typeof r.was_correct === 'boolean',
  ) as Array<{ confidence: number; was_correct: boolean }>

  if (graded.length === 0) return null

  const positives = graded.filter((r) => r.was_correct).map((r) => r.confidence)
  const negatives = graded.filter((r) => !r.was_correct).map((r) => r.confidence)

  const buckets = BUCKETS.map(({ label, min, max }) => {
    const inBucket = graded.filter((r) => r.confidence >= min && r.confidence < max)
    const correct = inBucket.filter((r) => r.was_correct).length
    const incorrect = inBucket.length - correct
    return {
      label,
      correct,
      incorrect,
      hitRate: inBucket.length ? (100 * correct) / inBucket.length : null,
    }
  })

  return {
    sample: graded.length,
    correct: positives.length,
    incorrect: negatives.length,
    meanCorrect: mean(positives),
    meanIncorrect: mean(negatives),
    separation: mean(positives) - mean(negatives),
    auc: computeAuc(positives, negatives),
    buckets,
  }
}

/**
 * Plain-language verdict. Deliberately blunt at the low end: the honest
 * reading of an AUC near 0.5 is "this barely ranks anything", and softening
 * it would recreate the overstatement this whole panel exists to correct.
 */
export function describeAuc(auc: number | null, lang: 'en' | 'ro' = 'en'): string {
  if (auc === null) {
    return lang === 'ro'
      ? 'Nu există încă suficiente rezultate pentru a măsura separarea.'
      : 'There are not yet enough settled results to measure separation.'
  }
  // 0.56, not 0.55: at n in the low hundreds, sampling noise alone spans
  // several points of AUC, so anything under ~0.56 is indistinguishable from
  // a score that ranks nothing. Erring toward the harsher label is the point.
  if (auc < 0.56) {
    return lang === 'ro'
      ? 'Aproape nicio putere de discriminare — abia se distinge de o alegere la întâmplare.'
      : 'Almost no discriminating power — barely distinguishable from chance.'
  }
  if (auc < 0.60) {
    return lang === 'ro'
      ? 'Putere de discriminare slabă. Nu trata scorul ca pe o măsură fiabilă.'
      : 'Weak discriminating power. Do not treat the score as a reliable measure.'
  }
  if (auc < 0.70) {
    return lang === 'ro'
      ? 'Putere de discriminare modestă, dar măsurabilă.'
      : 'Modest but measurable discriminating power.'
  }
  return lang === 'ro'
    ? 'Putere de discriminare consistentă în acest eșantion.'
    : 'Consistent discriminating power across this sample.'
}
