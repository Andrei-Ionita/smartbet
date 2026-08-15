import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import {
  competitionById,
  competitionOptionLabel,
  EXPLORE_LEAGUE_OPTIONS,
  publicCompetitionLabel,
  ROMANIAN_SUPERLIGA,
  SEARCHABLE_COMPETITIONS,
  SIGNAL_COMPETITION_IDS,
} from '../coverage'

describe('competition identity', () => {
  it.each([
    [271, 'Danish Superliga', 'Denmark'],
    [474, 'Romanian SuperLiga', 'Romania'],
    [609, 'Ukrainian Premier League', 'Ukraine'],
  ])('identifies SportMonks league %i without ambiguous provider naming', (id, name, country) => {
    expect(competitionById(id)).toMatchObject({ name, country })
    expect(publicCompetitionLabel(id)).toBe(`${name} — ${country}`)
  })

  it('gives every active competition a country-explicit Explore label', () => {
    const activeOptions = EXPLORE_LEAGUE_OPTIONS.filter(({ id }) => id)
    expect(activeOptions).toHaveLength(SEARCHABLE_COMPETITIONS.length)
    for (const option of activeOptions) {
      expect(option.country).not.toBe('')
      expect(option.label).toBe(`${option.name} — ${option.country}`)
      expect(competitionOptionLabel(option, 'en')).toBe(option.label)
    }
    expect(competitionOptionLabel(EXPLORE_LEAGUE_OPTIONS[0], 'ro')).toBe('Toate competițiile')
    expect(publicCompetitionLabel(271, '', 'ro')).toBe('Danish Superliga — Danemarca')
    expect(publicCompetitionLabel(609, '', 'ro')).toBe('Ukrainian Premier League — Ucraina')
    expect(publicCompetitionLabel(474, '', 'ro')).toBe('Romanian SuperLiga — România')
  })

  it('replaces Russia with the Romanian SuperLiga in search and signals', () => {
    expect(ROMANIAN_SUPERLIGA).toMatchObject({
      id: 474,
      providerName: 'Liga 1',
      country: 'Romania',
      configured: true,
      providerEntitlementVerified: true,
      providerPayloadsVerified: true,
    })
    expect(SEARCHABLE_COMPETITIONS.some(({ id }) => Number(id) === 474)).toBe(true)
    expect(SIGNAL_COMPETITION_IDS).toContain(474)
    expect(SEARCHABLE_COMPETITIONS.some(({ id }) => Number(id) === 486)).toBe(false)
    expect(SIGNAL_COMPETITION_IDS).not.toContain(486)
  })

  it('normalises the provider league name in full fixture workspaces', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/services/fixtureService.ts'), 'utf8')
    expect(source).toContain("import { publicCompetitionLabel } from '@/app/lib/coverage'")
    expect(source).toContain('league: publicCompetitionLabel(')
    expect(source).toContain('league_id: leagueId')
  })

  it('contains no old ambiguous public competition placeholders', () => {
    const names = SEARCHABLE_COMPETITIONS.map(({ name }) => name)
    expect(names).not.toContain('Superliga')
    expect(names).not.toContain('Premier League (Additional)')
    expect(names).not.toContain('Premier League (additional)')
    expect(names).not.toContain('Premiership')
    expect(names).not.toContain('Pro League')
    expect(names).not.toContain('Super League')
  })
})
