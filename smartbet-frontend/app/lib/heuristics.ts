/**
 * The CURRENT BetGlitch heuristic layer, extracted verbatim.
 *
 * Shared by the public recommendation route and the internal evidence feed so
 * "Variant B" is literally the live transformation rather than a
 * reimplementation of it. A second copy would drift, and the entire point of
 * the A-vs-B experiment is that B is exactly what production does today.
 *
 * NOTE ON WHAT THESE NUMBERS ARE
 * ------------------------------
 * calculateFormMomentum returns a multiplier applied to ONE outcome's
 * probability without renormalising the rest of the market vector, and the
 * result is capped at 0.95. The output is therefore NOT a probability and must
 * never be presented as one — see the 2026-08-04 calibration audit.
 */

export function calculateMarketScore(probabilityGap: number, expectedValue: number, confidence: number): number {
  // Normalize values to 0-1 scale
  const normalizedGap = Math.min(probabilityGap, 0.5) / 0.5  // Cap at 50% gap
  const normalizedEV = Math.min(Math.max(expectedValue, 0), 0.5) / 0.5  // Cap at 50% EV
  const normalizedConf = confidence  // Already 0-1

  return (normalizedGap * 0.4) + (normalizedEV * 0.3) + (normalizedConf * 0.3)
}

// ============= ACCURACY ENHANCEMENT #1: Form Momentum Adjustment =============
// Analyzes recent team form (W/D/L) and returns a multiplier for confidence
// If form strongly aligns with prediction: boost (+5% to +10%)
// If form contradicts prediction: reduce (-5% to -15%)
export function calculateFormMomentum(
  teamForm: string,
  isHome: boolean,
  predictedForThisTeam: boolean
): { multiplier: number; reason: string } {
  if (!teamForm || teamForm === '?????' || teamForm.length < 3) {
    return { multiplier: 1.0, reason: 'No form data' }
  }

  // Parse form string (e.g., "WWDLW" -> most recent first)
  const formArray = teamForm.toUpperCase().slice(0, 5).split('')
  const wins = formArray.filter(f => f === 'W').length
  const draws = formArray.filter(f => f === 'D').length
  const losses = formArray.filter(f => f === 'L').length

  // Calculate momentum score: recent results weighted more heavily
  // Format: most recent = index 0
  let momentumScore = 0
  const weights = [0.30, 0.25, 0.20, 0.15, 0.10] // Most recent weighted highest

  formArray.forEach((result, idx) => {
    const weight = weights[idx] || 0.10
    if (result === 'W') momentumScore += weight
    else if (result === 'L') momentumScore -= weight
    // Draws are neutral (0)
  })

  // momentumScore ranges from -1.0 (all losses) to +1.0 (all wins)

  if (predictedForThisTeam) {
    // We're predicting this team to win/be part of winning outcome
    if (momentumScore >= 0.5) {
      // Strong positive momentum aligns with prediction
      return {
        multiplier: 1.08,
        reason: `${isHome ? 'Home' : 'Away'} on hot streak (${wins}W in last 5)`
      }
    } else if (momentumScore >= 0.2) {
      return { multiplier: 1.04, reason: `${isHome ? 'Home' : 'Away'} in decent form` }
    } else if (momentumScore <= -0.3) {
      // Predicting a team that's struggling - reduce confidence
      return {
        multiplier: 0.92,
        reason: `${isHome ? 'Home' : 'Away'} struggling (${losses}L in last 5)`
      }
    } else if (momentumScore <= -0.5) {
      return {
        multiplier: 0.85,
        reason: `${isHome ? 'Home' : 'Away'} on cold streak`
      }
    }
  } else {
    // We're predicting AGAINST this team
    if (momentumScore <= -0.5) {
      // Team is struggling, aligns with our prediction against them
      return { multiplier: 1.06, reason: `${isHome ? 'Home' : 'Away'} on losing run` }
    } else if (momentumScore >= 0.5) {
      // Predicting against a team on fire - risky, reduce confidence
      return {
        multiplier: 0.90,
        reason: `Warning: ${isHome ? 'Home' : 'Away'} in strong form`
      }
    }
  }

  return { multiplier: 1.0, reason: 'Form is mixed' }
}

// ============= ACCURACY ENHANCEMENT #2: Value Zone Filtering =============
// Flags EV values that are suspiciously high (often odds errors or traps)
// Returns adjusted EV and a flag
export function evaluateValueZone(ev: number): {
  adjustedEV: number
  zone: 'optimal' | 'good' | 'suspicious' | 'trap'
  warning: string | null
  scorePenalty: number
} {
  // EV is in decimal form (0.05 = 5%)
  const evPercent = ev * 100

  if (evPercent >= 5 && evPercent <= 15) {
    // Optimal value zone - this is where sustainable profits come from
    return {
      adjustedEV: ev,
      zone: 'optimal',
      warning: null,
      scorePenalty: 0
    }
  } else if (evPercent > 15 && evPercent <= 25) {
    // Good but slightly suspicious - could be real value or pricing error
    return {
      adjustedEV: ev * 0.95, // Slight reduction
      zone: 'good',
      warning: 'High EV - verify odds are accurate',
      scorePenalty: 0.05
    }
  } else if (evPercent > 25 && evPercent <= 40) {
    // Suspicious - likely odds error or trap
    return {
      adjustedEV: ev * 0.85,
      zone: 'suspicious',
      warning: 'Unusually high EV - possible odds error',
      scorePenalty: 0.15
    }
  } else if (evPercent > 40) {
    // Almost certainly an error or trap market
    return {
      adjustedEV: Math.min(ev * 0.7, 0.20), // Cap at 20% adjusted EV
      zone: 'trap',
      warning: 'Extreme EV detected - likely odds error, proceed with caution',
      scorePenalty: 0.30
    }
  }

  // EV below 5% - standard processing
  return {
    adjustedEV: ev,
    zone: 'optimal',
    warning: null,
    scorePenalty: 0
  }
}
