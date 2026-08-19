import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

describe('launch hardening', () => {
  it('uses the generated fixture URL without duplicating the prediction segment', () => {
    const workspace = read('app/components/FixtureDecisionWorkspace.tsx')
    expect(workspace).toContain('<Link href={matchSlug}')
    expect(workspace).not.toContain('`/prediction/${matchSlug}`')
  })

  it('canonicalizes the public domain and keeps monitoring out of search', () => {
    const layout = read('app/layout.tsx')
    const sitemap = read('app/sitemap.ts')
    const robots = read('app/robots.ts')
    const monitoring = read('app/monitoring/page.tsx')
    const middleware = read('middleware.ts')

    expect(layout).toContain('https://www.betglitch.com')
    expect(sitemap).toContain('https://www.betglitch.com')
    expect(sitemap).not.toMatch(/path:\s*['"]\/monitoring['"]/)
    expect(robots).toContain("'/monitoring/'")
    expect(monitoring).toContain('index: false')
    expect(middleware).toContain("host === 'betglitch.com'")
    expect(middleware).toContain("canonical.hostname = 'www.betglitch.com'")
    expect(middleware).toContain("canonical.port = ''")
    expect(middleware).toContain('NextResponse.redirect(canonical, 308)')
  })

  it('applies baseline browser security headers without wildcard API CORS', () => {
    const config = read('next.config.mjs')
    expect(config).toContain('Strict-Transport-Security')
    expect(config).toContain('Content-Security-Policy')
    expect(config).toContain("frame-ancestors 'none'")
    expect(config).toContain('Permissions-Policy')
    expect(config).not.toContain("Access-Control-Allow-Origin', value: '*'")
  })

  it('publishes aggregate Gem diagnostics without exposing fixture rejection reasons', () => {
    const engine = read('app/api/recommendations/engine.ts')
    const home = read('app/page.tsx')
    expect(engine).toContain('rejection_breakdown: publicGemRejectionBreakdown')
    expect(engine).toContain('rejection_counts_overlap: true')
    expect(home).toContain('diagnosticsHeading')
    expect(home).toContain('fixtures_affected')
  })

  it('separates the free public launch gate from monetization readiness', () => {
    const identity = read('app/lib/publicLegalIdentity.ts')
    const launchCheck = read('scripts/check-public-launch.mjs')
    const monetizationCheck = read('scripts/check-monetization-readiness.mjs')
    const packageJson = read('package.json')
    const terms = read('app/terms/TermsContent.tsx')
    const privacy = read('app/privacy/PrivacyContent.tsx')

    expect(launchCheck).toContain('NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED')
    expect(launchCheck).toContain('NEXT_PUBLIC_COMMERCIAL_MODE')
    expect(launchCheck).toContain('Free public launch mode is correctly fail-closed')
    expect(launchCheck).not.toContain('NEXT_PUBLIC_OPERATOR_NAME')
    expect(packageJson).toContain('"monetization:check"')

    for (const name of [
      'NEXT_PUBLIC_OPERATOR_NAME',
      'NEXT_PUBLIC_OPERATOR_ADDRESS',
      'NEXT_PUBLIC_OPERATOR_COUNTRY',
      'NEXT_PUBLIC_GOVERNING_LAW',
      'NEXT_PUBLIC_COMPETENT_COURTS',
    ]) {
      expect(identity).toContain(name)
      expect(monetizationCheck).toContain(name)
    }
    expect(monetizationCheck).toContain('CONTACT_EMAILS_MONITORED')
    expect(monetizationCheck).toContain('LEGAL_REVIEW_CONFIRMED')
    expect(terms).toContain('PUBLIC_LEGAL_IDENTITY_COMPLETE')
    expect(privacy).toContain('PUBLIC_LEGAL_IDENTITY_COMPLETE')
  })

  it('keeps launch-critical public surfaces available in Romanian', () => {
    const surfaces = [
      ['app/calibration/CalibrationContent.tsx', 'Sunt probabilitățile corecte?'],
      ['app/terms/TermsContent.tsx', 'Termeni și condiții'],
      ['app/privacy/PrivacyContent.tsx', 'Politica de confidențialitate'],
      ['app/disclaimer/DisclaimerContent.tsx', 'Declinarea răspunderii'],
      ['app/responsible-gambling/ResponsibleGamblingContent.tsx', 'Joc responsabil'],
      ['app/components/AgeGateModal.tsx', 'Este necesară confirmarea vârstei'],
    ] as const

    for (const [rel, romanianCopy] of surfaces) {
      const source = read(rel)
      expect(source, rel).toContain('useLanguage')
      expect(source, rel).toContain(romanianCopy)
    }

    const layout = read('app/layout.tsx')
    expect(layout.indexOf('<LanguageProvider>')).toBeLessThan(layout.indexOf('<AgeGateModal />'))
  })
})
