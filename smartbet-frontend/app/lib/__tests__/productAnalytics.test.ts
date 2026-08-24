import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('privacy-minimal product analytics', () => {
  const analytics = read('app/lib/analytics.ts')
  const collector = read('app/api/product-events/route.ts')
  const layout = read('app/layout.tsx')

  it('collects anonymous route reach and coarse dwell from the root layout', () => {
    expect(layout).toContain('<ProductAnalytics />')
    expect(analytics).toContain("| 'page_viewed'")
    expect(analytics).toContain("| 'page_dwell'")
    expect(analytics).toContain('duration_bucket')
  })

  it('uses a session-only UUID and sends no query or fixture identifier', () => {
    expect(analytics).toContain('window.sessionStorage')
    expect(analytics).toContain('window.crypto.randomUUID()')
    expect(analytics).toContain("return '/prediction/:slug'")
    expect(analytics).toContain("surface.split('?')[0]")
    expect(analytics).not.toContain('localStorage')
  })

  it('uses a same-origin endpoint with no browser credentials', () => {
    expect(analytics).toContain("fetch('/api/product-events/'")
    expect(analytics).toContain("credentials: 'omit'")
    expect(collector).toContain("process.env.DJANGO_API_URL")
    expect(collector).toContain("'Cache-Control': 'no-store'")
    expect(collector).not.toContain("request.headers.get('cookie')")
    expect(collector).not.toContain("request.headers.get('authorization')")
  })
})
