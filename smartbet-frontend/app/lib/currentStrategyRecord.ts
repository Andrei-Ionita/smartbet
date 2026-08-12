import { RANKING_VERSION } from './rankingPolicy'

export const CURRENT_STRATEGY_VERSION = RANKING_VERSION
export const FLAT_STAKE = 10

export interface StrategyClaim {
  ranking_version: string | null
  claim_state: 'PENDING' | 'WON' | 'LOST' | 'VOID' | 'CANCELLED'
  counts_towards_verified_record: boolean
  odds: number
}

export interface StrategyRecordSummary {
  published: number
  pending: number
  finished: number
  counted: number
  excluded: number
  won: number
  lost: number
  totalStaked: number
  profit: number
  roiPercent: number | null
}

/**
 * The public record is versioned. A result from an earlier selection policy is
 * useful history, but it is not evidence for the strategy visitors see today.
 */
export function isCurrentStrategyClaim(claim: StrategyClaim) {
  return claim.ranking_version === CURRENT_STRATEGY_VERSION
}

export function partitionStrategyClaims<T extends StrategyClaim>(claims: T[]) {
  return {
    current: claims.filter(isCurrentStrategyClaim),
    historical: claims.filter((claim) => !isCurrentStrategyClaim(claim)),
  }
}

export function summarizeStrategyRecord(
  claims: StrategyClaim[],
  stake = FLAT_STAKE,
): StrategyRecordSummary {
  const pending = claims.filter((claim) => claim.claim_state === 'PENDING').length
  const finishedClaims = claims.filter((claim) => claim.claim_state !== 'PENDING')
  const countedClaims = claims.filter(
    (claim) =>
      claim.counts_towards_verified_record &&
      (claim.claim_state === 'WON' || claim.claim_state === 'LOST'),
  )
  const won = countedClaims.filter((claim) => claim.claim_state === 'WON').length
  const lost = countedClaims.filter((claim) => claim.claim_state === 'LOST').length
  const profit = countedClaims.reduce(
    (total, claim) =>
      total + (claim.claim_state === 'WON' ? stake * (claim.odds - 1) : -stake),
    0,
  )
  const roundedProfit = Math.round(profit * 100) / 100
  const totalStaked = countedClaims.length * stake

  return {
    published: claims.length,
    pending,
    finished: finishedClaims.length,
    counted: countedClaims.length,
    excluded: finishedClaims.length - countedClaims.length,
    won,
    lost,
    totalStaked,
    profit: roundedProfit,
    roiPercent:
      totalStaked > 0 ? Math.round((roundedProfit / totalStaked) * 1000) / 10 : null,
  }
}
