import { describe, expect, it } from 'vitest'

import {
  CURRENT_STRATEGY_VERSION,
  partitionStrategyClaims,
  summarizeStrategyRecord,
} from '../currentStrategyRecord'

const claim = (
  state: 'PENDING' | 'WON' | 'LOST' | 'VOID' | 'CANCELLED',
  options: { current?: boolean; counted?: boolean; odds?: number } = {},
) => ({
  ranking_version: options.current === false ? 'retired-strategy' : CURRENT_STRATEGY_VERSION,
  claim_state: state,
  counts_towards_verified_record: options.counted ?? (state === 'WON' || state === 'LOST'),
  odds: options.odds ?? 2,
})

describe('current strategy record', () => {
  it('never lets an earlier methodology validate the current strategy', () => {
    const groups = partitionStrategyClaims([
      claim('WON'),
      claim('LOST', { current: false }),
      claim('PENDING', { current: false }),
    ])

    expect(groups.current).toHaveLength(1)
    expect(groups.historical).toHaveLength(2)
  })

  it('reconciles the current strategy and computes flat-stake return', () => {
    const summary = summarizeStrategyRecord([
      claim('WON', { odds: 2.5 }),
      claim('LOST'),
      claim('PENDING'),
      claim('VOID', { counted: false }),
    ])

    expect(summary).toMatchObject({
      published: 4,
      pending: 1,
      finished: 3,
      counted: 2,
      excluded: 1,
      won: 1,
      lost: 1,
      totalStaked: 20,
      profit: 5,
      roiPercent: 25,
    })
  })

  it('shows no return before the first settled current pick', () => {
    expect(summarizeStrategyRecord([claim('PENDING')])).toMatchObject({
      counted: 0,
      profit: 0,
      roiPercent: null,
    })
  })
})
