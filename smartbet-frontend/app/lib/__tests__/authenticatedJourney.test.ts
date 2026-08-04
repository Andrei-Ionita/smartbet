/**
 * Contracts established by the authenticated user-journey verification pass.
 *
 * Every assertion here corresponds to a defect observed on betglitch.com while
 * signed in with the language switcher set to Romanian: the dashboard chrome
 * stayed English regardless of language, because the strings were hardcoded in
 * JSX and because the two components that carry their own copy — StatusBadge
 * and EmptyState — were rendered without a `lang`.
 *
 * Source scans rather than renders, matching terminology.test.ts: the suite has
 * no DOM, and scanning catches a regression in any branch rather than only the
 * one a render happens to exercise.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { getCopy } from '../terminology'
import type { EmptyStateKey } from '../../components/EmptyState'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

describe('dashboard chrome is bilingual', () => {
  const src = read('app/dashboard/page.tsx')

  it('renders the heading, bankroll link and record copy from terminology', () => {
    expect(src).toContain('{copy.dashboard.title}')
    expect(src).toContain('{copy.dashboard.manageBankroll}')
    expect(src).toContain('{copy.dashboard.recordBuilding}')
  })

  it('has no hardcoded English left in that chrome', () => {
    // These exact strings shipped to Romanian visitors.
    expect(src).not.toContain('Your dashboard\n')
    expect(src).not.toContain('Manage bankroll\n')
    expect(src).not.toContain('The verified record is being built')
  })

  it('passes the visitor language to every StatusBadge', () => {
    const badges = src.match(/<StatusBadge[^>]*>/g) ?? []
    expect(badges.length).toBeGreaterThan(0)
    for (const badge of badges) {
      expect(badge).toContain('lang={language}')
    }
  })

  it('passes the visitor language to EmptyState', () => {
    expect(src).toContain('<EmptyState state="first_dashboard" lang={language} />')
  })
})

describe('terminology carries both languages for the dashboard', () => {
  const en = getCopy('en')
  const ro = getCopy('ro')

  it('defines every dashboard string in each language', () => {
    for (const key of ['title', 'manageBankroll', 'recordBuilding'] as const) {
      expect(en.dashboard[key].length).toBeGreaterThan(0)
      expect(ro.dashboard[key].length).toBeGreaterThan(0)
    }
  })

  it('does not ship English as the Romanian wording', () => {
    expect(ro.dashboard.title).not.toBe(en.dashboard.title)
    expect(ro.dashboard.manageBankroll).not.toBe(en.dashboard.manageBankroll)
    expect(ro.dashboard.recordBuilding).not.toBe(en.dashboard.recordBuilding)
  })
})

describe('EmptyState translates every state it can render', () => {
  const src = read('app/components/EmptyState.tsx')

  it('keeps English as the default so provider-less callers still work', () => {
    expect(src).toContain("lang = 'en'")
  })

  it('covers each EmptyStateKey in Romanian', () => {
    // Parsed from the source so a newly added state cannot skip translation.
    const keys = (src.match(/^  \| '([a-z_]+)'$/gm) ?? [])
      .map((line) => line.replace(/[^a-z_]/g, ''))
    const firstKey = src.match(/export type EmptyStateKey\s*=\s*\n?\s*\| '([a-z_]+)'/)
    if (firstKey) keys.push(firstKey[1])
    const all = Array.from(new Set(keys)) as EmptyStateKey[]
    expect(all.length).toBeGreaterThanOrEqual(8)

    const roBlock = src.slice(src.indexOf('const RO_WORDS'))
    for (const key of all) {
      expect(roBlock).toContain(`${key}: {`)
    }
  })

  it('overlays only wording, leaving destinations shared', () => {
    // href lives in SPECS alone; a Romanian visitor must not be routed
    // somewhere different from an English one.
    const roBlock = src.slice(src.indexOf('const RO_WORDS'), src.indexOf('export function EmptyState'))
    expect(roBlock).not.toContain('href')
  })
})
