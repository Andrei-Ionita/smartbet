import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('unified public Results', () => {
  const page = read('app/track-record/page.tsx')
  const results = read('app/track-record/UnifiedResultsContent.tsx')
  const navigation = read('components/Navigation.tsx')

  it('uses one Results page with separate records for each public selection standard', () => {
    expect(page).toContain('<UnifiedResultsContent')
    expect(results).toContain("tabs: { overview: 'Overview', homepage: 'Homepage', strategy: 'Strategies', gems: 'Hidden Gems', pending: 'Pending' }")
    expect(results).toContain("rows.filter(row => row.category === 'homepage')")
    expect(results).toContain("rows.filter(row => row.category === 'strategy')")
    expect(results).toContain("rows.filter(row => row.category === 'gems')")
  })

  it('shows the useful public metrics without blending denominators', () => {
    expect(results).toContain("record: 'Record'")
    expect(results).toContain("hitRate: 'Hit rate'")
    expect(results).toContain("averageOdds: 'Average odds'")
    expect(results).toContain("roi: 'ROI'")
    expect(results).toContain('Nothing is blended into a more flattering denominator')
  })

  it('keeps pending selections and losses visible', () => {
    expect(results).toContain("row.status === 'PENDING'")
    expect(results).toContain("status === 'LOST' || status === 'HALF_LOST'")
    expect(results).toContain('Pending selections remain visible')
  })

  it('removes technical research and calibration from the primary navigation', () => {
    expect(navigation).toContain("href: '/track-record'")
    expect(navigation).not.toContain("href: '/monitoring'")
    expect(navigation).not.toContain("href: '/calibration'")
  })
})
