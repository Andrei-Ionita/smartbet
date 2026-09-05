import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('new engine record and earlier archive boundary', () => {
  it('keeps earlier performance promotion disabled', () => {
    expect(read('app/lib/publicResultsMode.ts')).toContain('export const PUBLIC_RESULTS_VISIBLE = false')
    expect(read('app/page.tsx')).toContain("useSWR(PUBLIC_RESULTS_VISIBLE ? '/api/performance' : null")
  })
  it('serves the new cohort on Results', () => {
    expect(read('app/track-record/page.tsx')).toContain('<PortfolioResultsContent')
    expect(read('app/track-record/PortfolioResultsContent.tsx')).toContain('/api/selection-portfolio?view=results')
    expect(read('app/track-record/PortfolioResultsContent.tsx')).not.toContain('/api/results-selections')
    expect(read('components/Navigation.tsx')).toContain("href: '/track-record'")
  })
  it('preserves existing receipts while current cards link to their own receipt', () => {
    expect(read('app/results/selection/[selectionId]/page.tsx')).toContain('index: false, follow: false')
    expect(read('app/components/PortfolioCard.tsx')).toContain('href={item.receipt_url}')
  })
})
