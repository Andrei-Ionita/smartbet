import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('public performance history pause', () => {
  it('uses one explicit false-by-default release flag', () => {
    const mode = read('app/lib/publicResultsMode.ts')
    expect(mode).toContain('export const PUBLIC_RESULTS_VISIBLE = false')
    expect(mode).toContain('Existing immutable')
    expect(mode).toContain('receipt URLs remain valid')
    expect(mode).toContain("public record's forward start timestamp")
  })

  it('replaces the Results history with a bilingual validation notice', () => {
    const page = read('app/track-record/page.tsx')
    const notice = read('app/track-record/ResultsValidationContent.tsx')
    expect(page).toContain('PUBLIC_RESULTS_VISIBLE ? <UnifiedResultsContent /> : <ResultsValidationContent />')
    expect(page).toContain('index: false')
    expect(notice).toContain('The public results record has not started yet')
    expect(notice).toContain('Istoricul public de rezultate nu a început încă')
    expect(notice).toContain('Existing immutable receipts remain valid')
    expect(notice).not.toContain('/api/results-selections')
  })

  it('removes Results from normal discovery while preserving current fixture research', () => {
    const navigation = read('components/Navigation.tsx')
    const footer = read('components/Footer.tsx')
    const sitemap = read('app/sitemap.ts')
    const home = read('app/page.tsx')
    expect(navigation).toContain("...(PUBLIC_RESULTS_VISIBLE ? [{ href: '/track-record'")
    expect(footer).toContain('PUBLIC_RESULTS_VISIBLE &&')
    expect(sitemap).toContain("...(PUBLIC_RESULTS_VISIBLE ? ['/track-record'] : [])")
    expect(home).toContain("useSWR(PUBLIC_RESULTS_VISIBLE ? '/api/performance' : null")
    expect(home).toContain('<HomepageSelections')
  })

  it('does not promote historical receipts from current fixture or strategy surfaces', () => {
    const fixtureReceipts = read('app/components/FixtureSelectionReceipts.tsx')
    const homepage = read('app/components/HomepageSelections.tsx')
    const strategies = read('app/components/StrategyCurrentFits.tsx')
    expect(fixtureReceipts).toContain('PUBLIC_RESULTS_VISIBLE ?')
    expect(fixtureReceipts).toContain('if (!PUBLIC_RESULTS_VISIBLE || !receipts.length) return null')
    expect(homepage).toContain('PUBLIC_RESULTS_VISIBLE && item.receipt_url')
    expect(strategies).toContain('PUBLIC_RESULTS_VISIBLE && <Link href={item.receipt_url}')
    expect(read('app/prediction/[...slug]/PredictionContent.tsx')).toContain('PUBLIC_RESULTS_VISIBLE && <div className="mt-8">')
    expect(read('app/results/selection/[selectionId]/page.tsx')).toContain('index: false, follow: false')
  })
})
