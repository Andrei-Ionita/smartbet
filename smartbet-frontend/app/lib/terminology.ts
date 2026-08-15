/**
 * THE single source of public product vocabulary.
 *
 * BetGlitch has exactly three internal evidence states. Public pages describe
 * them in bettor-friendly language while keeping the underlying distinction:
 * with these words — previously each page invented its own ("recommendations",
 * "smart picks", "top quality bets", "predictions"), which made a mutable model
 * output and an immutable published claim look like the same object.
 *
 *   1. LIVE SIGNAL        — BetGlitch's current ranked output for an upcoming
 *                           fixture. MUTABLE. Not part of public performance.
 *   2. PUBLISHED PICK     — an immutable PublishedClaim, locked before kickoff
 *                           with its selection, score, odds, bookmaker and
 *                           provenance.
 *   3. RESULTS            — resolved, integrity-valid published claims ONLY.
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
  recordRedesign: {
    eyebrow: 'Current strategy record',
    title: 'How the current Gems perform',
    intro:
      'This page measures one thing: picks produced by the Gem strategy running today, published before kickoff and settled against the final result.',
    boundary:
      'Fixture analysis in Explore is never counted automatically. Earlier strategy versions are kept separately below and never change the current record.',
    flowExploreTitle: 'Explore',
    flowExploreBody: 'Search any fixture and inspect its probabilities, price and context.',
    flowGemTitle: 'Gem qualifies',
    flowGemBody: 'Up to three fixtures survive every current reliability and price gate.',
    flowPublishTitle: 'Published',
    flowPublishBody: 'The selection and recorded price are locked before kickoff.',
    flowResultTitle: 'Measured here',
    flowResultBody: 'After full-time, the locked pick becomes a win or a loss in this record.',
    currentHeading: 'Current Gem strategy',
    currentBody: 'Only picks carrying today\'s exact strategy version appear in these figures.',
    currentVersionLabel: 'Active methodology',
    zeroHeading: 'The current strategy starts at zero',
    zeroBody:
      'No current-generation Gem has been published yet. That is expected while no fixture passes every gate. The first qualifying pick will appear here before kickoff; its result will remain visible afterwards.',
    zeroAction: 'Explore today\'s fixtures',
    summaryPublished: 'Published Gems',
    summaryPending: 'Awaiting results',
    summarySettled: 'Settled and counted',
    summaryRecord: 'Win–loss record',
    summaryReturn: 'Flat-stake return',
    summaryReturnEmpty: 'Starts after the first settled pick',
    summaryReturnDetail: (stake: number, roi: string) =>
      `$${stake.toFixed(2)} staked · ${roi}% ROI`,
    currentPicksHeading: 'Published Gems from the current strategy',
    currentPicksBody:
      'This is the complete list for the active strategy. A published Gem cannot be edited, removed or re-priced after publication.',
    currentPicksEmpty: 'No current-strategy Gem has been published yet.',
    historicalHeading: 'Earlier strategy archive',
    historicalBody:
      'These picks were published under retired selection rules. They remain available for transparency, but they are not evidence for the current Gem strategy and are excluded from every figure above.',
    historicalSummary: (count: number) =>
      `${count} earlier published ${count === 1 ? 'pick' : 'picks'}`,
    historicalOpen: 'View earlier published picks',
    historicalVersionLabel: 'Retired methodology',
  },

  terms: {
    liveSignal: {
      label: 'Live signal',
      plural: 'Live signals',
      short: 'Live signal',
      definition:
        'BetGlitch’s current ranked outcome for an upcoming fixture, derived from prediction-model data. It can change before kickoff.',
      mutability:
        'Live signals update when the pipeline runs again, odds move, new model data arrives or a newer snapshot is generated.',
      notInRecord:
        'A live signal is not a betting recommendation, and it enters the public evaluation record only if BetGlitch formally commits it before kickoff.',
    },
    // The backend model stays PublishedClaim. Publicly, this is a published
    // pick: plain language for a selection locked before kickoff.
    publicCommitment: {
      label: 'Published pick',
      plural: 'Published picks',
      short: 'Locked',
      definition:
        'A selection BetGlitch published and locked before kickoff. Its selection, recorded price and publication time cannot be changed or deleted later.',
      notARecommendation:
        'Published means the pick existed before kickoff. It does not mean the outcome is guaranteed or that the methodology has proved an edge.',
      frozenFields: [
        'Selection', 'Signal score', 'Recorded odds', 'Bookmaker', 'Timestamps',
        'Provenance',
      ],
    },
    verifiedRecord: {
      label: 'Results',
      definition:
        'Every settled published pick, kept visible with its result — win or lose.',
      scope:
        'Pending picks are shown separately. Void or cancelled picks do not count in the performance totals.',
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
      body: 'We review prediction-model probabilities, market pricing and the available fixture context.',
    },
    {
      id: 'rank',
      title: 'Rank',
      body: 'BetGlitch ranks the available outcomes and surfaces the top-ranked one in each market, preserving what remains uncertain. Whether that ranking is useful is exactly what the public record measures.',
    },
    {
      id: 'publish',
      title: 'Publish',
      body: 'Selected picks are published and locked before kickoff with their recorded price and bookmaker.',
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
    headline: 'Every signal explained. Every published pick locked. Every result visible.',
    supporting:
      'Search any fixture, understand the probabilities, prices, context and uncertainty, then decide for yourself. When BetGlitch publishes a pick, we lock it before kickoff and keep the result visible — win or lose.',
    primaryCta: 'Explore live signals',
    secondaryCta: 'See published results',
    // Three commitments in one quiet line — a rule, not a badge.
    trustLine: 'Free public beta · No guaranteed wins · No hidden losses · Versioned methodology',
    zeroState: 'Current Gem strategy: no settled picks yet',
  },

  /**
   * The public manifesto. One authored text, rendered on the homepage and
   * About — never paraphrased per-page, or the philosophy drifts exactly the
   * way the vocabulary once did.
   */
  manifesto: {
    heading: 'Evidence before confidence. Results before claims. Improvement by version.',
    paragraphs: [
      'We publish selected picks before kickoff and lock the selection and recorded price. We keep every eligible result visible, including the losses.',
      'We continuously test signals, strategies and fixture context to learn what genuinely improves decision quality. Weak results and missing context are evidence too, so we publish them instead of hiding them.',
      'We do not promise an edge or that every version will improve. We promise a transparent process: name the rule, preserve the decision, publish the result and let the record decide what deserves to change.',
    ],
  },

  home: {
    signalsHeading: 'Live signals right now',
    gemsHeading: 'Today\'s qualified Gems',
    gemsLimit: 'Up to three can appear. If none pass every gate, we publish none.',
    gemsSupporting:
      'The few fixtures that passed every reliability, market-consensus and verified-price gate. Ranked by model probability–payout balance, not by the biggest odds.',
    scanFixtures: 'fixtures scanned',
    scanPredictions: 'prediction-ready',
    scanQualified: 'passed every gate',
    scanShown: 'shown',
    noGemsHeading: 'No fixture earned Gem status',
    noGemsBody:
      'None passed every reliability, consensus and price test. Showing nothing is the filter working—not a reason to lower the standard.',
    diagnosticsHeading: 'Why fixtures were filtered out',
    diagnosticsBody:
      'This scan reports where candidates stopped. One fixture can fail more than one strategy check, so the reason counts may overlap.',
    diagnosticsSignalPrice: 'Signal or verified-price readiness',
    diagnosticsReliability: 'League and fixture reliability',
    diagnosticsProviderValue: 'Model-versus-price evidence',
    diagnosticsConsensus: 'Cross-market agreement',
    diagnosticsPriceQuality: 'Price quality and coverage',
    diagnosticsAffected: 'fixtures affected',
    methodologyCta: 'Read the exact methodology',
    browseAll: 'Browse all fixtures',

    // ── The BetGlitch difference: a conceptual contrast, not a feature list.
    differenceContrastHeading: 'The BetGlitch difference',
    differenceOthersLabel: 'Most prediction products',
    differenceOthersFlow: ['Prediction', 'Result'],
    differenceUsLabel: 'BetGlitch',
    differenceUsFlow: ['Signal', 'Evidence', 'Published pick', 'Result', 'Evaluation', 'Improvement'],

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
    improvementHeading: 'Improvement is a process we can prove, not a promise we ask you to trust.',
    improvementBody:
      'Every published pick stores the exact ranking version that produced it. When the logic changes, the version changes too, so results from different strategies can be compared instead of blended. We do not claim the current score has demonstrated an edge — the public results exist to test that honestly.',

    howHeading: 'How BetGlitch works',
    differenceHeading: 'Published before kickoff. Visible after the result.',
    differenceBody:
      'When BetGlitch publishes a pick, its selection and recorded price are locked. We cannot add it after the match, edit it later or remove it when it loses.',
    notInPerformance: 'Not part of public performance.',
    frozenIntro: 'Frozen before kickoff. These can never change:',
    benefitsHeading: 'What you get for every decision',
    benefits: [
      {
        title: 'Fixture context, including the gaps',
        body: 'See the market, top-ranked outcome, signal score, verified price, recent form and every unavailable input we cannot responsibly fill in.',
      },
      {
        title: 'A verifiable decision trail',
        body: 'Each published pick preserves the selection, price freshness and bookmaker before kickoff. Methodology and timestamp details remain available for anyone who wants to verify them.',
      },
      {
        title: 'The evidence to decide yourself',
        body: 'Review every eligible result, the measured weaknesses of the current score and the context behind a fixture. BetGlitch never turns uncertainty into a guaranteed bet.',
      },
    ],
    coverageHeading: 'Coverage',
    coverageBody: 'European competitions, up to 14 days ahead. Including:',
    viewAllLeagues: 'View all competitions',
    settledLabel: 'current-strategy results',
    openRecord: 'See all results',
    finalHeading: 'Free while we build the public results',
    finalBody:
      'There is nothing to buy and no account or payment method is required. Explore any fixture and inspect every published pick as it settles.',
    createAccount: 'Open the public record',
    signalsError: 'Live signals could not be loaded',
    signalsErrorBody:
      'The request to the signal service failed. Nothing is wrong with your account and no published pick is affected.',
    tryAgain: 'Try again',
  },

  register: {
    heading: 'Create your free beta account',
    supporting:
      'Explore live signals, use the bankroll tools and follow BetGlitch’s verified public record as it develops.',
    freeDuringBeta: 'Free during public beta',
    noPayment: 'No payment method is required',
    informational: 'Informational only — BetGlitch does not place bets',
    agreementBefore: 'By creating an account, you agree to the',
    termsLabel: 'Terms of Service',
    agreementAnd: 'and acknowledge the',
    privacyLabel: 'Privacy Policy',
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
        title: 'See published picks',
        body: 'See the selections BetGlitch locked before kickoff and left visible afterwards.',
        cta: 'See published picks',
        href: '/track-record#published-picks',
      },
      {
        id: 'record',
        title: 'Check the results',
        body: 'Review every eligible settled pick as the sample develops.',
        cta: 'See all results',
        href: '/track-record#results',
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
      'The public results are being built. Eligible settled picks will appear here, including both wins and losses.',
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
    scopeHeading: 'How these results work',
    scopeCutoff:
      'Current results contain only Gems published by the active strategy version. Earlier strategies remain available in the separate archive and never change these figures.',
    scopeImmutable:
      'Only picks published and locked before kickoff can enter these results.',
    scopePending:
      'Pending picks are not results. Void or cancelled picks are kept visible but excluded from the relevant totals.',
    scopeLive:
      'Live fixture analysis can change and is not counted unless BetGlitch publishes and locks the pick before kickoff.',

    publishedHeading: 'Published picks',
    publishedBody:
      'These picks were published before kickoff. Their selection, recorded price and publication time cannot be edited later or removed when they lose.',
    // The sentence a confused visitor needs most: why fewer fixtures here
    // than the homepage shows? Because commitment is a separate, gated act
    // (policy v1) — not a quality ranking of the live signals.
    publishedDistinction:
      'Live fixture analysis may change as new data arrives. A published pick is different: it is locked and stays public.',
    publishedStates:
      'A pick stays pending until the match finishes. It then appears as won, lost, void or cancelled. Pending picks do not count in the totals.',
    publishedEmpty:
      'No pick has been published under the current standard yet. New picks appear here as soon as they are locked — before kickoff.',
    publishedCount: 'Published picks',
    publishedLoading: 'Loading published picks…',
    publishedError:
      'Published picks could not be loaded. This is a display problem; no stored pick or result has changed. Reload in a moment.',
    publishedRetry: 'Try again',
    publishedProofLink: 'View pick',
    publishedOddsLabel: 'Recorded price',
    publishedAtLabel: 'Published',
    publishedPriceAgeLabel: 'Price age when published',
    publishedVersionLabel: 'Methodology version',
    publishedFreshLabel: 'Within the 12-hour freshness rule',
    publishedStaleLabel: 'Legacy price age — excluded from performance',
    publishedNotCounted: 'Awaiting the result — not counted yet',
    publishedExcludedFromRecord: 'Kept visible — excluded from performance totals',
    publishedCountedIn: 'Included in the results',
    publishedExcludedStalePrice: (hours: string) =>
      `Excluded from performance: the recorded price was ${hours}h old when published; the limit is 12h.`,
    publishedExcludedMissingPrice:
      'Excluded from performance: no verifiably fresh recorded price was available.',
    publishedExcludedIntegrity:
      'Excluded from performance: the stored integrity check did not pass.',
    publishedExcludedSuperseded:
      'Excluded from performance: this pick was replaced by a published correction.',
    publishedExcludedVoid:
      'Excluded from performance: the match was void, so no stake is scored.',
    publishedExcludedCancelled:
      'Excluded from performance: the match was cancelled, so no stake is scored.',
    publishedExcludedGeneric:
      'Kept visible, but excluded because it does not meet every performance-record rule.',

    // Honest publication policy — AUTOMATIC since policy v1 (2026-08-08).
    // This copy must state exactly what core/management/commands/
    // auto_publish_claims.py does and nothing more. Do not claim "strongest
    // signal" or "best value" here — no such rule exists; the committed
    // selection is the top-ranked outcome by construction, and every other
    // criterion is a machine-checked gate, not a judgment call.
    policyLink: 'How picks are published',
    policyBody:
      'Picks are published automatically by a fixed rule; no person adds or removes individual fixtures after seeing the outcome. A pick needs a verified recent price, complete bookmaker and market details, coherent timestamps and at least six hours before kickoff. Publication proves the pick existed in advance, not that it is guaranteed or will win long-term.',

    verifiedHeading: 'Results',
    verifiedBody:
      'Wins and losses have equal visibility. The totals use eligible settled picks only; pending, void, cancelled and legacy rows are excluded so the denominator remains honest.',
    verifiedFromCommitments:
      'The list above contains every published pick. This summary shows exactly how completed matches become the performance total.',
    reconciliationHeading: 'How every published pick is accounted for',
    reconciliationBody:
      'Published picks split into two groups: awaiting a result or finished. Finished picks then split into counted and excluded.',
    reconciliationPublished: 'Published in total',
    reconciliationPending: 'Awaiting result',
    reconciliationFinished: 'Matches finished',
    reconciliationEquation: (finished: number, counted: number, excluded: number) =>
      `${finished} finished = ${counted} counted + ${excluded} excluded`,
    reconciliationExcludedNote:
      'Excluded matches remain visible above, but they do not change accuracy or ROI. Their exact reason appears directly on each pick.',

    noAccuracy: 'No verified results yet',
    accuracyAppears: 'Accuracy appears once the first published pick settles.',
    noSettled: 'No settled picks yet',
    winsLosses: 'Wins and losses are both published here as they settle.',
    roiRestarted:
      'Our verified pricing record restarted and fills in as matches settle.',
    noBreakdown:
      'No breakdown yet. Once published picks settle, results are grouped by their recorded market here.',

    legacyHeading: 'Legacy prediction log — not included in results',
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

    capturePanelTitle: 'Inspect the published results.',
    capturePanelBody:
      'Review every eligible result and every pre-kickoff published pick directly. Nothing is hidden behind an account or email form.',
    capturePanelEyebrow: 'Public evidence',
    capturePanelSeePublished: 'See published picks',
    capturePanelSeeVerified: 'See all results',
    captureTitle: 'Accountless public beta',
    captureBody:
      'No email, login or payment is required. The complete public record remains available for anyone to inspect.',
    captureDefaultTitle: 'Follow every published pick publicly',
    captureDefaultBody:
      'Inspect which picks BetGlitch published and how they settled — wins and losses both — without creating an account.',
  },

  footer: {
    tagline:
      'Football decision intelligence across European competitions. Published picks are locked before kickoff and every result stays visible — win or lose.',
    emailSupport: 'Email BetGlitch support',
    platform: 'Platform',
    explore: 'Explore signals',
    dashboard: 'User dashboard',
    trackRecord: 'Results',
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
  recordRedesign: {
    eyebrow: 'Istoricul strategiei actuale',
    title: 'Cum performează Gem-urile actuale',
    intro:
      'Această pagină măsoară un singur lucru: selecțiile produse de strategia Gem activă astăzi, publicate înainte de start și evaluate după rezultatul final.',
    boundary:
      'Analiza meciurilor din Explore nu este numărată automat. Versiunile anterioare ale strategiei sunt păstrate separat mai jos și nu modifică istoricul actual.',
    flowExploreTitle: 'Explorează',
    flowExploreBody: 'Caută orice meci și verifică probabilitățile, prețul și contextul.',
    flowGemTitle: 'Gem calificat',
    flowGemBody: 'Cel mult trei meciuri trec toate filtrele actuale de fiabilitate și preț.',
    flowPublishTitle: 'Publicat',
    flowPublishBody: 'Selecția și prețul înregistrat sunt blocate înainte de start.',
    flowResultTitle: 'Măsurat aici',
    flowResultBody: 'După meci, selecția blocată devine câștig sau pierdere în acest istoric.',
    currentHeading: 'Strategia Gem actuală',
    currentBody: 'Doar selecțiile care poartă versiunea exactă a strategiei de astăzi intră în aceste cifre.',
    currentVersionLabel: 'Metodologie activă',
    zeroHeading: 'Strategia actuală începe de la zero',
    zeroBody:
      'Niciun Gem din generația actuală nu a fost publicat încă. Este normal cât timp niciun meci nu trece toate filtrele. Prima selecție calificată va apărea aici înainte de start, iar rezultatul ei va rămâne vizibil după meci.',
    zeroAction: 'Explorează meciurile de astăzi',
    summaryPublished: 'Gem-uri publicate',
    summaryPending: 'În așteptarea rezultatului',
    summarySettled: 'Încheiate și numărate',
    summaryRecord: 'Bilanț câștig–pierdere',
    summaryReturn: 'Rezultat cu miză fixă',
    summaryReturnEmpty: 'Începe după prima selecție încheiată',
    summaryReturnDetail: (stake: number, roi: string) =>
      `$${stake.toFixed(2)} mizate · ROI ${roi}%`,
    currentPicksHeading: 'Gem-uri publicate de strategia actuală',
    currentPicksBody:
      'Aceasta este lista completă pentru strategia activă. Un Gem publicat nu poate fi modificat, șters sau repriced după publicare.',
    currentPicksEmpty: 'Niciun Gem al strategiei actuale nu a fost publicat încă.',
    historicalHeading: 'Arhiva strategiilor anterioare',
    historicalBody:
      'Aceste selecții au fost publicate sub reguli retrase. Rămân disponibile pentru transparență, dar nu sunt dovezi pentru strategia Gem actuală și sunt excluse din toate cifrele de mai sus.',
    historicalSummary: (count: number) =>
      `${count} ${count === 1 ? 'selecție publicată anterior' : 'selecții publicate anterior'}`,
    historicalOpen: 'Vezi selecțiile publicate anterior',
    historicalVersionLabel: 'Metodologie retrasă',
  },

  terms: {
    liveSignal: {
      label: 'Semnal live',
      plural: 'Semnale live',
      short: 'Semnal live',
      definition:
        'Rezultatul clasat curent al BetGlitch pentru un meci viitor, derivat din datele modelului de predicție. Se poate schimba până la start.',
      mutability:
        'Semnalele live se actualizează când pipeline-ul rulează din nou, când cotele se mișcă, când apar date noi de model sau când se generează un snapshot mai recent.',
      notInRecord:
        'Un semnal live nu este o recomandare de pariere și intră în registrul public de evaluare doar dacă BetGlitch îl angajează formal înainte de start.',
    },
    publicCommitment: {
      label: 'Selecție publicată',
      plural: 'Selecții publicate',
      short: 'Blocată',
      definition:
        'O selecție publicată și blocată de BetGlitch înainte de start. Selecția, cota înregistrată și momentul publicării nu mai pot fi modificate sau șterse.',
      notARecommendation:
        'Publicată înseamnă că selecția exista înainte de start. Nu înseamnă că rezultatul este garantat sau că metodologia a dovedit un avantaj.',
      frozenFields: [
        'Selecție', 'Scor semnal', 'Cota înregistrată', 'Casa de pariuri',
        'Marcaje de timp', 'Proveniență',
      ],
    },
    verifiedRecord: {
      label: 'Rezultate',
      definition:
        'Fiecare selecție publicată încheiată, păstrată vizibilă cu rezultatul ei — câștig sau pierdere.',
      scope:
        'Selecțiile în așteptare sunt afișate separat. Cele nule sau anulate nu intră în totalurile de performanță.',
    },
  },

  workflow: [
    {
      id: 'analyse',
      title: 'Analizăm',
      body: 'Analizăm probabilitățile modelului de predicție, prețurile pieței și contextul de meci disponibil.',
    },
    {
      id: 'rank',
      title: 'Clasăm',
      body: 'BetGlitch clasează rezultatele disponibile și îl arată pe cel mai bine clasat din fiecare piață, păstrând vizibil ce rămâne incert. Dacă această clasare este utilă este exact ceea ce măsoară registrul public.',
    },
    {
      id: 'publish',
      title: 'Publicăm',
      body: 'Selecțiile alese sunt publicate și blocate înainte de start, cu cota înregistrată și casa de pariuri.',
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
    headline: 'Fiecare semnal explicat. Fiecare selecție blocată. Fiecare rezultat vizibil.',
    supporting:
      'Caută orice meci, înțelege probabilitățile, prețurile, contextul și incertitudinea, apoi decide singur. Când BetGlitch publică o selecție, o blocăm înainte de start și păstrăm rezultatul vizibil — câștig sau pierdere.',
    primaryCta: 'Explorează semnalele live',
    secondaryCta: 'Vezi rezultatele publicate',
    trustLine: 'Beta public gratuit · Fără câștiguri garantate · Fără pierderi ascunse · Metodologie versionată',
    zeroState: 'Strategia Gem actuală: niciun rezultat încheiat încă',
  },

  manifesto: {
    heading: 'Dovezi înaintea încrederii. Rezultate înaintea afirmațiilor. Îmbunătățire pe versiuni.',
    paragraphs: [
      'Publicăm selecțiile alese înainte de start și blocăm alegerea și cota înregistrată. Menținem vizibil fiecare rezultat eligibil, inclusiv pierderile.',
      'Testăm continuu semnale, strategii și context de meci ca să aflăm ce îmbunătățește cu adevărat calitatea deciziilor. Rezultatele slabe și contextul lipsă sunt tot dovezi, așa că le publicăm în loc să le ascundem.',
      'Nu promitem un avantaj și nici că fiecare versiune va fi mai bună. Promitem un proces transparent: numim regula, păstrăm decizia, publicăm rezultatul și lăsăm istoricul să decidă ce merită schimbat.',
    ],
  },

  home: {
    signalsHeading: 'Semnale live acum',
    gemsLimit: 'Pot apărea cel mult trei. Dacă niciunul nu trece toate filtrele, nu publicăm nimic.',
    gemsHeading: 'Gem-urile calificate astăzi',
    gemsSupporting:
      'Puținele meciuri care au trecut toate filtrele de fiabilitate, consens între piețe și preț verificat. Clasate după echilibrul probabilitate–plată al modelului, nu după cea mai mare cotă.',
    scanFixtures: 'meciuri scanate',
    scanPredictions: 'cu predicții disponibile',
    scanQualified: 'au trecut toate filtrele',
    scanShown: 'afișate',
    noGemsHeading: 'Niciun meci nu a obținut statutul Gem',
    noGemsBody:
      'Niciunul nu a trecut toate testele de fiabilitate, consens și preț. Faptul că nu afișăm nimic arată că filtrul funcționează—nu este un motiv să coborâm standardul.',
    diagnosticsHeading: 'De ce au fost filtrate meciurile',
    diagnosticsBody:
      'Scanarea arată unde s-au oprit candidații. Un meci poate eșua mai multe verificări ale strategiei, deci numerele motivelor se pot suprapune.',
    diagnosticsSignalPrice: 'Semnal sau preț verificat insuficient',
    diagnosticsReliability: 'Fiabilitatea ligii și a meciului',
    diagnosticsProviderValue: 'Dovezi model–preț',
    diagnosticsConsensus: 'Acord între piețe',
    diagnosticsPriceQuality: 'Calitatea și acoperirea prețului',
    diagnosticsAffected: 'meciuri afectate',
    methodologyCta: 'Citește metodologia exactă',
    browseAll: 'Vezi toate meciurile',

    differenceContrastHeading: 'Diferența BetGlitch',
    differenceOthersLabel: 'Majoritatea produselor de predicții',
    differenceOthersFlow: ['Predicție', 'Rezultat'],
    differenceUsLabel: 'BetGlitch',
    differenceUsFlow: ['Semnal', 'Dovezi', 'Selecție publicată', 'Rezultat', 'Evaluare', 'Îmbunătățire'],

    rulesHeading: 'Reguli pe care produsul nu le poate încălca',
    rules: [
      'Nicio pierdere ștearsă',
      'Nicio cotă rescrisă',
      'Niciun pontaj retroactiv',
      'Niciun câștig garantat',
    ],

    improvementHeading: 'Îmbunătățirea este un proces demonstrabil, nu o promisiune pe care cerem să o crezi.',
    improvementBody:
      'Fiecare selecție publicată păstrează versiunea exactă de clasare care a produs-o. Când logica se schimbă, se schimbă și versiunea, astfel încât rezultatele strategiilor diferite să poată fi comparate, nu amestecate. Nu susținem că scorul actual a demonstrat un avantaj — rezultatele publice există ca să testeze asta onest.',

    howHeading: 'Cum funcționează BetGlitch',
    differenceHeading: 'Publicată înainte de start. Vizibilă după rezultat.',
    differenceBody:
      'Când BetGlitch publică o selecție, alegerea și cota înregistrată sunt blocate. Nu o putem adăuga după meci, modifica ulterior sau șterge atunci când pierde.',
    notInPerformance: 'Nu face parte din performanța publică.',
    frozenIntro: 'Înghețate înainte de start. Acestea nu se mai pot schimba:',
    benefitsHeading: 'Ce primești pentru fiecare decizie',
    benefits: [
      {
        title: 'Contextul meciului, inclusiv lipsurile',
        body: 'Vezi piața, rezultatul clasat primul, scorul de semnal, prețul verificat, forma recentă și fiecare informație indisponibilă pe care nu o putem completa responsabil.',
      },
      {
        title: 'Un traseu verificabil al deciziei',
        body: 'Fiecare selecție publicată păstrează alegerea, vechimea cotei și casa de pariuri înainte de start. Detaliile metodologiei și marcajului de timp rămân disponibile pentru verificare.',
      },
      {
        title: 'Dovezile pentru propria decizie',
        body: 'Analizează fiecare rezultat eligibil, slăbiciunile măsurate ale scorului actual și contextul meciului. BetGlitch nu transformă niciodată incertitudinea într-un pariu garantat.',
      },
    ],
    coverageHeading: 'Acoperire',
    coverageBody: 'competiții europene, cu până la 14 zile în avans. Inclusiv:',
    viewAllLeagues: 'Vezi toate competițiile',
    settledLabel: 'rezultate ale strategiei actuale',
    openRecord: 'Vezi toate rezultatele',
    finalHeading: 'Gratuit cât timp construim rezultatele publice',
    finalBody:
      'Nu ai ce cumpăra și nu este necesar niciun cont sau o metodă de plată. Explorează orice meci și verifică fiecare selecție publicată până la decontare.',
    createAccount: 'Deschide istoricul public',
    signalsError: 'Semnalele live nu au putut fi încărcate',
    signalsErrorBody:
      'Cererea către serviciul de semnale a eșuat. Contul tău nu are nicio problemă și nicio selecție publicată nu este afectată.',
    tryAgain: 'Încearcă din nou',
  },

  register: {
    heading: 'Creează-ți contul gratuit de beta',
    supporting:
      'Explorează semnalele live, folosește instrumentele de bankroll și urmărește istoricul public verificat BetGlitch pe măsură ce se dezvoltă.',
    freeDuringBeta: 'Gratuit în perioada de beta public',
    noPayment: 'Nu este necesară o metodă de plată',
    informational: 'Doar informativ — BetGlitch nu plasează pariuri',
    agreementBefore: 'Prin crearea unui cont, accepți',
    termsLabel: 'Termenii de utilizare',
    agreementAnd: 'și confirmi că ai citit',
    privacyLabel: 'Politica de confidențialitate',
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
        title: 'Vezi selecțiile publicate',
        body: 'Vezi selecțiile pe care BetGlitch le-a blocat înainte de start și le-a păstrat vizibile.',
        cta: 'Vezi selecțiile publicate',
        href: '/track-record#published-picks',
      },
      {
        id: 'record',
        title: 'Verifică rezultatele',
        body: 'Analizează fiecare selecție eligibilă încheiată pe măsură ce eșantionul crește.',
        cta: 'Vezi toate rezultatele',
        href: '/track-record#results',
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
      'Rezultatele publice sunt în construcție. Selecțiile eligibile încheiate vor apărea aici, inclusiv câștigurile și pierderile.',
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
    scopeHeading: 'Cum funcționează aceste rezultate',
    scopeCutoff:
      'Rezultatele actuale conțin doar Gem-urile publicate de versiunea activă a strategiei. Strategiile anterioare rămân în arhiva separată și nu modifică aceste cifre.',
    scopeImmutable:
      'Doar selecțiile publicate și blocate înainte de start pot intra în aceste rezultate.',
    scopePending:
      'Selecțiile în așteptare nu sunt rezultate. Cele nule sau anulate rămân vizibile, dar sunt excluse din totalurile relevante.',
    scopeLive:
      'Analiza live se poate schimba și nu este numărată decât dacă BetGlitch publică și blochează selecția înainte de start.',

    publishedHeading: 'Selecții publicate',
    publishedBody:
      'Aceste selecții au fost publicate înainte de start. Alegerea, cota înregistrată și momentul publicării nu pot fi modificate ulterior sau șterse când pierd.',
    publishedDistinction:
      'Analiza live se poate schimba când apar date noi. O selecție publicată este diferită: este blocată și rămâne publică.',
    publishedStates:
      'O selecție rămâne în așteptare până se termină meciul, apoi apare drept câștigată, pierdută, nulă sau anulată. Cele în așteptare nu intră în totaluri.',
    publishedEmpty:
      'Nicio selecție nu a fost publicată încă sub standardul actual. Selecțiile noi apar aici imediat ce sunt blocate — înainte de start.',
    publishedCount: 'Selecții publicate',
    publishedLoading: 'Se încarcă selecțiile publicate…',
    publishedError:
      'Selecțiile publicate nu au putut fi încărcate. Este o problemă de afișare; nicio selecție și niciun rezultat stocat nu s-au modificat. Reîncarcă peste puțin timp.',
    publishedRetry: 'Încearcă din nou',
    publishedProofLink: 'Vezi selecția',
    publishedOddsLabel: 'Preț înregistrat',
    publishedAtLabel: 'Publicată',
    publishedPriceAgeLabel: 'Vechimea cotei la publicare',
    publishedVersionLabel: 'Versiunea metodologiei',
    publishedFreshLabel: 'În limita de prospețime de 12 ore',
    publishedStaleLabel: 'Preț istoric prea vechi — exclus din performanță',
    publishedNotCounted:
      'În așteptarea rezultatului — nu este numărată încă',
    publishedExcludedFromRecord:
      'Păstrată vizibilă — exclusă din totalurile de performanță',
    publishedCountedIn: 'Inclusă în rezultate',
    publishedExcludedStalePrice: (hours: string) =>
      `Exclusă din performanță: prețul înregistrat avea ${hours}h la publicare; limita este 12h.`,
    publishedExcludedMissingPrice:
      'Exclusă din performanță: nu era disponibil un preț înregistrat recent și verificabil.',
    publishedExcludedIntegrity:
      'Exclusă din performanță: verificarea integrității datelor stocate nu a trecut.',
    publishedExcludedSuperseded:
      'Exclusă din performanță: selecția a fost înlocuită de o corecție publicată.',
    publishedExcludedVoid:
      'Exclusă din performanță: meciul a fost declarat nul, deci nu se calculează nicio miză.',
    publishedExcludedCancelled:
      'Exclusă din performanță: meciul a fost anulat, deci nu se calculează nicio miză.',
    publishedExcludedGeneric:
      'Rămâne vizibilă, dar este exclusă deoarece nu îndeplinește toate regulile istoricului de performanță.',

    policyLink: 'Cum sunt publicate selecțiile',
    policyBody:
      'Selecțiile sunt publicate automat după o regulă fixă; nicio persoană nu adaugă sau elimină meciuri individuale după ce vede rezultatul. O selecție are nevoie de o cotă recentă verificată, detalii complete despre casa de pariuri și piață, marcaje de timp coerente și cel puțin șase ore până la start. Publicarea dovedește că selecția exista în avans, nu că este garantată sau că va câștiga pe termen lung.',

    verifiedHeading: 'Rezultate',
    verifiedBody:
      'Câștigurile și pierderile au aceeași vizibilitate. Totalurile folosesc doar selecții eligibile încheiate; cele în așteptare, nule, anulate și legacy sunt excluse pentru ca numitorul să rămână onest.',
    verifiedFromCommitments:
      'Lista de mai sus conține fiecare selecție publicată. Acest rezumat arată exact cum meciurile încheiate formează totalul de performanță.',
    reconciliationHeading: 'Cum este contabilizată fiecare selecție publicată',
    reconciliationBody:
      'Selecțiile publicate se împart în două grupuri: în așteptarea rezultatului sau încheiate. Cele încheiate se împart apoi în numărate și excluse.',
    reconciliationPublished: 'Publicate în total',
    reconciliationPending: 'În așteptarea rezultatului',
    reconciliationFinished: 'Meciuri încheiate',
    reconciliationEquation: (finished: number, counted: number, excluded: number) =>
      `${finished} încheiate = ${counted} numărate + ${excluded} excluse`,
    reconciliationExcludedNote:
      'Meciurile excluse rămân vizibile mai sus, dar nu modifică acuratețea sau ROI. Motivul exact apare direct pe fiecare selecție.',

    noAccuracy: 'Niciun rezultat verificat încă',
    accuracyAppears:
      'Acuratețea apare după ce se încheie prima selecție publicată.',
    noSettled: 'Nicio selecție încheiată încă',
    winsLosses:
      'Atât câștigurile cât și pierderile sunt publicate aici pe măsură ce se încheie.',
    roiRestarted:
      'Istoricul nostru verificat de prețuri a fost restartat și se completează pe măsură ce meciurile se încheie.',
    noBreakdown:
      'Nicio defalcare încă. După ce selecțiile publicate se încheie, rezultatele sunt grupate aici după piața înregistrată.',

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

    capturePanelTitle: 'Verifică rezultatele publicate.',
    capturePanelBody:
      'Analizează direct fiecare rezultat eligibil și fiecare selecție publicată înainte de start. Nimic nu este ascuns în spatele unui cont sau formular de email.',
    capturePanelEyebrow: 'Dovezi publice',
    capturePanelSeePublished: 'Vezi selecțiile publicate',
    capturePanelSeeVerified: 'Vezi toate rezultatele',
    captureTitle: 'Beta public fără cont',
    captureBody:
      'Nu este necesar niciun email, cont sau plată. Istoricul public complet rămâne disponibil oricui pentru verificare.',
    captureDefaultTitle: 'Urmărește public fiecare selecție',
    captureDefaultBody:
      'Verifică selecțiile publicate de BetGlitch și cum s-au încheiat — și câștiguri, și pierderi — fără să creezi un cont.',
  },

  footer: {
    tagline:
      'Informații pentru decizii de fotbal din competițiile europene. Selecțiile publicate sunt blocate înainte de start, iar fiecare rezultat rămâne vizibil — câștig sau pierdere.',
    emailSupport: 'Scrie echipei de suport BetGlitch',
    platform: 'Platformă',
    explore: 'Explorează semnalele',
    dashboard: 'Panoul utilizatorului',
    trackRecord: 'Rezultate',
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
