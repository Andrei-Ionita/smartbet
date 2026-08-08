import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

/**
 * Independent timestamping, honestly presented.
 *
 * A skeptical reviewer (2026-08-08) refused to accept BetGlitch's own SHA-256
 * as proof, correctly: we compute the hash, we serve the record, so the hash
 * shows tamper-evidence and nothing about WHEN the record existed. The answer
 * is an external Bitcoin-anchored timestamp — but the copy around it is now
 * itself a claim, so these tests pin that it never overstates.
 */

const root = join(__dirname, '..', '..', '..')
const read = (p: string) => readFileSync(join(root, p), 'utf-8').replace(/\r\n/g, '\n')

const ANCHORS_PAGE = read('app/proof/anchors/page.tsx')
const PROOF_BODY = read('app/proof/_shared/ProofPageBody.tsx')

describe('the proof page reports real anchor state, never an assumed one', () => {
  it('branches on the payload instead of asserting a status', () => {
    expect(PROOF_BODY).toContain('data.anchor ?')
    expect(PROOF_BODY).toContain("data.anchor.status === 'CONFIRMED'")
  })

  it('shows "not anchored yet" rather than hiding the absence', () => {
    expect(PROOF_BODY).toContain('has not been externally timestamped yet')
  })

  it('still states plainly what a self-hosted hash cannot prove', () => {
    expect(PROOF_BODY).toContain('BetGlitch serves both the record')
  })

  it('warns loudly if the claim diverges from what was timestamped', () => {
    expect(PROOF_BODY).toContain('!data.anchor.matches_current_hash')
    expect(PROOF_BODY).toContain('no longer matches the hash that was timestamped')
  })

  it('never claims anchoring is live as a static sentence', () => {
    // The interim copy said anchoring was "not live yet". Once shipped, a
    // hardcoded sentence in either direction is a lie waiting to happen.
    expect(PROOF_BODY).not.toContain('anchoring is not live yet')
  })
})

describe('the anchors page tells the reader how to check without us', () => {
  it('publishes the verification procedure, including the ots command', () => {
    expect(ANCHORS_PAGE).toContain('ots verify --digest')
    expect(ANCHORS_PAGE).toContain('/api/proof/claims/')
  })

  it('explains why the timing matters', () => {
    expect(ANCHORS_PAGE).toContain('before kickoff')
    expect(ANCHORS_PAGE).toContain('immediately')
  })

  it('states the limit of the proof — it is not a claim of being right', () => {
    expect(ANCHORS_PAGE).toContain('does <strong>not</strong> prove')
    // Collapse JSX line wrapping before matching prose.
    const prose = ANCHORS_PAGE.replace(/\s+/g, ' ')
    expect(prose).toContain('never whether we were right')
    expect(prose).toContain('prove: that a commitment was a good bet')
  })

  it('offers the raw proof and the exact manifest for download', () => {
    expect(ANCHORS_PAGE).toContain('Download .ots proof')
    expect(ANCHORS_PAGE).toContain('View manifest')
  })

  it('handles the empty and failed states without implying coverage', () => {
    expect(ANCHORS_PAGE).toContain('No commitments have been anchored yet')
    expect(ANCHORS_PAGE).toContain('could not be loaded')
  })
})

describe('the verified record links to the independent proof', () => {
  it('offers the anchors page in both languages', () => {
    const src = read('app/track-record/TrackRecordContent.tsx')
    expect(src).toContain('/proof/anchors')
    expect(src).toContain('Independent timestamps — verify them yourself')
    expect(src).toContain('Marcaje de timp independente')
  })
})
