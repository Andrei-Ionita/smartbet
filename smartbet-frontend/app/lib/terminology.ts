/**
 * THE single source of public product vocabulary.
 *
 * BetGlitch has exactly three public concepts. Every page must describe them
 * with these words — previously each page invented its own ("recommendations",
 * "smart picks", "top quality bets", "predictions"), which made a mutable model
 * output and an immutable published claim look like the same object.
 *
 *   1. LIVE SIGNAL        — BetGlitch's current ranked output for an upcoming
 *                           fixture. MUTABLE. Not part of public performance.
 *   2. PUBLIC COMMITMENT  — an immutable PublishedClaim, frozen before kickoff
 *                           with its selection, score, odds, bookmaker and
 *                           provenance.
 *   3. VERIFIED RECORD    — resolved, integrity-valid published claims ONLY.
 *                           The only universe behind any public accuracy, ROI,
 *                           win/loss, market or league figure.
 *
 * The distinction is the product. Do not blur it in copy.
 *
 * Bilingual because the EN/RO switcher in the navigation is user-reachable.
 * Keeping both languages in ONE module is the point: a concept cannot drift
 * between languages if both wordings live on adjacent lines.
 */

export type Lang = 'en' | 'ro'

const EN = {
  terms: {
    liveSignal: {
      label: 'Live signal',
      plural: 'Live signals',
      short: 'Live signal',
      definition:
        'BetGlitch’s current ranked outcome for an upcoming fixture, derived from provider probability data. It can change before kickoff.',
      mutability:
        'Live signals update when the pipeline runs again, odds move, new provider data arrives or a newer snapshot is generated.',
      notInRecord:
        'A live signal is not a betting recommendation, and it enters the public evaluation record only if BetGlitch formally commits it before kickoff.',
    },
    // Publicly a PUBLIC COMMITMENT. "Published pick" made the one committed
    // fixture read as a featured betting recommendation — a visitor seeing
    // many live signals and one "pick" reasonably asked why that one was
    // special. It is not special: it is simply a signal formally frozen into
    // the permanent evaluation record. The backend model stays PublishedClaim;
    // this is public vocabulary, not a schema change.
    publicCommitment: {
      label: 'Public commitment',
      plural: 'Public commitments',
      short: 'Committed',
      definition:
        'A live signal BetGlitch deliberately froze before kickoff for public forward evaluation — selection, signal score, recorded odds, bookmaker and timestamps can no longer change.',
      notARecommendation:
        'A public commitment records that BetGlitch stated this outcome in advance — not that the outcome was statistically compelling. It carries no minimum score and no demonstrated value threshold. What it proves is that the selection and its price cannot be rewritten or quietly removed.',
      frozenFields: [
        'Selection', 'Signal score', 'Recorded odds', 'Bookmaker', 'Timestamps',
        'Provenance',
      ],
    },
    verifiedRecord: {
      label: 'Verified record',
      definition:
        'Every eligible public commitment that has settled, kept public with its result — win or lose.',
      scope:
        'Only eligible settled commitments count. Pending commitments are not results — they are shown separately, and void or cancelled commitments are excluded from the totals.',
    },
  },

  /**
   * Five stages, not three. The old Explore/Publish/Verify triad ended at the
   * result, which quietly told visitors BetGlitch is a static prediction
   * engine. Measure and Improve are the point: the system is evaluated in
   * public and changed by what the evidence shows.
   */
  workflow: [
    {
      id: 'analyse',
      title: 'Analyse',
      body: 'We review provider-derived probability data, market pricing and the available fixture context.',
    },
    {
      id: 'rank',
      title: 'Rank',
      body: 'BetGlitch surfaces the strongest current signals while preserving what remains uncertain.',
    },
    {
      id: 'publish',
      title: 'Publish',
      body: 'Selected decisions are frozen before kickoff with their price, bookmaker, timestamp and public proof.',
    },
    {
      id: 'measure',
      title: 'Measure',
      body: 'Eligible settled results enter the record — including the losses.',
    },
    {
      id: 'improve',
      title: 'Improve',
      body: 'We study what worked, what failed and what should change.',
    },
  ],

  hero: {
    eyebrow: 'FREE PUBLIC BETA',
    // The brand line. Not "verifiable signals" (a feature) but the reason the
    // feature exists: decisions improve when the evidence behind them does.
    headline: 'Better football decisions start with better evidence.',
    supporting:
      'Explore transparent football signals, verified market prices and the context behind each fixture. When BetGlitch commits a signal to the public record, the decision is frozen before kickoff and every eligible result remains visible — win or lose.',
    primaryCta: 'Explore live signals',
    secondaryCta: 'View the verified record',
    // Three commitments in one quiet line — a rule, not a badge.
    trustLine: 'Free public beta · No guaranteed wins · No hidden losses',
    zeroState: 'Building the verified record from zero',
  },

  /**
   * The public manifesto. One authored text, rendered on the homepage and
   * About — never paraphrased per-page, or the philosophy drifts exactly the
   * way the vocabulary once did.
   */
  manifesto: {
    heading: 'Betting platforms usually show certainty. BetGlitch shows evidence.',
    paragraphs: [
      'We publish the decisions we commit to before kickoff. We preserve the price, the timestamp and the proof. We keep every eligible result visible, including the losses.',
      'We continuously test new signals, strategies and fixture context — not to manufacture more picks, but to understand what genuinely improves decision quality.',
      'We do not promise perfect predictions. We promise transparency, accountability and measurable improvement.',
    ],
  },

  home: {
    signalsHeading: 'Live signals right now',
    browseAll: 'Browse all fixtures',

    // ── The BetGlitch difference: a conceptual contrast, not a feature list.
    differenceContrastHeading: 'The BetGlitch difference',
    differenceOthersLabel: 'Most prediction products',
    differenceOthersFlow: ['Prediction', 'Result'],
    differenceUsLabel: 'BetGlitch',
    differenceUsFlow: ['Signal', 'Evidence', 'Commitment', 'Result', 'Evaluation', 'Improvement'],

    // ── Product rules. Presented as constraints the system obeys, not as
    // marketing badges — each one is enforced by architecture, not policy.
    rulesHeading: 'Rules the product cannot break',
    rules: [
      'No deleted losses',
      'No rewritten odds',
      'No retrospective picks',
      'No guaranteed wins',
    ],

    // ── Continuous improvement, stated without claiming it has succeeded.
    improvementHeading: 'We measure the system, not just the scoreline.',
    improvementBody:
      'BetGlitch is continuously testing whether its filtering, pricing evidence and fixture context genuinely improve decision quality. We do not claim they already do — the public record exists to find out. What does not improve the evidence does not earn a place in the product.',

    howHeading: 'How BetGlitch works',
    differenceHeading: 'Not every signal becomes a public commitment',
    differenceBody:
      'BetGlitch shows far more live signals than it commits. A live signal is current analysis and may change; a public commitment is the subset formally frozen into the permanent evaluation record — and only eligible settled commitments count towards it.',
    notInPerformance: 'Not part of public performance.',
    frozenIntro: 'Frozen before kickoff. These can never change:',
    benefitsHeading: 'What you can do here',
    benefits: [
      {
        title: 'Read the evidence, not a tip',
        body: 'Every fixture shows its signal score, the market it applies to and the recorded price with its provenance — not just a selection.',
      },
      {
        title: 'Check the receipts',
        body: 'Public commitments keep a permanent public page showing what was frozen, when, and at which bookmaker. Odds are never rewritten and losses are never deleted.',
      },
      {
        title: 'Decide for yourself',
        body: 'BetGlitch does not size stakes for you and does not tell you to bet. It shows what it ranked, at what price, and what happened next.',
      },
    ],
    coverageHeading: 'Coverage',
    coverageBody: 'European competitions, up to 14 days ahead. Including:',
    viewAllLeagues: 'View all competitions',
    settledLabel: 'Verified results',
    openRecord: 'Open the verified record',
    finalHeading: 'Free while we build the verified record',
    finalBody:
      'There is nothing to buy and no payment method is required. Create an account to use the bankroll tools and follow public commitments as they settle.',
    createAccount: 'Create a free account',
    signalsError: 'Live signals could not be loaded',
    signalsErrorBody:
      'The request to the signal service failed. Nothing is wrong with your account and no public commitment is affected.',
    tryAgain: 'Try again',
  },

  register: {
    heading: 'Create your free beta account',
    supporting:
      'Explore live signals, use the bankroll tools and follow BetGlitch’s verified public record as it develops.',
    freeDuringBeta: 'Free during public beta',
    noPayment: 'No payment method is required',
    informational: 'Informational only — BetGlitch does not place bets',
    submit: 'Create account',
    submitting: 'Creating account…',
  },

  onboarding: {
    heading: 'Welcome to BetGlitch',
    body: 'Three things worth knowing before you start.',
    dismiss: 'Dismiss',
    actions: [
      {
        id: 'explore',
        title: 'Explore current signals',
        body: 'Browse upcoming fixtures and their current live signals.',
        cta: 'Explore live signals',
        href: '/explore',
      },
      {
        id: 'proof',
        title: 'View public commitments',
        body: 'See how an immutable public commitment differs from a changing live signal.',
        cta: 'View public commitments',
        href: '/track-record#public-commitments',
      },
      {
        id: 'record',
        title: 'Check the verified record',
        body: 'Review eligible settled commitments as the sample develops.',
        cta: 'Open verified record',
        href: '/track-record#verified-record',
      },
    ],
  },

  beta: {
    primary:
      'BetGlitch is currently in public beta. Access is free while we build and validate the verified public record.',
  },

  dashboard: {
    title: 'Your dashboard',
    manageBankroll: 'Manage bankroll',
    recordBuilding:
      'The verified record is being built. Eligible settled commitments will appear here, including both wins and losses.',
  },

  auth: {
    login: {
      heading: 'Welcome back',
      supporting: 'Sign in to continue to BetGlitch',
      usernameLabel: 'Username or email',
      usernamePlaceholder: 'Enter your username',
      passwordLabel: 'Password',
      passwordPlaceholder: 'Enter your password',
      submit: 'Sign in',
      submitting: 'Signing in…',
      noAccount: 'Don’t have an account?',
      signUp: 'Sign up',
      backHome: '← Back to home',
    },
    register: {
      usernameLabel: 'Username',
      usernamePlaceholder: 'Choose a username',
      emailLabel: 'Email',
      emailPlaceholder: 'your@email.com',
      passwordLabel: 'Password',
      passwordPlaceholder: 'At least 8 characters',
      confirmLabel: 'Confirm password',
      confirmPlaceholder: 'Confirm your password',
      haveAccount: 'Already have an account?',
      signIn: 'Sign in',
      backHome: '← Back to home',
      passwordTooShort: 'Password must be at least 8 characters long',
      passwordMismatch: 'Passwords do not match',
    },
  },

  record: {
    scopeHeading: 'What counts towards this record',
    scopeCutoff:
      'The verified public record begins on the date BetGlitch started verifying every recorded price. Predictions made before that date are preserved as legacy and excluded from every figure on this page.',
    scopeImmutable:
      'Only immutable public commitments enter the record — signals frozen before kickoff with their selection, signal score, recorded odds and bookmaker.',
    scopePending:
      'Pending commitments are not counted as results, and void or cancelled commitments are excluded from the relevant denominators.',
    scopeLive:
      'Live signals shown elsewhere in the product never enter this record unless BetGlitch formally commits them.',

    publishedHeading: 'Public commitments',
    publishedBody:
      'Signals BetGlitch has deliberately frozen before kickoff for public forward evaluation. Once committed, the selection, recorded price and publication time cannot be rewritten or quietly removed.',
    // The sentence a confused visitor needs most: why fewer fixtures here
    // than the homepage shows? Because commitment is a separate, gated act
    // (policy v1) — not a quality ranking of the live signals.
    publishedDistinction:
      'A public commitment is not the same thing as every live signal. Live signals may change before kickoff. Public commitments are the subset BetGlitch has formally placed into the permanent evaluation record.',
    publishedStates:
      'A commitment stays pending until the match finishes. Pending is not a result: it is counted nowhere in the verified record below. Once the match ends it settles as won or lost, or is marked void or cancelled and excluded from the relevant totals.',
    publishedEmpty:
      'No public commitment has settled yet, so nothing is listed here. Settled commitments appear as soon as one does — win or lose.',
    publishedCount: 'Public commitments on record',
    publishedLoading: 'Loading public commitments…',
    publishedError:
      'Public commitments could not be loaded. Nothing is wrong with the record itself — this is a display problem and no commitment has changed. Reload in a moment.',
    publishedRetry: 'Try again',
    publishedProofLink: 'View proof',
    publishedOddsLabel: 'Recorded price',
    publishedAtLabel: 'Committed',
    publishedNotCounted: 'Awaiting settlement — not included in verified performance',
    publishedCountedIn: 'Counted in the verified record',

    // Honest publication policy — AUTOMATIC since policy v1 (2026-08-08).
    // This copy must state exactly what core/management/commands/
    // auto_publish_claims.py does and nothing more. Do not claim "strongest
    // signal" or "best value" here — no such rule exists; the committed
    // selection is the top-ranked outcome by construction, and every other
    // criterion is a machine-checked gate, not a judgment call.
    policyLink: 'How commitments are selected',
    policyBody:
      'Commitments are published automatically by a fixed, pre-registered rule — no human picks or vetoes individual fixtures. A live signal is committed when all of the following hold: it passes the machine-checked eligibility gate (verified price with complete bookmaker and market provenance, coherent timestamps, not superseded), kickoff is at least 6 hours away, and the fixture does not already hold a commitment. The committed selection is simply the top-ranked outcome in its market. Publication itself is not a claim that a signal has proven betting value.',

    verifiedHeading: 'Verified record',
    verifiedBody:
      'This is the record we cannot rewrite. These aggregate figures are calculated from eligible settled commitments only. Pending commitments, void and cancelled commitments, and every legacy prediction from before price verification began are excluded — so this record is smaller than the number of signals BetGlitch has produced, and that is deliberate.',
    verifiedFromCommitments:
      'Public commitments may include pending entries. The verified record below contains only eligible settled commitments.',

    noAccuracy: 'No verified results yet',
    accuracyAppears: 'Accuracy appears once the first public commitment settles.',
    noSettled: 'No settled commitments yet',
    winsLosses: 'Wins and losses are both published here as they settle.',
    roiRestarted:
      'Our verified pricing record restarted and fills in as matches settle.',
    noBreakdown:
      'No breakdown yet. Once public commitments settle, accuracy is split by predicted outcome here.',

    legacyHeading: 'Prediction log — not the verified record',
    legacyAll: (n: number) => `All ${n} rows below were`,
    legacySome: (n: number, total: number) => `${n} of the ${total} rows below were`,
    legacyBody:
      'recorded before BetGlitch began verifying every recorded price. They are kept public because BetGlitch does not delete history, but their prices could not be verified against the exact market and bookmaker, so they are excluded from the accuracy and ROI figures above and from every public performance claim.',
    legacyDetailBefore:
      'These predictions predate BetGlitch’s verified pricing standard. Their original price snapshots are not used in public performance reporting, so every price-dependent figure — expected value and profit/loss — reads ',
    notVerified: 'Not verified',
    legacyDetailAfter:
      ' rather than a number. The match, the selection and the actual outcome are still shown, because those do not depend on the recorded price.',
    notVerifiedTitle:
      'This prediction predates BetGlitch’s verified pricing standard. Its original price snapshot is not used in public performance reporting.',
    notVerifiedMeaningBefore: ' means the row’s recorded price predates the verified pricing standard, so no price-dependent figure is published for it.',

    capturePanelTitle: 'Check the receipts, then follow along by email.',
    capturePanelBody:
      'Verify every result here, then join the free list for updates on public commitments as the verified record develops.',
    capturePanelEyebrow: 'Proof-led funnel',
    capturePanelSeePublished: 'See the public commitments',
    capturePanelSeeVerified: 'See the verified record',
    captureTitle: 'Get the weekly summary',
    captureBody:
      'A free weekly email covering the signals BetGlitch committed and how they settled.',
    captureDefaultTitle: 'Follow the public commitments by email',
    captureDefaultBody:
      'A free weekly email covering which signals BetGlitch committed and how they settled — wins and losses both.',
  },

  footer: {
    tagline:
      'Football market signals across European competitions. Selected signals are committed before kickoff with their recorded odds and stay public after settlement — win or lose.',
    emailSupport: 'Email BetGlitch support',
    platform: 'Platform',
    explore: 'Explore signals',
    dashboard: 'User dashboard',
    trackRecord: 'Verified record',
    pricing: 'Pricing',
    resources: 'Resources',
    howItWorks: 'How it works',
    blog: 'Blog',
    responsibleGambling: 'Responsible gambling',
    about: 'About',
    legal: 'Legal',
    terms: 'Terms of service',
    privacy: 'Privacy policy',
    disclaimer: 'Disclaimer',
    noticeTitle: 'Important legal notice',
    noticeOperatorStrong:
      'BetGlitch is NOT a betting operator, bookmaker, or gambling site.',
    noticeOperatorRest: ' We do not accept bets, wagers, or deposits of any kind. Our signals are provided for ',
    noticeOperatorEmphasis: 'informational and entertainment purposes only',
    noticeOperatorTail: ' and should not be considered financial or betting advice.',
    noticeRiskLabel: 'Risk warning:',
    noticeRiskBody:
      ' Betting involves significant risk, including the possible loss of your entire stake. Past performance is not indicative of future results. Never bet more than you can afford to lose.',
    noticeRegionalLabel: 'Regional notice:',
    noticeRegionalBody:
      ' Online gambling may be restricted or illegal in your jurisdiction. It is your responsibility to ensure compliance with local laws before engaging in any gambling activity.',
    noticeHelp:
      'If you or someone you know has a gambling problem, please seek help:',
    ageNotice:
      'This website is for adults only. You must be 18 years or older to use this service.',
    rights: 'BetGlitch Analytics. All rights reserved.',
    operational: 'Systems operational',
  },

  responsibleUse:
    'BetGlitch publishes ranked signals for information only. It is not a bookmaker, it does not accept bets, and no outcome is guaranteed — you can lose everything you stake. 18+. Please gamble responsibly.',

  modelScoreNote:
    'A signal score ranks BetGlitch’s relative preference among the available outcomes. It is not a calibrated probability.',
}

const RO: typeof EN = {
  terms: {
    liveSignal: {
      label: 'Semnal live',
      plural: 'Semnale live',
      short: 'Semnal live',
      definition:
        'Rezultatul clasat curent al BetGlitch pentru un meci viitor, derivat din datele de probabilitate ale furnizorului. Se poate schimba până la start.',
      mutability:
        'Semnalele live se actualizează când pipeline-ul rulează din nou, când cotele se mișcă, când apar date noi de la furnizor sau când se generează un snapshot mai recent.',
      notInRecord:
        'Un semnal live nu este o recomandare de pariere și intră în registrul public de evaluare doar dacă BetGlitch îl angajează formal înainte de start.',
    },
    publicCommitment: {
      label: 'Angajament public',
      plural: 'Angajamente publice',
      short: 'Angajat',
      definition:
        'Un semnal live pe care BetGlitch l-a înghețat deliberat înainte de start pentru evaluare publică prospectivă — selecția, scorul de semnal, cota înregistrată, casa de pariuri și marcajele de timp nu se mai pot schimba.',
      notARecommendation:
        'Un angajament public înregistrează că BetGlitch a enunțat acest rezultat în avans — nu că rezultatul ar fi convingător statistic. Nu are un scor minim și niciun prag de valoare demonstrată. Ce dovedește este că selecția și prețul ei nu pot fi rescrise sau șterse discret.',
      frozenFields: [
        'Selecție', 'Scor semnal', 'Cota înregistrată', 'Casa de pariuri',
        'Marcaje de timp', 'Proveniență',
      ],
    },
    verifiedRecord: {
      label: 'Istoric verificat',
      definition:
        'Fiecare angajament public eligibil care s-a încheiat, păstrat public împreună cu rezultatul — câștigat sau pierdut.',
      scope:
        'Contează doar angajamentele eligibile încheiate. Cele în așteptare nu sunt rezultate — sunt afișate separat, iar cele anulate sunt excluse din totaluri.',
    },
  },

  workflow: [
    {
      id: 'analyse',
      title: 'Analizăm',
      body: 'Analizăm datele de probabilitate ale furnizorului, prețurile pieței și contextul de meci disponibil.',
    },
    {
      id: 'rank',
      title: 'Clasăm',
      body: 'BetGlitch scoate la suprafață cele mai puternice semnale curente, păstrând vizibil ce rămâne incert.',
    },
    {
      id: 'publish',
      title: 'Publicăm',
      body: 'Deciziile selectate sunt înghețate înainte de start, cu prețul, casa de pariuri, marcajul de timp și dovada publică.',
    },
    {
      id: 'measure',
      title: 'Măsurăm',
      body: 'Rezultatele eligibile încheiate intră în istoric — inclusiv pierderile.',
    },
    {
      id: 'improve',
      title: 'Îmbunătățim',
      body: 'Studiem ce a funcționat, ce a eșuat și ce trebuie schimbat.',
    },
  ],

  hero: {
    eyebrow: 'BETA PUBLIC GRATUIT',
    headline: 'Deciziile mai bune în fotbal încep cu dovezi mai bune.',
    supporting:
      'Explorează semnale transparente de fotbal, prețuri de piață verificate și contextul din spatele fiecărui meci. Când BetGlitch angajează un semnal în registrul public, decizia este înghețată înainte de start și fiecare rezultat eligibil rămâne vizibil — câștig sau pierdere.',
    primaryCta: 'Explorează semnalele live',
    secondaryCta: 'Vezi istoricul verificat',
    trustLine: 'Beta public gratuit · Fără câștiguri garantate · Fără pierderi ascunse',
    zeroState: 'Construim istoricul verificat de la zero',
  },

  manifesto: {
    heading: 'Platformele de pariuri afișează de obicei certitudine. BetGlitch arată dovezi.',
    paragraphs: [
      'Publicăm deciziile la care ne angajăm înainte de start. Păstrăm prețul, marcajul de timp și dovada. Menținem vizibil fiecare rezultat eligibil, inclusiv pierderile.',
      'Testăm continuu semnale, strategii și context de meci noi — nu ca să producem mai multe pontaje, ci ca să înțelegem ce îmbunătățește cu adevărat calitatea deciziilor.',
      'Nu promitem predicții perfecte. Promitem transparență, responsabilitate și îmbunătățire măsurabilă.',
    ],
  },

  home: {
    signalsHeading: 'Semnale live acum',
    browseAll: 'Vezi toate meciurile',

    differenceContrastHeading: 'Diferența BetGlitch',
    differenceOthersLabel: 'Majoritatea produselor de predicții',
    differenceOthersFlow: ['Predicție', 'Rezultat'],
    differenceUsLabel: 'BetGlitch',
    differenceUsFlow: ['Semnal', 'Dovezi', 'Angajament', 'Rezultat', 'Evaluare', 'Îmbunătățire'],

    rulesHeading: 'Reguli pe care produsul nu le poate încălca',
    rules: [
      'Nicio pierdere ștearsă',
      'Nicio cotă rescrisă',
      'Niciun pontaj retroactiv',
      'Niciun câștig garantat',
    ],

    improvementHeading: 'Măsurăm sistemul, nu doar scorul.',
    improvementBody:
      'BetGlitch testează continuu dacă filtrarea, dovezile de preț și contextul de meci îmbunătățesc cu adevărat calitatea deciziilor. Nu susținem că o fac deja — istoricul public există exact ca să aflăm. Ce nu îmbunătățește dovezile nu își câștigă locul în produs.',

    howHeading: 'Cum funcționează BetGlitch',
    differenceHeading: 'Nu orice semnal devine angajament public',
    differenceBody:
      'BetGlitch afișează mult mai multe semnale live decât angajează. Un semnal live este analiză curentă și se poate schimba; un angajament public este subsetul înghețat formal în registrul permanent de evaluare — și doar angajamentele eligibile încheiate contează pentru el.',
    notInPerformance: 'Nu face parte din performanța publică.',
    frozenIntro: 'Înghețate înainte de start. Acestea nu se mai pot schimba:',
    benefitsHeading: 'Ce poți face aici',
    benefits: [
      {
        title: 'Citește dovada, nu un pont',
        body: 'Fiecare meci arată scorul de semnal, piața la care se aplică și prețul înregistrat cu proveniența lui — nu doar o selecție.',
      },
      {
        title: 'Verifică dovezile',
        body: 'Angajamentele publice păstrează o pagină publică permanentă cu ce a fost înghețat, când și la ce casă de pariuri. Cotele nu sunt rescrise, iar pierderile nu sunt șterse.',
      },
      {
        title: 'Decizi singur',
        body: 'BetGlitch nu îți dimensionează miza și nu îți spune să pariezi. Îți arată ce a clasat, la ce preț și ce a urmat.',
      },
    ],
    coverageHeading: 'Acoperire',
    coverageBody: 'competiții europene, cu până la 14 zile în avans. Inclusiv:',
    viewAllLeagues: 'Vezi toate competițiile',
    settledLabel: 'Rezultate verificate',
    openRecord: 'Deschide istoricul verificat',
    finalHeading: 'Gratuit cât timp construim istoricul verificat',
    finalBody:
      'Nu ai ce cumpăra și nu este necesară o metodă de plată. Creează un cont pentru a folosi instrumentele de bankroll și pentru a urmări angajamentele publice până se încheie.',
    createAccount: 'Creează un cont gratuit',
    signalsError: 'Semnalele live nu au putut fi încărcate',
    signalsErrorBody:
      'Cererea către serviciul de semnale a eșuat. Contul tău nu are nicio problemă și niciun angajament public nu este afectat.',
    tryAgain: 'Încearcă din nou',
  },

  register: {
    heading: 'Creează-ți contul gratuit de beta',
    supporting:
      'Explorează semnalele live, folosește instrumentele de bankroll și urmărește istoricul public verificat BetGlitch pe măsură ce se dezvoltă.',
    freeDuringBeta: 'Gratuit în perioada de beta public',
    noPayment: 'Nu este necesară o metodă de plată',
    informational: 'Doar informativ — BetGlitch nu plasează pariuri',
    submit: 'Creează cont',
    submitting: 'Se creează contul…',
  },

  onboarding: {
    heading: 'Bine ai venit pe BetGlitch',
    body: 'Trei lucruri utile înainte să începi.',
    dismiss: 'Închide',
    actions: [
      {
        id: 'explore',
        title: 'Explorează semnalele curente',
        body: 'Vezi meciurile viitoare și semnalele lor live curente.',
        cta: 'Explorează semnalele live',
        href: '/explore',
      },
      {
        id: 'proof',
        title: 'Vezi angajamentele publice',
        body: 'Vezi cum diferă un angajament public imutabil de un semnal live care se schimbă.',
        cta: 'Vezi angajamentele publice',
        href: '/track-record#public-commitments',
      },
      {
        id: 'record',
        title: 'Verifică istoricul verificat',
        body: 'Analizează angajamentele eligibile încheiate pe măsură ce eșantionul crește.',
        cta: 'Deschide istoricul verificat',
        href: '/track-record#verified-record',
      },
    ],
  },

  beta: {
    primary:
      'BetGlitch este în prezent în beta public. Accesul este gratuit cât timp construim și validăm istoricul public verificat.',
  },

  dashboard: {
    title: 'Panoul tău',
    manageBankroll: 'Gestionează bugetul',
    recordBuilding:
      'Istoricul verificat este în construcție. Angajamentele eligibile încheiate vor apărea aici, inclusiv câștigurile și pierderile.',
  },

  auth: {
    login: {
      heading: 'Bine ai revenit',
      supporting: 'Autentifică-te pentru a continua pe BetGlitch',
      usernameLabel: 'Nume de utilizator sau email',
      usernamePlaceholder: 'Introdu numele de utilizator',
      passwordLabel: 'Parolă',
      passwordPlaceholder: 'Introdu parola',
      submit: 'Autentificare',
      submitting: 'Se autentifică…',
      noAccount: 'Nu ai cont?',
      signUp: 'Înregistrează-te',
      backHome: '← Înapoi acasă',
    },
    register: {
      usernameLabel: 'Nume de utilizator',
      usernamePlaceholder: 'Alege un nume de utilizator',
      emailLabel: 'Email',
      emailPlaceholder: 'adresa@ta.com',
      passwordLabel: 'Parolă',
      passwordPlaceholder: 'Cel puțin 8 caractere',
      confirmLabel: 'Confirmă parola',
      confirmPlaceholder: 'Confirmă parola',
      haveAccount: 'Ai deja cont?',
      signIn: 'Autentifică-te',
      backHome: '← Înapoi acasă',
      passwordTooShort: 'Parola trebuie să aibă cel puțin 8 caractere',
      passwordMismatch: 'Parolele nu corespund',
    },
  },

  record: {
    scopeHeading: 'Ce intră în acest istoric',
    scopeCutoff:
      'Istoricul public verificat începe de la data la care BetGlitch a început să verifice fiecare preț înregistrat. Predicțiile făcute înainte de această dată sunt păstrate ca moștenire și excluse din fiecare cifră de pe această pagină.',
    scopeImmutable:
      'Doar angajamentele publice imutabile intră în istoric — semnale înghețate înainte de start, cu selecția, scorul de semnal, cota înregistrată și casa de pariuri.',
    scopePending:
      'Angajamentele în așteptare nu sunt numărate ca rezultate, iar cele anulate sau nule sunt excluse din numitorii relevanți.',
    scopeLive:
      'Semnalele live afișate în altă parte a produsului nu intră niciodată în acest istoric decât dacă BetGlitch le angajează formal.',

    publishedHeading: 'Angajamente publice',
    publishedBody:
      'Semnale pe care BetGlitch le-a înghețat deliberat înainte de start pentru evaluare publică prospectivă. Odată angajate, selecția, prețul înregistrat și momentul publicării nu mai pot fi rescrise sau șterse discret.',
    publishedDistinction:
      'Un angajament public nu este același lucru cu fiecare semnal live. Semnalele live se pot schimba înainte de start. Angajamentele publice sunt subsetul pe care BetGlitch l-a plasat formal în registrul permanent de evaluare.',
    publishedStates:
      'Un angajament rămâne în așteptare până se termină meciul. Așteptarea nu este un rezultat: nu este numărată nicăieri în istoricul verificat de mai jos. După încheierea meciului se soluționează ca fiind câștigat sau pierdut, ori este marcat nul sau anulat și exclus din totalurile relevante.',
    publishedEmpty:
      'Niciun angajament public nu s-a încheiat încă, așa că aici nu este listat nimic. Angajamentele încheiate apar imediat ce se încheie unul — câștig sau pierdere.',
    publishedCount: 'Angajamente publice înregistrate',
    publishedLoading: 'Se încarcă angajamentele publice…',
    publishedError:
      'Angajamentele publice nu au putut fi încărcate. Istoricul în sine este intact — este o problemă de afișare și niciun angajament nu s-a modificat. Reîncarcă peste puțin timp.',
    publishedRetry: 'Încearcă din nou',
    publishedProofLink: 'Vezi dovada',
    publishedOddsLabel: 'Preț înregistrat',
    publishedAtLabel: 'Angajat',
    publishedNotCounted:
      'În așteptarea încheierii — nu este inclus în performanța verificată',
    publishedCountedIn: 'Numărat în istoricul verificat',

    policyLink: 'Cum sunt selectate angajamentele',
    policyBody:
      'Angajamentele sunt publicate automat, după o regulă fixă, pre-înregistrată — niciun om nu alege și nu respinge meciuri individuale. Un semnal live este angajat când toate condițiile sunt îndeplinite: trece de verificarea automată de eligibilitate (preț verificat cu proveniență completă de casă de pariuri și piață, marcaje de timp coerente, neînlocuit), mai sunt cel puțin 6 ore până la începerea meciului, iar meciul nu are deja un angajament. Selecția angajată este pur și simplu rezultatul clasat cel mai sus în piața sa. Publicarea în sine nu este o afirmație că semnalul are valoare de pariere dovedită.',

    verifiedHeading: 'Istoric verificat',
    verifiedBody:
      'Acesta este istoricul pe care nu îl putem rescrie. Aceste cifre agregate sunt calculate exclusiv din angajamente eligibile încheiate. Angajamentele în așteptare, cele nule și anulate, precum și fiecare predicție de dinainte de începerea verificării prețurilor sunt excluse — deci acest istoric este mai mic decât numărul de semnale produse de BetGlitch, iar asta este intenționat.',
    verifiedFromCommitments:
      'Angajamentele publice pot include intrări în așteptare. Istoricul verificat de mai jos conține doar angajamente eligibile încheiate.',

    noAccuracy: 'Niciun rezultat verificat încă',
    accuracyAppears:
      'Acuratețea apare după ce se încheie primul angajament public.',
    noSettled: 'Niciun angajament încheiat încă',
    winsLosses:
      'Atât câștigurile cât și pierderile sunt publicate aici pe măsură ce se încheie.',
    roiRestarted:
      'Istoricul nostru verificat de prețuri a fost restartat și se completează pe măsură ce meciurile se încheie.',
    noBreakdown:
      'Nicio defalcare încă. După ce angajamentele publice se încheie, acuratețea este împărțită aici pe rezultat prezis.',

    legacyHeading: 'Jurnal de predicții — nu este istoricul verificat',
    legacyAll: (n: number) => `Toate cele ${n} rânduri de mai jos au fost`,
    legacySome: (n: number, total: number) => `${n} din cele ${total} rânduri de mai jos au fost`,
    legacyBody:
      'înregistrate înainte ca BetGlitch să înceapă verificarea fiecărui preț înregistrat. Sunt păstrate public pentru că BetGlitch nu șterge istoricul, dar prețurile lor nu au putut fi verificate față de piața și casa de pariuri exacte, așa că sunt excluse din cifrele de acuratețe și ROI de mai sus și din orice afirmație publică de performanță.',
    legacyDetailBefore:
      'Aceste predicții sunt anterioare standardului verificat de preț al BetGlitch. Capturile lor originale de preț nu sunt folosite în raportarea publică de performanță, așa că fiecare cifră dependentă de preț — valoarea estimată și profitul/pierderea — afișează ',
    notVerified: 'Neverificat',
    legacyDetailAfter:
      ' în loc de un număr. Meciul, selecția și rezultatul real sunt în continuare afișate, pentru că nu depind de prețul înregistrat.',
    notVerifiedTitle:
      'Această predicție este anterioară standardului verificat de preț al BetGlitch. Captura originală de preț nu este folosită în raportarea publică de performanță.',
    notVerifiedMeaningBefore: ' înseamnă că prețul înregistrat al rândului este anterior standardului verificat de preț, așa că pentru el nu se publică nicio cifră dependentă de preț.',

    capturePanelTitle: 'Verifică dovezile, apoi urmărește-ne pe email.',
    capturePanelBody:
      'Verifică fiecare rezultat aici, apoi înscrie-te gratuit pentru actualizări despre angajamentele publice pe măsură ce istoricul verificat se dezvoltă.',
    capturePanelEyebrow: 'Canal bazat pe dovezi',
    capturePanelSeePublished: 'Vezi angajamentele publice',
    capturePanelSeeVerified: 'Vezi istoricul verificat',
    captureTitle: 'Primește rezumatul săptămânal',
    captureBody:
      'Un email săptămânal gratuit despre semnalele angajate de BetGlitch și cum s-au încheiat.',
    captureDefaultTitle: 'Urmărește angajamentele publice pe email',
    captureDefaultBody:
      'Un email săptămânal gratuit despre ce semnale a angajat BetGlitch și cum s-au încheiat — și câștiguri, și pierderi.',
  },

  footer: {
    tagline:
      'Semnale de piață pentru fotbal din competițiile europene. Semnalele selectate sunt angajate înainte de start cu cotele înregistrate și rămân publice după încheiere — câștig sau pierdere.',
    emailSupport: 'Scrie echipei de suport BetGlitch',
    platform: 'Platformă',
    explore: 'Explorează semnalele',
    dashboard: 'Panoul utilizatorului',
    trackRecord: 'Istoric verificat',
    pricing: 'Prețuri',
    resources: 'Resurse',
    howItWorks: 'Cum funcționează',
    blog: 'Blog',
    responsibleGambling: 'Joc responsabil',
    about: 'Despre',
    legal: 'Legal',
    terms: 'Termeni și condiții',
    privacy: 'Politica de confidențialitate',
    disclaimer: 'Precizări legale',
    noticeTitle: 'Notificare legală importantă',
    noticeOperatorStrong:
      'BetGlitch NU este operator de pariuri, casă de pariuri sau site de jocuri de noroc.',
    noticeOperatorRest:
      ' Nu acceptăm pariuri, mize sau depuneri de niciun fel. Semnalele noastre sunt oferite ',
    noticeOperatorEmphasis: 'exclusiv în scop informativ și de divertisment',
    noticeOperatorTail:
      ' și nu trebuie considerate sfaturi financiare sau de pariere.',
    noticeRiskLabel: 'Avertisment de risc:',
    noticeRiskBody:
      ' Pariurile implică un risc semnificativ, inclusiv pierderea întregii mize. Rezultatele din trecut nu indică rezultatele viitoare. Nu paria niciodată mai mult decât îți permiți să pierzi.',
    noticeRegionalLabel: 'Notificare regională:',
    noticeRegionalBody:
      ' Jocurile de noroc online pot fi restricționate sau ilegale în jurisdicția ta. Este responsabilitatea ta să te asiguri că respecți legislația locală înainte de a participa la orice activitate de jocuri de noroc.',
    noticeHelp:
      'Dacă tu sau cineva cunoscut are o problemă cu jocurile de noroc, caută ajutor:',
    ageNotice:
      'Acest site este destinat exclusiv adulților. Trebuie să ai cel puțin 18 ani pentru a folosi acest serviciu.',
    rights: 'BetGlitch Analytics. Toate drepturile rezervate.',
    operational: 'Sisteme funcționale',
  },

  responsibleUse:
    'BetGlitch publică semnale clasate doar cu scop informativ. Nu este casă de pariuri, nu acceptă pariuri și niciun rezultat nu este garantat — poți pierde tot ce mizezi. 18+. Joacă responsabil.',

  modelScoreNote:
    'Scorul de semnal clasifică preferința relativă a BetGlitch între rezultatele disponibile. Nu este o probabilitate calibrată.',
}

const COPY: Record<Lang, typeof EN> = { en: EN, ro: RO }

/** Resolve the copy bundle for a language, falling back to English. */
export function getCopy(lang?: string) {
  return COPY[(lang as Lang) in COPY ? (lang as Lang) : 'en']
}

// English defaults, for server components and tests that assert exact wording.
export const TERMS = EN.terms
export const WORKFLOW_STEPS = EN.workflow
export const HERO = EN.hero
export const RESPONSIBLE_USE = EN.responsibleUse
export const MODEL_SCORE_NOTE = EN.modelScoreNote

/**
 * Claims that must never reappear in public copy, in either language. Asserted
 * by tests. Each was unverifiable, unsupported by the verified record, or a
 * promise BetGlitch cannot keep.
 */
export const BANNED_CLAIMS = [
  'the only platform',
  'mathematically correctly',
  'ready to start winning',
  'join thousands',
  'thousands of users',
  'proven accuracy',
  'proven track record',
  'highest-quality opportunities',
  'highest quality opportunities',
  'guaranteed profit',
  'always win',
  'bet smart',
  // Added by the public-truth pass: each of these was live in product copy
  // while the product could not support it.
  'edge vs market',
  'edge vs. market',
  'live model signal',
  'models rerun',
  'ai-generated predictions',
  'ai-powered football predictions',
  'free weekly tips',
  'free betting tips',
  'profitable opportunities',
  'profitable sports betting',
  'verifiable edge',
  'proprietary model',
  'every prediction is published',
  'singura platformă',
  'matematic corect',
  'mii de utilizatori',
  'edge vs piață',
  'predicții generate de ai',
] as const
