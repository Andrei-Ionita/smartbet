/**
 * The recommendation card's semantic contract.
 *
 * The card previously asserted things the product cannot support: a "Model
 * score" of "59.2%" (a ranking presented as a probability), "low variance
 * across models" (there is one provider model and no variance), a RECOMMENDED
 * badge and a Speculative badge (both relative to a calibration standard that
 * does not exist), and an active stake calculator on a signal whose value
 * cannot be assessed.
 *
 * Source scan, matching the rest of the suite: no DOM here, and scanning
 * catches a regression in any branch rather than only a rendered one.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
const CARD = read('app/components/RecommendationCard.tsx')
/** Rendered code only: comments legitimately name the claims they removed. */
const CARD_CODE = CARD
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .split('\n')
  .map((line) => line.replace(/\/\/.*$/, ''))
  .join('\n')

describe('signal terminology replaces model terminology', () => {
  it('says Signal score, in both languages', () => {
    expect(CARD).toContain("'Scor semnal' : 'Signal score'")
    expect(CARD).not.toContain("'Scor model' : 'Model score'")
  })

  it('renders the score as N / 100, never as a percentage', () => {
    expect(CARD).toContain('/ 100')
    // The old render was `{Math.round(confidence * 100)}` followed by a bare
    // label; a '%' beside the score would read as a calibrated probability.
    expect(CARD).not.toMatch(/confidence \* 100\)\}%/)
    expect(CARD).not.toMatch(/confidence \* 100\)\.toFixed\(1\)\}%/)
  })

  it('states the disclaimer in both languages', () => {
    expect(CARD).toContain(
      'A signal score ranks BetGlitch’s relative preference among the available outcomes. It is not a calibrated probability.',
    )
    expect(CARD).toContain(
      'Scorul de semnal clasifică preferința relativă a BetGlitch între rezultatele disponibile. Nu este o probabilitate calibrată.',
    )
  })

  it('labels the selection as the highest-ranked outcome', () => {
    expect(CARD).toContain("'Rezultatul cel mai bine clasat'")
    expect(CARD).toContain("'Highest-ranked outcome'")
  })
})

describe('no ensemble, consensus or model-agreement language remains', () => {
  it.each([
    'low variance across models',
    'varianță scăzută între modele',
    'AI models',
    'modele AI',
    'model agreement',
    'consensus',
    'all AI models agree',
  ])('does not contain %s', (phrase) => {
    expect(CARD_CODE.toLowerCase()).not.toContain(phrase.toLowerCase())
  })
})

describe('card-state matrix', () => {
  it('derives state solely from verified-price availability', () => {
    expect(CARD).toContain(
      "const cardState: 'signal_only' | 'verified_price' =\n    priceVerified ? 'verified_price' : 'signal_only'",
    )
  })

  it('renders SIGNAL ONLY when no verified price exists', () => {
    expect(CARD).toContain("'DOAR SEMNAL' : 'SIGNAL ONLY'")
    expect(CARD).toContain("'Nu poate fi evaluată' : 'Cannot be assessed'")
    expect(CARD).toContain(
      'This outcome ranks above the other available outcomes, but BetGlitch cannot assess betting value without a verified market price.',
    )
  })

  it('renders VERIFIED MARKET PRICE with value not yet assessed', () => {
    expect(CARD).toContain("'PREȚ DE PIAȚĂ VERIFICAT' : 'VERIFIED MARKET PRICE'")
    expect(CARD).toContain("'Neevaluată încă' : 'Not yet assessed'")
    expect(CARD).toContain(
      'The market price has been verified, but BetGlitch does not yet have sufficient calibration evidence to determine whether the price offers value.',
    )
  })

  it('renders the two states differently', () => {
    expect(CARD).toContain("cardState === 'verified_price' ? 'text-blue-700' : 'text-amber-700'")
    expect(CARD).toContain(
      "cardState === 'verified_price'\n                  ? 'border-gray-200 bg-gray-50'\n                  : 'border-amber-200 bg-amber-50'",
    )
  })
})

describe('no unsupported quality claims', () => {
  it('shows no RECOMMENDED or Speculative badge', () => {
    expect(CARD_CODE).not.toContain('card.badges.speculative')
    expect(CARD_CODE).not.toContain("t('card.badges.premium')")
    // The badge slot now renders the state, not a quality ladder.
    expect(CARD).toContain('{stateCopy.status}')
  })

  it('introduces no BET/NO-BET, fair odds or minimum acceptable odds', () => {
    for (const banned of [
      'NO_BET', 'PRICE_QUALIFIES', 'fair_odds', 'fair odds',
      'minimum_acceptable_odds', 'minimum acceptable odds',
      'calibrated_probability', 'conservative_probability',
    ]) {
      expect(CARD).not.toContain(banned)
    }
  })

  it('keeps Variant A as the public signal — no heuristic fields', () => {
    for (const banned of [
      'shadow_adjusted_probability', 'form_multiplier', 'form_inputs',
      'live_activation', 'FORM_HEURISTIC_LIVE_ENABLED', 'modelActivation',
    ]) {
      expect(CARD).not.toContain(banned)
    }
  })
})

describe('stake CTA is absent while value cannot be assessed', () => {
  it('no longer opens the stake calculator from the card header', () => {
    expect(CARD).not.toContain("t('card.stake.calculate')")
    expect(CARD).not.toContain('onClick={() => setIsCalculatorOpen(true)}')
  })

  it('offers a neutral action instead of a dead disabled button', () => {
    expect(CARD).toContain("'Vezi detaliile semnalului' : 'View signal details'")
    expect(CARD).toContain('min-h-[44px]')
  })
})

describe('why this signal', () => {
  it('is renamed and evidenced', () => {
    expect(CARD).toContain("'De ce acest semnal' : 'Why this signal'")
    expect(CARD).not.toContain("'De ce această predicție' : 'Why This Pick'")
  })

  it('reports price status as a reason, in both languages', () => {
    expect(CARD).toContain('Market price verified, with complete provenance')
    expect(CARD).toContain('No verified price for this market — value cannot be assessed')
    expect(CARD).toContain('Preț de piață verificat, cu proveniență completă')
  })
})

describe('unverified quotes are informational', () => {
  it('labels them explicitly in both languages', () => {
    expect(CARD).toContain('Unverified market quotes — informational only')
    expect(CARD).toContain('Cote de piață neverificate — doar informativ')
  })

  it('mutes them rather than presenting them as executable', () => {
    expect(CARD).not.toContain(
      "<div className=\"text-lg font-bold text-gray-900\">{recommendation.odds_data.home?.toFixed(2) || '-'}</div>",
    )
    expect(CARD).toContain('text-lg font-semibold text-gray-500')
  })
})

describe('the expanded analysis is fully bilingual and inside the brand', () => {
  /*
   * 2026-08-07 brand-consistency cleanup. The Romanian drill-down was quoting
   * English fragments ("Match Dynamics: Strong favorite with 28.0%
   * advantage", the API's English `explanation` under a Romanian heading),
   * and two DEAD blocks — gated on fields the public DTO never carries —
   * would have rendered "AI vs Market", a value-opportunity caption and a
   * fabricated "Trading Volume" if those fields ever returned.
   */
  it.each([
    // The retired English-only verdict ladder for the probability gap.
    'Match Dynamics',
    'Clear favorite',
    'Strong favorite',
    'Moderate favorite',
    // The dead market-indicators grid and its banned vocabulary.
    'market_indicators',
    'AI vs Market',
    'Market Favorite',
    'Trading Volume',
    'value_opportunity',
    // The dead league-accuracy grade.
    'league_accuracy',
    'accuracy_percent',
  ])('rendered code no longer contains %s', (phrase) => {
    expect(CARD_CODE).not.toContain(phrase)
  })

  it('does not quote the API explanation string (it is English-only)', () => {
    expect(CARD_CODE).not.toContain('{recommendation.explanation}')
  })

  it('states the probability gap in both languages, as a fact not a verdict', () => {
    expect(CARD).toContain("'Diferența de probabilitate:' : 'Probability gap:'")
    expect(CARD).toContain('the leading outcome sits ${gap} points above the next')
    expect(CARD).toContain('primul rezultat este cu ${gap} puncte peste următorul')
  })

  it('builds the signal summary locally in both languages', () => {
    expect(CARD).toContain('`Rezultatul cel mai bine clasat: ${selection}.`')
    expect(CARD).toContain('`Highest-ranked outcome: ${selection}.`')
  })

  it("renders 'What we don't know' in both languages from real state only", () => {
    expect(CARD).toContain("'Ce nu știm' : \"What we don't know\"")
    expect(CARD).toContain('There is not yet enough calibration evidence')
    expect(CARD).toContain('Nu există încă suficiente dovezi de calibrare')
  })
})

describe('accessibility', () => {
  it('describes the score as a ranking, not a recommendation', () => {
    expect(CARD).toContain('A relative ranking, not a calibrated probability.')
    expect(CARD).toContain('Clasare relativă, nu o probabilitate calibrată.')
  })

  it('conveys state as text, not colour alone', () => {
    // Both status and value-status render readable strings.
    expect(CARD).toContain('{stateCopy.status}')
    // The value status flows through the state badge's description.
    expect(CARD).toContain('description: stateCopy.value')
    expect(CARD).toContain('{stateCopy.panelTitle}')
  })

  it('states value status ONCE on the collapsed card, not as a stack of caveats', () => {
    // The separate "Value status:" line was consolidated into the state badge
    // + state panel on 2026-08-08 after a first-visitor review read the
    // repeated caveats as noise. Reintroducing it re-creates the stack.
    expect(CARD).not.toContain("'Statut valoare' : 'Value status'")
  })

  it('tells the reader what a signal is FOR, in both languages', () => {
    expect(CARD).toContain('Use it as a starting point for your own read')
    expect(CARD).toContain('Folosește-l ca punct de plecare')
  })
})
