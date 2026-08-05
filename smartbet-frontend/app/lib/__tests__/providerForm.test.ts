/**
 * The canonical form parser, against the SHAPE PRODUCTION ACTUALLY RETURNS.
 *
 * The fixtures below are the sanitised structure captured from
 * standings/seasons/{id}?include=form on 2026-08-05 — an array of one-letter
 * results with sort_order, not a string. The previous implementation
 * JSON.stringify'd that array and fed it to a parser reading the first five
 * characters for W/D/L, so it always found none and the multiplier collapsed
 * to 1.0.
 */
import { describe, expect, it } from 'vitest'

import {
  buildFormMap,
  formFor,
  MIN_FORM_RESULTS,
  parseStandingForm,
} from '../providerForm'
import { calculateFormMomentum } from '../heuristics'

const providerForm = (letters: string[]) =>
  letters.map((letter, index) => ({
    id: 1000 + index,
    standing_type: 'overall',
    standing_id: 55,
    fixture_id: 9000 + index,
    form: letter,
    sort_order: index + 1,
  }))

describe('parses the real provider structure', () => {
  it('reads an array of one-letter results in sort_order', () => {
    const parsed = parseStandingForm(providerForm(['W', 'W', 'D', 'L', 'W']))
    expect(parsed.letters).toBe('WWDLW')
    expect(parsed.count).toBe(5)
    expect(parsed.available).toBe(true)
    expect(parsed.reason).toBe('')
  })

  it('trusts sort_order over array order', () => {
    const shuffled = [
      { form: 'L', sort_order: 3 },
      { form: 'W', sort_order: 1 },
      { form: 'D', sort_order: 2 },
    ]
    expect(parseStandingForm(shuffled).letters).toBe('WDL')
  })

  it('caps at the five results the momentum weights use', () => {
    const parsed = parseStandingForm(providerForm(['W', 'W', 'W', 'W', 'W', 'L', 'L']))
    expect(parsed.letters).toHaveLength(5)
  })

  it('still accepts a plain string, defensively', () => {
    expect(parseStandingForm('WWDLW').letters).toBe('WWDLW')
  })
})

describe('missing data is reported, never defaulted', () => {
  it.each([
    [null, 'provider_form_unavailable'],
    [undefined, 'provider_form_unavailable'],
    [[], 'provider_form_unavailable'],
    ['', 'provider_form_unavailable'],
  ])('%s -> %s', (raw, reason) => {
    const parsed = parseStandingForm(raw as unknown)
    expect(parsed.available).toBe(false)
    expect(parsed.reason).toBe(reason)
    expect(parsed.letters).toBe('')
  })

  it('flags a malformed structure explicitly rather than guessing', () => {
    expect(parseStandingForm([{ notForm: 'W' }]).reason).toBe('provider_form_parse_error')
    expect(parseStandingForm([42]).reason).toBe('provider_form_parse_error')
    expect(parseStandingForm(123).reason).toBe('provider_form_parse_error')
  })

  it('flags too-few results as incomplete rather than usable', () => {
    const parsed = parseStandingForm(providerForm(['W', 'L']))
    expect(parsed.count).toBe(2)
    expect(parsed.count).toBeLessThan(MIN_FORM_RESULTS)
    expect(parsed.available).toBe(false)
    expect(parsed.reason).toBe('provider_form_incomplete')
  })

  it('distinguishes an unknown team from a team without form', () => {
    const map = buildFormMap([{ data: [{ participant_id: 7, form: providerForm(['W', 'W', 'W']) }] }])
    expect(formFor(map, 7).available).toBe(true)
    expect(formFor(map, 999).reason).toBe('provider_form_unavailable')
    expect(formFor(map, undefined).reason).toBe('fixture_team_mapping_missing')
  })
})

describe('the old implementation was inert — this is why', () => {
  it('JSON.stringify of the real payload yields no usable form', () => {
    const raw = providerForm(['W', 'W', 'D', 'L', 'W'])
    const asOldCodeSawIt = JSON.stringify(raw)     // what the live route passed
    const firstFive = asOldCodeSawIt.slice(0, 5)   // what the momentum read

    expect(firstFive).not.toMatch(/[WDL]/)
    // ...so the multiplier was always exactly 1.0, whatever the team's form.
    expect(calculateFormMomentum(asOldCodeSawIt, true, true).multiplier).toBe(1.0)

    // The canonical parser recovers the real letters from the same payload.
    expect(parseStandingForm(raw).letters).toBe('WWDLW')
    expect(calculateFormMomentum('WWDLW', true, true).multiplier).not.toBe(1.0)
  })

  it('an absent form never silently becomes a 1.0 multiplier in evidence', () => {
    const parsed = parseStandingForm(null)
    expect(parsed.available).toBe(false)
    // Callers must branch on `available`; the letters are empty, so any caller
    // that ignores it gets 'No form data' rather than a fabricated adjustment.
    expect(calculateFormMomentum(parsed.letters, true, true).reason).toBe('No form data')
  })
})

describe('buildFormMap', () => {
  it('keys by participant_id across several standings responses', () => {
    const map = buildFormMap([
      { data: [{ participant_id: 1, form: providerForm(['W', 'W', 'W']) }] },
      { data: [{ participant_id: 2, form: providerForm(['L', 'L', 'L']) }] },
      null,
      { data: [{ participant_id: 3 }] },
    ])
    expect(map.get(1)?.letters).toBe('WWW')
    expect(map.get(2)?.letters).toBe('LLL')
    expect(map.get(3)?.available).toBe(false)
  })

  it('keeps the richest observation when a team appears twice', () => {
    const map = buildFormMap([
      { data: [{ participant_id: 5, form: providerForm(['W', 'D']) }] },
      { data: [{ participant_id: 5, form: providerForm(['W', 'D', 'L', 'W']) }] },
    ])
    expect(map.get(5)?.count).toBe(4)
  })
})
