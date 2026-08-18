export type GemRejectionCategory =
  | 'reliability'
  | 'provider_value'
  | 'cross_market_consensus'
  | 'price_quality'
  | 'other'

export type GemRejectionCounts = Record<GemRejectionCategory, number>

export interface PublicGemRejectionDiagnostic {
  code:
    | 'signal_or_verified_price'
    | 'reliability'
    | 'provider_value'
    | 'cross_market_consensus'
    | 'price_quality'
  fixtures_affected: number
}

export function emptyGemRejectionCounts(): GemRejectionCounts {
  return {
    reliability: 0,
    provider_value: 0,
    cross_market_consensus: 0,
    price_quality: 0,
    other: 0,
  }
}

export function categorizeGemRejectionReason(reason: string): GemRejectionCategory {
  if (reason.startsWith('fixture_') || reason.startsWith('league_')) {
    return 'reliability'
  }
  if (reason.startsWith('provider_')) return 'provider_value'
  if (
    reason.startsWith('correct_score_') ||
    reason.startsWith('double_chance_') ||
    reason.startsWith('cross_market_')
  ) {
    return 'cross_market_consensus'
  }
  if (
    reason.startsWith('canonical_price_') ||
    reason === 'insufficient_bookmaker_coverage' ||
    reason.startsWith('price_')
  ) {
    return 'price_quality'
  }
  return 'other'
}

/**
 * Count each affected fixture once per category. A fixture can legitimately
 * fail several categories, so category totals are explicitly non-exclusive.
 */
export function recordGemRejection(
  counts: GemRejectionCounts,
  reasons: string[],
): void {
  const categories = new Set<GemRejectionCategory>(
    reasons.map(categorizeGemRejectionReason),
  )
  categories.forEach((category) => {
    counts[category] += 1
  })
}

export function publicGemRejectionBreakdown(
  signalOrPriceFailures: number,
  counts: GemRejectionCounts,
): PublicGemRejectionDiagnostic[] {
  return [
    {
      code: 'signal_or_verified_price',
      fixtures_affected: Math.max(0, signalOrPriceFailures),
    },
    { code: 'reliability', fixtures_affected: counts.reliability },
    { code: 'provider_value', fixtures_affected: counts.provider_value },
    {
      code: 'cross_market_consensus',
      fixtures_affected: counts.cross_market_consensus,
    },
    { code: 'price_quality', fixtures_affected: counts.price_quality },
  ]
}
