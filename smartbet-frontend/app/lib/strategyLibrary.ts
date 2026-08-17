export type StrategyCategory = 'handicaps' | 'goals' | 'results' | 'specialists'

export interface LocalizedStrategyCopy {
  name: string
  shortName: string
  summary: string
  thesis: string
  mechanics: string[]
  usefulWhen: string[]
  risks: string[]
  settlement: string
  example: string
  breakEvenExample: string
}

export interface StrategyDefinition {
  slug: string
  strategyKey: string
  category: StrategyCategory
  marketLabel: string
  complexity: 'beginner' | 'intermediate' | 'advanced'
  copy: {
    en: LocalizedStrategyCopy
    ro: LocalizedStrategyCopy
  }
}

export const STRATEGIES: StrategyDefinition[] = [
  {
    slug: 'asian-handicap', strategyKey: 'asian-handicap-score-distribution', category: 'handicaps', marketLabel: 'Asian Handicap', complexity: 'advanced',
    copy: {
      en: {
        name: 'Asian Handicap', shortName: 'Asian Handicap',
        summary: 'Remove the draw or alter the winning margin by giving one team a virtual head start.',
        thesis: 'A strong favourite may be overpriced in the ordinary match-winner market. Handicap lines let you express a more precise view about the likely winning margin—but the extra precision creates extra ways to be wrong.',
        mechanics: ['Whole lines can return the stake when the adjusted score is level.', 'Half lines remove the possibility of a push.', 'Quarter lines split one stake equally across the adjacent whole and half lines.'],
        usefulWhen: ['You have a distribution for winning margins, not just a winner prediction.', 'The ordinary favourite price offers little upside.', 'Team news or match context changes the expected margin more than the expected winner.'],
        risks: ['A favourite can win the match but still lose the handicap bet.', 'Quarter-line notation and settlement are easy to misunderstand.', 'Small probability errors matter when comparing neighbouring lines.'],
        settlement: 'The selected handicap is added to that team’s 90-minute score. Quarter lines are settled as two equal half-stakes. Extra time does not count unless the bookmaker explicitly states otherwise.',
        example: 'Favourite −1.25 at 2.00: half the stake is on −1 and half on −1.5. A one-goal win loses half and refunds half; a two-goal win wins both halves.',
        breakEvenExample: 'At decimal odds 2.00, a full-win/full-loss bet needs a 50% win probability before costs. Quarter-line pushes and half outcomes require the complete settlement distribution—not the shortcut 1 ÷ odds.',
      },
      ro: {
        name: 'Handicap asiatic', shortName: 'Handicap asiatic',
        summary: 'Elimină egalul sau modifică marja victoriei printr-un avantaj virtual acordat unei echipe.',
        thesis: 'O favorită puternică poate avea o cotă prea mică pe piața clasică. Liniile de handicap permit o opinie mai precisă despre diferența probabilă de scor, dar precizia suplimentară aduce și mai multe moduri de a greși.',
        mechanics: ['Liniile întregi pot returna miza dacă scorul ajustat este egal.', 'Liniile de jumătate elimină posibilitatea rambursării.', 'Liniile de sfert împart miza egal între liniile întregi și de jumătate alăturate.'],
        usefulWhen: ['Ai o distribuție a diferenței de scor, nu doar un pronostic despre câștigătoare.', 'Cota clasică a favoritei oferă un randament mic.', 'Absențele sau contextul schimbă mai mult marja așteptată decât echipa câștigătoare.'],
        risks: ['Favorita poate câștiga meciul, dar pariul cu handicap poate pierde.', 'Notația și decontarea liniilor de sfert sunt ușor de interpretat greșit.', 'Erori mici de probabilitate contează mult între linii apropiate.'],
        settlement: 'Handicapul ales se adaugă scorului echipei după 90 de minute. Liniile de sfert sunt decontate ca două jumătăți egale de miză. Prelungirile nu se iau în calcul decât dacă operatorul precizează altfel.',
        example: 'Favorită −1,25 la 2,00: jumătate din miză este pe −1 și jumătate pe −1,5. Victoria la un gol pierde jumătate și rambursează jumătate; victoria la două goluri câștigă ambele părți.',
        breakEvenExample: 'La cota zecimală 2,00, un pariu doar câștig/pierdere are nevoie de 50% probabilitate înainte de costuri. Pentru liniile de sfert este necesară distribuția completă a decontării, nu simplificarea 1 ÷ cotă.',
      },
    },
  },
  {
    slug: 'asian-goal-lines', strategyKey: 'asian-goal-line-score-distribution', category: 'goals', marketLabel: 'Asian Goal Line', complexity: 'advanced',
    copy: {
      en: {
        name: 'Asian goal lines', shortName: 'Asian totals', summary: 'Trade a range of total-goal outcomes with whole, half and quarter lines.',
        thesis: 'Instead of asking only whether a match goes over 2.5 goals, Asian totals can price the uncertainty around two neighbouring goal thresholds.',
        mechanics: ['Whole lines can push.', 'Half lines settle as a simple win or loss.', 'Quarter lines split the stake across adjacent lines.'],
        usefulWhen: ['Your score distribution concentrates near a standard total.', 'The 2.5 line hides meaningful push protection at 2.0 or 3.0.', 'The teams’ pace and chance quality offer more information than their match-result probabilities.'],
        risks: ['A good view of match direction can still select the wrong line.', 'Bookmaker line naming is inconsistent.', 'Low-scoring football makes a single event disproportionately important.'],
        settlement: 'The two teams’ 90-minute goals are added together and compared with the selected line. Quarter lines split into equal stakes on the adjacent lines.',
        example: 'Over 2.25: half the stake is Over 2.0 and half Over 2.5. Exactly two goals refunds half and loses half.',
        breakEvenExample: 'Because pushes and half-losses change the payoff, calculate expected return from every score bucket and its exact payout.',
      },
      ro: {
        name: 'Linii asiatice de goluri', shortName: 'Total asiatic', summary: 'Evaluează totalul golurilor prin linii întregi, de jumătate și de sfert.',
        thesis: 'În loc să întrebi doar dacă meciul trece de 2,5 goluri, totalurile asiatice pot evalua incertitudinea dintre două praguri apropiate.',
        mechanics: ['Liniile întregi permit rambursarea.', 'Liniile de jumătate se încheie simplu prin câștig sau pierdere.', 'Liniile de sfert împart miza între două praguri alăturate.'],
        usefulWhen: ['Distribuția scorurilor este concentrată lângă un total standard.', 'Linia de 2,5 ascunde protecția oferită de 2,0 sau 3,0.', 'Ritmul și calitatea ocaziilor spun mai mult decât probabilitățile rezultatului final.'],
        risks: ['Poți anticipa corect direcția meciului, dar alege linia greșită.', 'Denumirile liniilor diferă între operatori.', 'În meciurile cu puține goluri, un singur eveniment schimbă radical rezultatul.'],
        settlement: 'Golurile ambelor echipe după 90 de minute se adună și se compară cu linia. Liniile de sfert împart miza egal între pragurile alăturate.',
        example: 'Peste 2,25: jumătate din miză este Peste 2,0 și jumătate Peste 2,5. Exact două goluri rambursează jumătate și pierd jumătate.',
        breakEvenExample: 'Rambursările și jumătățile pierdute modifică plata; randamentul trebuie calculat pentru fiecare scor și decontarea lui exactă.',
      },
    },
  },
  {
    slug: 'team-total-goals', strategyKey: 'team-total-score-distribution', category: 'goals', marketLabel: 'Team totals', complexity: 'intermediate',
    copy: {
      en: { name: 'Team total goals', shortName: 'Team totals', summary: 'Price how many goals one team will score, independent of the opponent’s total.', thesis: 'A mismatch may be clearer in one attack-versus-defence matchup than in the overall match total.', mechanics: ['Choose one team, a goal line and Over or Under.', 'Only that team’s goals settle the bet.', 'Whole and quarter variants can include pushes or split settlements.'], usefulWhen: ['One team drives most of the expected goals.', 'The opponent’s scoring outlook is highly uncertain.', 'Lineups materially affect one attack or defence.'], risks: ['A comfortable lead can reduce attacking urgency.', 'Red cards and game state can reverse the expected pattern.', 'Team-name and home/away mapping must be exact.'], settlement: 'Compare the selected team’s 90-minute goals with the quoted line; use Asian settlement when the line is whole or quarter.', example: 'Home team Over 1.5 needs at least two home goals. The away team’s goals do not affect settlement.', breakEvenExample: 'At 1.80 with no push, break-even is 55.6%. Compare that threshold with the probability mass for the team scoring enough goals.' },
      ro: { name: 'Total goluri pe echipă', shortName: 'Total echipă', summary: 'Evaluează câte goluri va marca o singură echipă, independent de totalul adversarei.', thesis: 'Un dezechilibru poate fi mai clar în duelul dintre un atac și o apărare decât în totalul general al meciului.', mechanics: ['Alegi echipa, linia și Peste sau Sub.', 'Doar golurile echipei alese decontează pariul.', 'Variantele întregi și de sfert pot avea rambursări sau decontări împărțite.'], usefulWhen: ['O echipă generează cea mai mare parte din golurile așteptate.', 'Perspectivele ofensive ale adversarei sunt foarte incerte.', 'Echipele de start afectează evident un atac sau o apărare.'], risks: ['Un avantaj confortabil poate reduce ritmul ofensiv.', 'Cartonașele roșii și starea jocului pot inversa scenariul.', 'Identificarea echipei gazdă/deplasare trebuie să fie exactă.'], settlement: 'Compară golurile echipei alese după 90 de minute cu linia; pentru linii întregi sau de sfert se aplică decontarea asiatică.', example: 'Gazde Peste 1,5 necesită cel puțin două goluri ale gazdelor. Golurile oaspeților nu afectează decontarea.', breakEvenExample: 'La 1,80 fără rambursare, pragul este 55,6%. Compară-l cu masa de probabilitate pentru numărul necesar de goluri.' },
    },
  },
  {
    slug: 'match-result', strategyKey: 'full-time-result-value', category: 'results', marketLabel: '1X2', complexity: 'beginner',
    copy: {
      en: { name: 'Full-time result value', shortName: 'Match result', summary: 'Compare home, draw and away probabilities with available prices.', thesis: 'Picking the likely winner is not enough. A selection has value only when its estimated chance exceeds the chance implied by the obtainable price by enough to absorb uncertainty.', mechanics: ['Evaluate all three mutually exclusive outcomes.', 'Remove bookmaker margin before comparing market probabilities.', 'Use a real timestamped price, not a later or best-case quote.'], usefulWhen: ['The full probability vector is available.', 'Several bookmakers confirm the price.', 'The model-market disagreement survives conservative assumptions.'], risks: ['The favourite can be likely and still be a poor price.', 'Draw probabilities are easy to understate.', 'Small edges disappear through margin and model error.'], settlement: 'Home, draw or away after regulation time. Extra time and penalties do not count.', example: 'A 50% estimate has fair odds of 2.00. A quote of 1.75 is not value merely because the team is likely to win.', breakEvenExample: 'Break-even probability is 1 ÷ decimal odds. At 2.20 it is 45.5%, before accounting for uncertainty.' },
      ro: { name: 'Valoare pe rezultatul final', shortName: 'Rezultat final', summary: 'Compară probabilitățile pentru gazde, egal și oaspeți cu prețurile disponibile.', thesis: 'A identifica rezultatul cel mai probabil nu este suficient. Există valoare doar când șansa estimată depășește suficient probabilitatea implicată de cota obținabilă.', mechanics: ['Evaluează toate cele trei rezultate exclusive.', 'Elimină marja operatorului înainte de comparație.', 'Folosește o cotă reală și datată, nu una ulterioară sau idealizată.'], usefulWhen: ['Este disponibil vectorul complet de probabilități.', 'Mai mulți operatori confirmă prețul.', 'Diferența model–piață rezistă ipotezelor conservatoare.'], risks: ['Favorita poate fi probabilă și totuși prea scumpă.', 'Probabilitatea egalului este ușor subestimată.', 'Avantajele mici dispar prin marjă și eroare de model.'], settlement: 'Gazde, egal sau oaspeți după timpul regulamentar. Prelungirile și loviturile de departajare nu contează.', example: 'O estimare de 50% are cota corectă 2,00. Cota 1,75 nu are valoare doar fiindcă echipa este favorită.', breakEvenExample: 'Probabilitatea de prag este 1 ÷ cota zecimală. La 2,20 este 45,5%, înainte de incertitudine.' },
    },
  },
  {
    slug: 'both-teams-to-score', strategyKey: 'both-teams-score-value', category: 'goals', marketLabel: 'BTTS', complexity: 'beginner',
    copy: {
      en: { name: 'Both teams to score', shortName: 'BTTS', summary: 'Assess whether each team will score at least once.', thesis: 'BTTS focuses on the interaction of two attacks and defences without requiring a winner or a high total.', mechanics: ['Yes wins when both teams score.', 'No wins when at least one team keeps a clean sheet.', 'The final goal count alone is insufficient: 3–0 and 2–1 settle differently.'], usefulWhen: ['Both teams create chances consistently.', 'A strong favourite also has a vulnerable defence.', 'The total-goals view is distorted by one dominant attack.'], risks: ['A high expected total does not guarantee both teams contribute.', 'Early game state may suppress one team.', 'Lineup changes to one striker or goalkeeper can matter greatly.'], settlement: 'Both teams must score during regulation time for Yes; own goals count for the team awarded the goal.', example: '2–1 wins BTTS Yes; 3–0 loses it despite the same three-goal total.', breakEvenExample: 'At 1.90, the simple break-even probability is 52.6%.' },
      ro: { name: 'Ambele echipe marchează', shortName: 'GG/NG', summary: 'Evaluează dacă fiecare echipă va înscrie cel puțin o dată.', thesis: 'Piața se concentrează pe interacțiunea celor două atacuri și apărări fără a cere o câștigătoare sau un total mare.', mechanics: ['Da câștigă dacă ambele echipe marchează.', 'Nu câștigă dacă cel puțin o echipă nu marchează.', 'Totalul golurilor nu este suficient: 3–0 și 2–1 se decontează diferit.'], usefulWhen: ['Ambele echipe creează constant ocazii.', 'O favorită puternică are totuși o apărare vulnerabilă.', 'Totalul golurilor este dominat de un singur atac.'], risks: ['Un total așteptat mare nu garantează contribuția ambelor echipe.', 'Starea timpurie a meciului poate bloca o echipă.', 'Absența unui atacant sau portar poate schimba mult estimarea.'], settlement: 'Pentru Da, ambele echipe trebuie să marcheze în timpul regulamentar; autogolurile contează pentru echipa căreia i-a fost acordat golul.', example: '2–1 câștigă GG; 3–0 pierde, deși ambele au trei goluri.', breakEvenExample: 'La cota 1,90, pragul simplu este 52,6%.' },
    },
  },
  ...[
    { slug: 'total-goals-1-5', key: 'total-goals-1-5-value', line: '1.5' },
    { slug: 'total-goals-2-5', key: 'total-goals-2-5-value', line: '2.5' },
    { slug: 'total-goals-3-5', key: 'total-goals-3-5-value', line: '3.5' },
  ].map(({ slug, key, line }): StrategyDefinition => ({
    slug, strategyKey: key, category: 'goals', marketLabel: `Over/Under ${line}`, complexity: 'beginner',
    copy: {
      en: { name: `Total goals ${line}`, shortName: `O/U ${line}`, summary: `Compare the probability of the match finishing above or below ${line} goals.`, thesis: `A totals strategy prices match scoring rather than the winner. The line ${line} changes which score outcomes belong to Over and Under.`, mechanics: [`Over ${line} needs at least ${Math.floor(Number(line)) + 1} total goals.`, `Under ${line} needs at most ${Math.floor(Number(line))} total goals.`, 'Both sides must be compared with margin-removed prices.'], usefulWhen: ['The expected pace and chance quality are measurable.', 'Winner uncertainty is high but scoring expectations are clearer.', 'The chosen threshold, not merely Over/Under direction, matches the score distribution.'], risks: ['A red card or early goal can change match state.', 'Related total lines must not be counted as independent evidence.', 'League averages can hide team-specific styles.'], settlement: `Add both teams’ regulation-time goals and compare the total with ${line}. There is no push on a half-goal line.`, example: `At ${line}, a 2–1 score is ${3 > Number(line) ? 'Over' : 'Under'} and a 1–0 score is ${1 > Number(line) ? 'Over' : 'Under'}.`, breakEvenExample: 'At 1.95, the simple break-even probability is 51.3%.' },
      ro: { name: `Total goluri ${line}`, shortName: `P/S ${line}`, summary: `Compară probabilitatea ca meciul să se termine peste sau sub ${line} goluri.`, thesis: `Strategia evaluează numărul de goluri, nu câștigătoarea. Linia ${line} stabilește ce scoruri intră la Peste și Sub.`, mechanics: [`Peste ${line} necesită cel puțin ${Math.floor(Number(line)) + 1} goluri.`, `Sub ${line} permite cel mult ${Math.floor(Number(line))} goluri.`, 'Ambele părți trebuie comparate cu prețurile fără marja operatorului.'], usefulWhen: ['Ritmul și calitatea ocaziilor pot fi estimate.', 'Câștigătoarea este incertă, dar profilul de goluri este mai clar.', 'Pragul ales, nu doar direcția Peste/Sub, corespunde distribuției scorurilor.'], risks: ['Un cartonaș roșu sau un gol timpuriu schimbă starea jocului.', 'Liniile corelate nu trebuie numărate ca dovezi independente.', 'Mediile ligii pot ascunde stilurile specifice echipelor.'], settlement: `Adună golurile ambelor echipe din timpul regulamentar și compară totalul cu ${line}. Liniile de jumătate nu au rambursare.`, example: `La ${line}, scorul 2–1 este ${3 > Number(line) ? 'Peste' : 'Sub'}, iar 1–0 este ${1 > Number(line) ? 'Peste' : 'Sub'}.`, breakEvenExample: 'La 1,95, pragul simplu este 51,3%.' },
    },
  })),
  {
    slug: 'double-chance', strategyKey: 'double-chance-value', category: 'results', marketLabel: 'Double chance', complexity: 'beginner',
    copy: {
      en: { name: 'Double chance', shortName: 'Double chance', summary: 'Cover two of the three match results: 1X, X2 or 12.', thesis: 'Combining outcomes increases hit probability but normally lowers the price. The relevant question remains whether the protection is priced fairly.', mechanics: ['1X covers home or draw.', 'X2 covers draw or away.', '12 covers either team winning and loses on a draw.'], usefulWhen: ['You distrust one outcome more than you favour a single team.', 'Draw protection has a measurable price.', 'The combined probability can be derived from a complete 1X2 vector.'], risks: ['A high hit rate can conceal poor expected value.', 'Short prices amplify small estimation errors.', 'Adding probabilities is valid only when the underlying outcomes are mutually exclusive and calibrated.'], settlement: 'The bet wins if either covered regulation-time result occurs.', example: '1X at 1.35 covers a home win and draw; it loses only on an away win.', breakEvenExample: 'At 1.35, break-even is 74.1%. “Safer” does not mean fairly priced.' },
      ro: { name: 'Șansă dublă', shortName: 'Șansă dublă', summary: 'Acoperă două dintre cele trei rezultate: 1X, X2 sau 12.', thesis: 'Combinarea rezultatelor crește șansa de câștig, dar reduce de obicei cota. Întrebarea rămâne dacă protecția este evaluată corect.', mechanics: ['1X acoperă gazde sau egal.', 'X2 acoperă egal sau oaspeți.', '12 acoperă victoria oricărei echipe și pierde la egal.'], usefulWhen: ['Respingi un rezultat mai mult decât favorizezi o singură echipă.', 'Protecția la egal are un preț măsurabil.', 'Probabilitatea combinată provine dintr-un vector 1X2 complet.'], risks: ['O rată mare de câștig poate ascunde valoare negativă.', 'Cotele mici amplifică erorile de estimare.', 'Adunarea probabilităților cere rezultate exclusive și probabilități calibrate.'], settlement: 'Pariul câștigă dacă apare oricare dintre cele două rezultate acoperite după timpul regulamentar.', example: '1X la 1,35 acoperă victoria gazdelor și egalul; pierde doar la victoria oaspeților.', breakEvenExample: 'La 1,35, pragul este 74,1%. „Mai sigur” nu înseamnă automat preț corect.' },
    },
  },
  {
    slug: 'half-time-result', strategyKey: 'half-time-result-value', category: 'specialists', marketLabel: 'Half-time result', complexity: 'intermediate',
    copy: {
      en: { name: 'Half-time result', shortName: 'Half-time', summary: 'Price the home, draw or away result after the first half.', thesis: 'Some teams start quickly or slowly, but a smaller time window increases variance and the importance of one event.', mechanics: ['The market is a separate 1X2 for the first half.', 'A 0–0 interval score is a draw.', 'Full-time recovery does not change settlement.'], usefulWhen: ['Starting intensity and first-half patterns are supported by data.', 'Lineups suggest an early tactical mismatch.', 'The price compensates for the smaller sample of match time.'], risks: ['Half-specific samples are smaller and noisier.', 'A single goal dominates settlement.', 'Narratives about “fast starters” can be overfit.'], settlement: 'Only the score at the official half-time interval counts.', example: 'A match that is 0–1 at half-time and 2–1 at full-time settles as Away for this market.', breakEvenExample: 'Use the first-half probability vector; full-time win probability is not a substitute.' },
      ro: { name: 'Rezultat la pauză', shortName: 'Pauză', summary: 'Evaluează gazde, egal sau oaspeți după prima repriză.', thesis: 'Unele echipe încep rapid sau lent, dar intervalul mai scurt crește variația și importanța unui singur eveniment.', mechanics: ['Piața este un 1X2 separat pentru prima repriză.', '0–0 la pauză înseamnă egal.', 'Revenirea din repriza a doua nu schimbă decontarea.'], usefulWhen: ['Intensitatea de start și tiparele primei reprize au suport în date.', 'Echipele de start sugerează un dezechilibru tactic timpuriu.', 'Cota compensează intervalul mai scurt.'], risks: ['Eșantioanele pe reprize sunt mai mici și mai zgomotoase.', 'Un singur gol domină decontarea.', 'Poveștile despre echipe care „încep tare” pot fi supraînvățate.'], settlement: 'Contează doar scorul oficial de la pauză.', example: 'Un meci 0–1 la pauză și 2–1 la final se decontează Oaspeți pe această piață.', breakEvenExample: 'Folosește vectorul de probabilități al primei reprize; probabilitatea de la final nu este un substitut.' },
    },
  },
  {
    slug: 'half-time-full-time', strategyKey: 'half-time-full-time-value', category: 'specialists', marketLabel: 'HT/FT', complexity: 'advanced',
    copy: {
      en: { name: 'Half-time / full-time', shortName: 'HT/FT', summary: 'Combine the result at half-time with the result after 90 minutes.', thesis: 'Nine outcome combinations offer precise match-path views and larger odds, but accurate joint probabilities are much harder than two separate predictions.', mechanics: ['Choose one half-time and one full-time outcome.', 'Both legs must be correct.', 'The outcomes are dependent and must be modelled jointly.'], usefulWhen: ['A model supplies a complete joint distribution.', 'Game-state transitions are explicitly represented.', 'The price remains attractive after conservative uncertainty.'], risks: ['Large odds are not evidence of value.', 'Multiplying separate HT and FT probabilities is usually wrong.', 'Sparse outcomes invite severe overfitting.'], settlement: 'Both the official half-time result and regulation-time full-time result must match the selection.', example: 'Draw/Home wins only if the match is level at half-time and the home team wins after 90 minutes.', breakEvenExample: 'At 6.00, break-even is 16.7%, but that probability must describe the exact joint path.' },
      ro: { name: 'Pauză / final', shortName: 'P/F', summary: 'Combină rezultatul de la pauză cu rezultatul după 90 de minute.', thesis: 'Cele nouă combinații descriu trasee precise și au cote mai mari, dar probabilitățile comune sunt mult mai greu de estimat decât două pronosticuri separate.', mechanics: ['Alegi un rezultat la pauză și unul la final.', 'Ambele componente trebuie să fie corecte.', 'Rezultatele sunt dependente și trebuie modelate împreună.'], usefulWhen: ['Modelul oferă o distribuție comună completă.', 'Tranzițiile dintre stările jocului sunt reprezentate explicit.', 'Cota rămâne atractivă după o marjă conservatoare de incertitudine.'], risks: ['Cotele mari nu dovedesc valoare.', 'Înmulțirea probabilităților separate este de obicei greșită.', 'Rezultatele rare favorizează supraînvățarea.'], settlement: 'Atât rezultatul oficial de la pauză, cât și cel de la finalul timpului regulamentar trebuie să corespundă selecției.', example: 'Egal/Gazde câștigă doar dacă este egal la pauză și gazdele câștigă după 90 de minute.', breakEvenExample: 'La 6,00, pragul este 16,7%, dar probabilitatea trebuie să descrie exact traseul comun.' },
    },
  },
  {
    slug: 'correct-score', strategyKey: 'correct-score-value', category: 'specialists', marketLabel: 'Correct score', complexity: 'advanced',
    copy: {
      en: { name: 'Correct score', shortName: 'Correct score', summary: 'Price one exact regulation-time scoreline.', thesis: 'Exact scores offer high prices because probability is spread across many outcomes. They are useful as a distribution diagnostic, but extremely fragile as standalone selections.', mechanics: ['Choose one exact home-away score.', 'Every other score loses.', 'An “Any other” bucket must remain part of a complete model distribution.'], usefulWhen: ['A coherent score distribution is available.', 'The exact outcome is compared against all alternatives.', 'The quote is supported by enough bookmaker coverage.'], risks: ['Very high variance and sparse wins.', 'Truncated score models exaggerate named outcomes.', 'A model can predict goal totals well and still miss exact scores badly.'], settlement: 'The regulation-time score must exactly match the selection.', example: '2–1 loses if the match ends 2–0, 1–1 or 3–1.', breakEvenExample: 'At 10.00, break-even is 10%, but model uncertainty and omitted score buckets make a conservative bound essential.' },
      ro: { name: 'Scor corect', shortName: 'Scor corect', summary: 'Evaluează un singur scor exact după timpul regulamentar.', thesis: 'Scorurile exacte au cote mari deoarece probabilitatea este împărțită între multe rezultate. Sunt utile pentru diagnosticarea distribuției, dar foarte fragile ca selecții individuale.', mechanics: ['Alegi un singur scor gazde–oaspeți.', 'Orice alt scor pierde.', 'Categoria „Orice alt scor” trebuie păstrată într-o distribuție completă.'], usefulWhen: ['Există o distribuție coerentă a scorurilor.', 'Rezultatul exact este comparat cu toate alternativele.', 'Cota este confirmată de suficienți operatori.'], risks: ['Variație foarte mare și câștiguri rare.', 'Modelele trunchiate exagerează scorurile enumerate.', 'Un model poate estima bine totalul golurilor și totuși rata scorurile exacte.'], settlement: 'Scorul după timpul regulamentar trebuie să corespundă exact selecției.', example: '2–1 pierde dacă meciul se termină 2–0, 1–1 sau 3–1.', breakEvenExample: 'La 10,00, pragul este 10%, dar incertitudinea și scorurile omise cer o limită conservatoare.' },
    },
  },
]

export const STRATEGY_BY_SLUG = Object.fromEntries(
  STRATEGIES.map((strategy) => [strategy.slug, strategy]),
) as Record<string, StrategyDefinition>
