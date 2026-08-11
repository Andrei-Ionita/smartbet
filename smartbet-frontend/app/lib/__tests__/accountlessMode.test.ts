import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

describe('accountless public journey', () => {
  it('redirects every dormant personal page to Explore', () => {
    const middleware = read('middleware.ts')
    for (const route of [
      '/login/:path*', '/register/:path*', '/forgot-password/:path*',
      '/reset-password/:path*', '/profile/:path*', '/dashboard/:path*',
      '/bankroll/:path*', '/pricing/:path*',
    ]) {
      expect(middleware).toContain(`'${route}'`)
    }
    expect(middleware).toContain("new URL('/explore', request.url)")
    expect(middleware).toContain('ACCOUNT_FEATURES_ENABLED')
  })

  it('removes account and newsletter conversion from the homepage', () => {
    const home = read('app/page.tsx')
    expect(home).not.toContain('href="/register"')
    expect(home).not.toContain('<EmailCapture')
    expect(home).toContain('href="/track-record"')
  })

  it('keeps personal navigation behind the shared account flag', () => {
    const navigation = read('components/Navigation.tsx')
    const footer = read('components/Footer.tsx')
    expect(navigation).toContain('ACCOUNT_FEATURES_ENABLED')
    expect(footer).toContain('ACCOUNT_FEATURES_ENABLED')
  })
})
