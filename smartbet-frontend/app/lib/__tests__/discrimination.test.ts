import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'
import { computeDiscrimination, describeAuc } from '../discrimination'

/**
 * The number that decides whether the product means anything.
 *
 * A reviewer computed the score's separation from our own public rows and
 * found ~1.3 points between correct and incorrect calls. We now publish that
 * measurement ourselves, which makes the statistic load-bearing: if this
 * function flatters the score, the page lies. So it is tested against known
 * extremes, not only against a snapshot.
 */

const root = join(__dirname, '..', '..', '..')

describe('AUC is honest at the extremes', () => {
  it('a score carrying no information reads exactly 0.500', () => {
    // Every row identical: the score cannot rank anything.
    const flat = Array.from({ length: 50 }, (_, i) => ({
      confidence: 60,
      was_correct: i % 2 === 0,
    }))
    expect(computeDiscrimination(flat)!.auc).toBeCloseTo(0.5, 10)
  })

  it('perfect separation reads 1.000', () => {
    const perfect = [
      ...Array.from({ length: 10 }, () => ({ confidence: 90, was_correct: true })),
      ...Array.from({ length: 10 }, () => ({ confidence: 10, was_correct: false })),
    ]
    expect(computeDiscrimination(perfect)!.auc).toBeCloseTo(1, 10)
  })

  it('perfectly inverted separation reads 0.000', () => {
    const inverted = [
      ...Array.from({ length: 10 }, () => ({ confidence: 10, was_correct: true })),
      ...Array.from({ length: 10 }, () => ({ confidence: 90, was_correct: false })),
    ]
    expect(computeDiscrimination(inverted)!.auc).toBeCloseTo(0, 10)
  })

  it('ties are averaged, so duplicates cannot inflate the figure', () => {
    const tied = [
      { confidence: 70, was_correct: true },
      { confidence: 70, was_correct: false },
    ]
    expect(computeDiscrimination(tied)!.auc).toBeCloseTo(0.5, 10)
  })
})

describe('only graded, scored rows are counted', () => {
  it('ignores pending rows and rows with no score', () => {
    const mixed = [
      { confidence: 70, was_correct: true },
      { confidence: 50, was_correct: false },
      { confidence: 65, was_correct: null },      // pending
      { confidence: null, was_correct: true },    // no score
      { confidence: undefined, was_correct: false },
    ]
    const d = computeDiscrimination(mixed)!
    expect(d.sample).toBe(2)
    expect(d.correct).toBe(1)
    expect(d.incorrect).toBe(1)
  })

  it('returns null rather than a fake figure when nothing is graded', () => {
    expect(computeDiscrimination([{ confidence: 60, was_correct: null }])).toBeNull()
    expect(computeDiscrimination([])).toBeNull()
  })

  it('reports no AUC when only one class exists', () => {
    const d = computeDiscrimination([{ confidence: 60, was_correct: true }])!
    expect(d.auc).toBeNull()
    expect(describeAuc(null)).toContain('not yet enough settled results')
  })
})

describe('the verdict never softens a weak result', () => {
  it('calls a near-chance AUC what it is', () => {
    // The measured production value on 2026-08-08 was 0.554.
    expect(describeAuc(0.554)).toContain('Almost no discriminating power')
    expect(describeAuc(0.554, 'ro')).toContain('Aproape nicio putere')
  })

  it('does not call anything below 0.60 reliable', () => {
    for (const auc of [0.50, 0.55, 0.59]) {
      expect(describeAuc(auc).toLowerCase()).not.toContain('consistent')
      expect(describeAuc(auc).toLowerCase()).not.toContain('strong')
    }
  })
})

describe('the monitoring page publishes the measurement', () => {
  const table = readFileSync(
    join(root, 'app/components/RecommendedPredictionsTable.tsx'), 'utf-8',
  ).replace(/\r\n/g, '\n')

  it('renders AUC, both means and the separation', () => {
    expect(table).toContain('computeDiscrimination')
    expect(table).toContain('Ranking power (AUC)')
    expect(table).toContain('Mean score when correct')
    expect(table).toContain('Mean score when incorrect')
  })

  it('measures ALL loaded rows, not the filtered view', () => {
    // Filtering until the number flatters us would be trivial otherwise.
    expect(table).toContain('computeDiscrimination(predictions)')
    expect(table).not.toContain('computeDiscrimination(filteredPredictions)')
  })

  it('warns that these rows are not the verified record', () => {
    expect(table).toContain('they are not the verified record')
  })
})
