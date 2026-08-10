/**
 * Public-language contract for the evidence system.
 *
 * PublishedClaim remains the backend object. Visitors only need three plain
 * ideas: live analysis can change; a published pick is locked before kickoff;
 * results keep wins and losses visible. Technical proof stays optional.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { getCopy } from '../terminology'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
const en = getCopy('en')
const ro = getCopy('ro')

describe('plain public vocabulary', () => {
  it('names live signals, published picks and results in both languages', () => {
    expect(en.terms.liveSignal.label).toBe('Live signal')
    expect(en.terms.publicCommitment.label).toBe('Published pick')
    expect(en.terms.verifiedRecord.label).toBe('Results')
    expect(ro.terms.liveSignal.label).toBe('Semnal live')
    expect(ro.terms.publicCommitment.label).toBe('Selecție publicată')
    expect(ro.terms.verifiedRecord.label).toBe('Rezultate')
  })

  it('states both the lock and its limit', () => {
    expect(en.terms.publicCommitment.definition).toContain('locked before kickoff')
    expect(en.terms.publicCommitment.notARecommendation).toContain('does not mean')
    expect(en.terms.publicCommitment.notARecommendation).toContain('guaranteed')
    expect(ro.terms.publicCommitment.notARecommendation).toContain('Nu înseamnă')
  })

  it('does not count pending picks as results', () => {
    expect(en.record.publishedNotCounted).toContain('not counted yet')
    expect(en.record.publishedStates).toContain('Pending picks do not count')
    expect(en.record.verifiedFromCommitments).toContain('settled picks only')
  })
})

describe('homepage simplification', () => {
  const src = read('app/page.tsx')

  it('teaches one direct trust promise', () => {
    expect(en.home.differenceHeading).toBe('Published before kickoff. Visible after the result.')
    expect(en.home.differenceBody).toContain('cannot add it after the match')
    expect(src).toContain('copy.home.differenceHeading')
    expect(src).toContain('/track-record#published-picks')
  })

  it('removes the three-stage counter funnel', () => {
    expect(src).not.toContain('pendingCommitments')
    expect(src).not.toContain('terms.publicCommitment.plural')
    expect(src).not.toContain('/api/proof/claims/')
  })
})

describe('results page', () => {
  const src = read('app/track-record/TrackRecordContent.tsx')

  it('keeps new and legacy anchors working', () => {
    for (const id of ['published-picks', 'public-commitments', 'results', 'verified-record']) {
      expect(src).toContain(`id="${id}"`)
    }
  })

  it('renders every stored pick consistently', () => {
    expect(src).toContain('{claims.map((claim) => (')
    expect(src).toContain('claim.counts_towards_verified_record')
    expect(src).not.toMatch(/Cardiff/i)
  })

  it('moves methodology and price-age fields behind verification details', () => {
    expect(src).toContain("'Verification details'")
    expect(src).toContain('rec.publishedPriceAgeLabel')
    expect(src).toContain('rec.publishedVersionLabel')
    expect(src).toContain('<details')
  })

  it('keeps the publication policy factual', () => {
    expect(en.record.policyBody).toContain('published automatically')
    expect(en.record.policyBody).toContain('at least six hours')
    expect(en.record.policyBody).toContain('not that it is guaranteed')
    for (const banned of ['strongest signal', 'best value', 'highest confidence']) {
      expect(en.record.policyBody.toLowerCase()).not.toContain(banned)
    }
  })
})

describe('proof page', () => {
  const src = read('app/proof/_shared/ProofPageBody.tsx')

  it('leads with the simple customer promise', () => {
    expect(src).toContain('published and locked before kickoff')
    expect(src).toContain('cannot add')
    expect(src).toContain('remove it when it loses')
  })

  it('keeps hashes, versions and timestamps under optional details', () => {
    expect(src).toContain('Verification details')
    expect(src.indexOf('<details')).toBeLessThan(src.indexOf('SHA-256'))
    for (const field of ['claim_hash', 'ranking_version', 'published_at', 'formatOdds']) {
      expect(src).toContain(field)
    }
  })
})

describe('fixture surfaces', () => {
  it('marks a published fixture without the commitment jargon', () => {
    const explore = read('app/explore/ExploreContent.tsx')
    const workspace = read('app/components/FixtureDecisionWorkspace.tsx')
    expect(explore).toContain("ro ? 'Selecție blocată' : 'Locked pick'")
    expect(workspace).toContain("ro ? 'VEZI SELECȚIA BLOCATĂ' : 'VIEW LOCKED PICK'")
    expect(workspace).toContain('This published pick was locked before kickoff')
  })
})
