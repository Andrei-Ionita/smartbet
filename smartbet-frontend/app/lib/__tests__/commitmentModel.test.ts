/**
 * The three-state product model: LIVE SIGNAL → PUBLIC COMMITMENT → VERIFIED
 * RESULT.
 *
 * The confusion this contract exists to prevent, observed on the real product:
 * the homepage showed many analysed fixtures while /track-record showed exactly
 * one "published pick" — so Cardiff read as a hand-picked flagship
 * recommendation, when it is simply record entry #1: the first signal formally
 * frozen into the permanent evaluation record. A live signal must never read
 * as "BetGlitch recommends this bet", and a commitment must never read as a
 * quality verdict.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { getCopy } from '../terminology'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

/** Comments legitimately name what they removed; scan rendered code only. */
const rendered = (rel: string) =>
  read(rel)
    .replace(/\r\n/g, '\n')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .map((l) => l.replace(/\/\/.*$/, ''))
    .join('\n')

const en = getCopy('en')
const ro = getCopy('ro')

describe('the three concepts exist, in both languages', () => {
  it('names live signal / public commitment / verified record', () => {
    expect(en.terms.liveSignal.label).toBe('Live signal')
    expect(en.terms.publicCommitment.label).toBe('Public commitment')
    expect(en.terms.verifiedRecord.label).toBe('Verified record')
    expect(ro.terms.liveSignal.label).toBe('Semnal live')
    expect(ro.terms.publicCommitment.label).toBe('Angajament public')
    expect(ro.terms.verifiedRecord.label).toBe('Istoric verificat')
  })

  it('a live signal explicitly denies being a recommendation', () => {
    expect(en.terms.liveSignal.notInRecord).toContain('not a betting recommendation')
    expect(ro.terms.liveSignal.notInRecord).toContain('nu este o recomandare de pariere')
  })

  it('a commitment explicitly denies being a value verdict', () => {
    expect(en.terms.publicCommitment.notARecommendation)
      .toContain('not a claim that a signal has proven betting value')
    expect(ro.terms.publicCommitment.notARecommendation)
      .toContain('nu este o afirmație că semnalul are valoare de pariere dovedită')
  })

  it('pending commitments are not results', () => {
    expect(en.record.publishedNotCounted)
      .toBe('Awaiting settlement — not included in verified performance')
    expect(ro.record.publishedNotCounted)
      .toContain('În așteptarea încheierii')
    expect(en.record.publishedStates).toContain('Pending is not a result')
  })

  it('the verified record is scoped to eligible settled commitments', () => {
    expect(en.record.verifiedFromCommitments).toContain(
      'The verified record below contains only eligible settled commitments',
    )
    expect(en.terms.verifiedRecord.scope).toContain('Only eligible settled commitments count')
  })
})

describe('"published picks" is no longer the public concept', () => {
  it.each([
    'app/lib/terminology.ts',
    'app/locales/translations.ts',
    'app/components/StatusBadge.tsx',
    'app/components/EmptyState.tsx',
    'app/components/EmailCapture.tsx',
    'app/proof/_shared/ProofPageBody.tsx',
    'app/track-record/page.tsx',
  ])('%s carries no published-pick vocabulary in rendered code', (rel) => {
    const src = rendered(rel).toLowerCase()
    expect(src).not.toContain('published pick')
    expect(src).not.toContain('pontaj publicat')
    expect(src).not.toContain('pontajele publicate')
  })

  it('the record section heading is Public commitments, both languages', () => {
    expect(en.record.publishedHeading).toBe('Public commitments')
    expect(ro.record.publishedHeading).toBe('Angajamente publice')
  })
})

describe('live surfaces never look like betting recommendations', () => {
  /**
   * RECOMMENDED / PICK / BET as a card badge is the reading the model forbids.
   * Word-boundary uppercase forms only — "Explore" contains no violation, and
   * lowercase prose is covered by the vocabulary scans above.
   */
  it.each([
    'app/page.tsx',
    'app/explore/ExploreContent.tsx',
    'app/components/RecommendationCard.tsx',
  ])('%s renders no RECOMMENDED / PICK / BEST BET badge', (rel) => {
    const src = rendered(rel)
    expect(src).not.toMatch(/['">]RECOMMENDED['"<]/)
    expect(src).not.toMatch(/['">](?:BEST |TOP )?PICK['"<]/)
    expect(src).not.toMatch(/['">]BEST BET['"<]/)
  })

  it('the homepage signal section uses the live-signal vocabulary', () => {
    const src = read('app/page.tsx')
    expect(src).toContain('signalsHeading')
    expect(src).toContain('<StatusBadge status="live"')
  })

  it('Explore stays entirely in the live-signal domain', () => {
    const translations = read('app/locales/translations.ts')
    expect(translations).toContain(
      'enter the public evaluation record only if BetGlitch formally commits them',
    )
  })
})

describe('the ledger, not a featured match', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('renders every commitment through the same map — identical treatment', () => {
    // One template for all rows; a special-cased Cardiff would need a branch.
    expect(src).toContain('{claims.map((claim) => (')
    expect(src).not.toMatch(/Cardiff/i)
  })

  it('hardcodes no claim UUID anywhere in the frontend', () => {
    for (const rel of [
      'app/track-record/TrackRecordContent.tsx',
      'app/page.tsx',
      'app/lib/terminology.ts',
    ]) {
      expect(rendered(rel)).not.toMatch(
        /['"][0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}['"]/i,
      )
    }
  })

  it('each row states its evaluation status', () => {
    expect(src).toContain('rec.publishedCountedIn')
    expect(src).toContain('rec.publishedNotCounted')
  })

  it('uses ledger labels: recorded price and committed date', () => {
    expect(en.record.publishedOddsLabel).toBe('Recorded price')
    expect(en.record.publishedAtLabel).toBe('Committed')
  })
})

describe('anchors: new concept, unbroken links', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('introduces #public-commitments and keeps #published-picks as an alias', () => {
    expect(src).toContain('id="public-commitments"')
    expect(src).toContain('id="published-picks"')
  })

  it('onboarding points at the new anchor in both languages', () => {
    const hrefsEn = en.onboarding.actions.map((a) => a.href)
    const hrefsRo = ro.onboarding.actions.map((a) => a.href)
    expect(hrefsEn).toContain('/track-record#public-commitments')
    expect(hrefsRo).toContain('/track-record#public-commitments')
  })

  it('onboarding teaches the three-stage journey', () => {
    expect(en.onboarding.actions.map((a) => a.cta)).toEqual([
      'Explore live signals',
      'View public commitments',
      'Open verified record',
    ])
  })
})

describe('publication policy is honest', () => {
  it('describes a deliberate manual step gated by eligibility checks', () => {
    expect(en.record.policyBody).toContain('deliberate manual step')
    expect(en.record.policyBody).toContain('eligibility checks')
    expect(ro.record.policyBody).toContain('pas manual deliberat')
  })

  it('publication is explicitly not a value claim', () => {
    expect(en.record.policyBody).toContain(
      'Publication itself is not a claim that a signal has proven betting value',
    )
  })

  it('invents no selection rule the code does not have', () => {
    // check_snapshot_publication_eligibility gates on integrity, provenance
    // and timing — never on signal strength or value. The copy must not claim
    // otherwise.
    for (const banned of [
      'strongest signal', 'best value', 'highest confidence',
      'profitable signals', 'price-qualified',
    ]) {
      expect(en.record.policyBody.toLowerCase()).not.toContain(banned)
      expect(ro.record.policyBody.toLowerCase()).not.toContain(banned)
    }
  })

  it('the policy is rendered as a disclosure on the ledger', () => {
    const src = read('app/track-record/TrackRecordContent.tsx')
    expect(src).toContain('rec.policyLink')
    expect(src).toContain('rec.policyBody')
    expect(src).toContain('<details')
  })
})

describe('the proof page is an accountability artifact, not an endorsement', () => {
  const src = read('app/proof/_shared/ProofPageBody.tsx')

  it('explains commitment-before-kickoff and denies the value claim', () => {
    expect(src).toContain('committed to the public record before kickoff')
    expect(src).toContain('evaluated without hindsight')
    expect(src).toContain('not a claim of proven betting value')
  })

  it('states the pending and settled positions', () => {
    expect(src).toContain('Awaiting settlement — not yet counted as a verified result.')
    expect(src).toContain('included in the verified record')
  })

  it('keeps the immutable audit trail', () => {
    for (const kept of ['claim_hash', 'published_at', 'formatOdds', 'formatBookmaker']) {
      expect(src).toContain(kept)
    }
  })
})

describe('the frozen score and the Explore commitment marker', () => {
  it('the proof surfaces render the score as /100 with the bilingual note', () => {
    const body = read('app/proof/_shared/ProofPageBody.tsx')
    expect(body).toContain('label="Signal score at commitment"')
    expect(body).toContain('recorded when the commitment was published')
    expect(body).toContain('It\n        is a relative ranking, not a calibrated probability.')
    expect(body).toContain('Este o clasare relativă, nu o probabilitate calibrată.')
    // The PNG card follows the same convention.
    expect(read('app/proof/_shared/proofCard.tsx')).toContain('label="SIGNAL SCORE"')
    const fmt = read('app/proof/_shared/format.ts')
    expect(fmt).toContain('/ 100`')
    expect(fmt).not.toContain('}%`')
  })

  it('Explore joins commitments by fixture id from the claims authority', () => {
    const src = read('app/explore/ExploreContent.tsx')
    // One list lookup, joined client-side. Never per-card, never hardcoded.
    expect(src).toContain("/api/proof/claims/?limit=200")
    expect(src).toContain('map.set(claim.fixture_id')
    expect(src).not.toMatch(/Cardiff/i)
    expect(rendered('app/explore/ExploreContent.tsx')).not.toMatch(
      /['"][0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}['"]/i,
    )
  })

  it('the marker renders ONLY for committed fixtures, in both languages', () => {
    const src = read('app/explore/ExploreContent.tsx')
    expect(src).toContain('commitments.has(fixture.fixture_id) && (')
    expect(src).toContain("language === 'ro' ? 'ANGAJAMENT PUBLIC' : 'PUBLIC COMMITMENT'")
    expect(src).toContain("language === 'ro' ? 'Vezi dovada' : 'View proof'")
  })

  it('states the dual-state distinction without a quality claim', () => {
    const src = read('app/explore/ExploreContent.tsx')
    expect(src).toContain(
      'The live signal may continue to change. The public commitment preserves the state BetGlitch committed to before kickoff.',
    )
    expect(src).toContain(
      'Semnalul live poate continua să se schimbe. Angajamentul public păstrează starea la care BetGlitch s-a angajat înainte de start.',
    )
    // No better/stronger/value wording around the marker.
    const scan = rendered('app/explore/ExploreContent.tsx').toLowerCase()
    for (const banned of ['stronger signal', 'best commitment', 'top commitment', 'recommended commitment']) {
      expect(scan).not.toContain(banned)
    }
  })

  it('live and committed remain visually distinct treatments', () => {
    const src = read('app/explore/ExploreContent.tsx')
    // Dashed sky = mutable live signal; solid indigo = frozen commitment.
    expect(src).toContain('border-sky-200 bg-sky-50')
    expect(src).toContain('border-solid border-indigo-500')
  })
})

describe('the homepage funnel strip makes 1 commitment look normal', () => {
  const src = read('app/page.tsx')

  it('shows all three counters side by side, each linking to its stage', () => {
    expect(src).toContain('terms.liveSignal.plural')
    expect(src).toContain('terms.publicCommitment.plural')
    expect(src).toContain('terms.verifiedRecord.label')
    expect(src).toContain('/track-record#public-commitments')
  })

  it('counts pending commitments from the claims authority, never the feed', () => {
    expect(src).toContain("/api/proof/claims/")
    expect(src).toContain("claim_state === 'PENDING'")
  })
})
