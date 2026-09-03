# Selection engine v4 registration — 2026-09-03

## Decision

Register `total-goals-2-5-accuracy-corridor:v4` as a private shadow
experiment. It is not eligible for public selections, Gems, or performance
claims until its forward-only promotion gates pass.

## Evidence used to generate the hypothesis

The public append-only prediction archive supplied one fixed decision per
fixture and market at least one hour before kickoff. The analysis used 464
confirmed, scoreable Over/Under 2.5 decisions from 2026-08-17 through
2026-09-02. Prices were the recorded `lower_median_v1` executable quotes.

The chronological split was 70% older fixtures for screening and 30% newer
fixtures as an untouched holdout. No legacy recommendation or v2 strategy rows
were used.

The registered rule is:

- market: regulation-time Over/Under 2.5;
- the model-selected side has probability at least 60%;
- the de-vigged market also favours that side (probability at least 50%);
- recorded decimal odds are from 1.40 through 1.80;
- the probability and price vectors are complete;
- at least three bookmakers support the price;
- the quote is at most two hours old;
- one decision per fixture, frozen at least one hour before kickoff.

Observed screening results:

| Cohort | Bets | Wins | Accuracy | Flat-stake ROI |
| --- | ---: | ---: | ---: | ---: |
| Older 70% | 30 | 23 | 76.7% | +19.4% |
| Newer 30% holdout | 13 | 9 | 69.2% | +7.5% |
| Combined descriptive sample | 43 | 32 | 74.4% | +15.8% |

## Why this is not validation

The rule was selected after inspecting historical evidence, and the holdout
contains only 13 bets. Many neighbouring filters looked excellent in the older
period and failed in the newer period. The figures above generate a hypothesis;
they do not establish a durable edge or justify a public ROI claim.

The model itself is not a sufficient selector. Across all 464 clean 1X2
fixtures its top choice recorded 49.1% accuracy and -22.2% ROI. Across all 464
Over/Under 2.5 fixtures it recorded 59.1% accuracy and -14.5% ROI. The no-vig
market baseline also beat the provider probability model on Brier score and log
loss for 1X2, BTTS, and Over/Under 2.5. The v4 hypothesis therefore requires
model-market agreement and abstains outside a narrow price corridor.

BTTS was screened under the same chronological process and rejected. Its 464
top choices recorded 54.3% accuracy and -20.9% ROI. Twenty-seven grid variants
cleared the screening threshold in the older 70%, but none retained both 60%+
accuracy and positive ROI with at least ten bets in the newer holdout. No new
BTTS version was registered.

## Frozen promotion gates

The v4 experiment needs all of the following:

- at least 100 forward-settled decisions;
- forward accuracy above 60%;
- a 95% Wilson accuracy lower bound above 50%;
- forward flat-stake ROI above 10%;
- the family-wise conservative ROI interval entirely above zero;
- positive ROI in both chronological halves;
- positive mean closing-line value;
- maximum drawdown no greater than 20 units;
- explicit human methodology review.

Changing any selection threshold requires a new version and a new forward
record. Retrospective rows may reject v4, but can never promote it.
