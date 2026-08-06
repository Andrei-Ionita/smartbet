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
 *   2. PUBLISHED PICK     — an immutable PublishedClaim, frozen before kickoff
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
        'Live signals are not part of the verified record unless BetGlitch publishes them as an immutable claim.',
    },
    publishedPick: {
      label: 'Published pick',
      plural: 'Published picks',
      short: 'Published',
      definition:
        'A pick BetGlitch froze before kickoff — selection, signal score, recorded odds, bookmaker and timestamps can no longer change.',
      frozenFields: [
        'Selection', 'Signal score', 'Recorded odds', 'Bookmaker', 'Timestamps',
        'Provenance',
      ],
    },
    verifiedRecord: {
      label: 'Verified record',
      definition:
        'Every published pick that has settled, kept public with its result — win or lose.',
      scope:
        'Only settled published picks count. Pending picks are shown separately, and void or cancelled picks are excluded from the totals.',
    },
  },

  workflow: [
    {
      id: 'explore',
      title: 'Explore',
      body: 'Browse current live signals for upcoming fixtures across European competitions.',
    },
    {
      id: 'publish',
      title: 'Publish',
      body: 'Selected picks are frozen before kickoff with their recorded odds and bookmaker.',
    },
    {
      id: 'verify',
      title: 'Verify',
      body: 'Results are added after full-time. Wins and losses both stay public.',
    },
  ],

  hero: {
    eyebrow: 'FREE PUBLIC BETA',
    headline: 'Verifiable football market signals.',
    supporting:
      'Explore provider-derived signals, see which picks BetGlitch freezes before kickoff, and verify every settled result — win or lose.',
    primaryCta: 'Explore live signals',
    secondaryCta: 'View verified record',
    zeroState: 'Building the verified record from zero',
  },

  home: {
    signalsHeading: 'Live signals right now',
    browseAll: 'Browse all fixtures',
    howHeading: 'How BetGlitch works',
    differenceHeading: 'Not every signal becomes a published pick',
    differenceBody:
      'BetGlitch shows far more live signals than it publishes. Only published picks count towards the verified record, and you can tell the two apart everywhere in the product.',
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
        body: 'Published picks keep a permanent public page showing what was frozen, when, and at which bookmaker. Odds are never rewritten and losses are never deleted.',
      },
      {
        title: 'Decide for yourself',
        body: 'BetGlitch does not size stakes for you and does not tell you to bet. It shows what it ranked, at what price, and what happened next.',
      },
    ],
    coverageHeading: 'Coverage',
    coverageBody: 'European competitions, up to 14 days ahead. Including:',
    viewAllLeagues: 'View all competitions',
    settledLabel: 'Settled published picks',
    openRecord: 'Open the verified record',
    finalHeading: 'Free while we build the verified record',
    finalBody:
      'There is nothing to buy and no payment method is required. Create an account to use the bankroll tools and follow published picks as they settle.',
    createAccount: 'Create a free account',
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
        title: 'Understand published proof',
        body: 'See how an immutable published claim differs from a changing live prediction.',
        cta: 'See published picks',
        href: '/track-record#published-picks',
      },
      {
        id: 'record',
        title: 'Follow the verified record',
        body: 'Review settled published picks as the sample develops.',
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
      'The verified record is being built. Settled published picks will appear here, including both wins and losses.',
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
      'The verified public record begins at a clean pricing-integrity cutoff. Predictions made before it are preserved internally as legacy and excluded from every figure on this page.',
    scopeImmutable:
      'Only immutable published picks enter the record — picks frozen before kickoff with their selection, signal score, recorded odds and bookmaker.',
    scopePending:
      'Pending picks are not counted in settled performance, and void or cancelled picks are excluded from the relevant denominators.',
    scopeLive:
      'Live signals shown elsewhere in the product never enter this record unless they are published.',

    publishedHeading: 'Published picks',
    publishedBody:
      'Every pick BetGlitch froze before kickoff, whatever happened next. A published pick keeps its selection, signal score, recorded odds and bookmaker exactly as they were at publication — it is never edited or withdrawn.',
    publishedStates:
      'A pick stays pending until the match finishes. Pending is not a result: it is counted nowhere in the verified record below. Once the match ends it settles as won or lost, or is marked void or cancelled and excluded from the relevant totals.',
    publishedEmpty:
      'No published pick has settled yet, so nothing is listed here. Published picks appear as soon as one does — win or lose.',
    publishedCount: 'Published picks on record',
    publishedLoading: 'Loading published picks…',
    publishedError:
      'Published picks could not be loaded. Nothing is wrong with the record itself — this is a display problem and no claim has changed. Reload in a moment.',
    publishedRetry: 'Try again',
    publishedProofLink: 'View proof',
    publishedOddsLabel: 'Recorded odds',
    publishedAtLabel: 'Published',
    publishedNotCounted: 'Not counted in verified performance until it settles',
    publishedCountedIn: 'Counted in the verified record',

    verifiedHeading: 'Verified record',
    verifiedBody:
      'These aggregate figures are calculated from settled published picks only. Pending picks, void and cancelled picks, and every legacy prediction from before the pricing-integrity cutoff are excluded — so this record is smaller than the number of predictions BetGlitch has made, and that is deliberate.',

    noAccuracy: 'No verified results yet',
    accuracyAppears: 'Accuracy appears once the first published pick settles.',
    noSettled: 'No settled picks yet',
    winsLosses: 'Wins and losses are both published here as they settle.',
    roiRestarted:
      'Our verified pricing record restarted and fills in as matches settle.',
    noBreakdown:
      'No breakdown yet. Once published picks settle, accuracy is split by predicted outcome here.',

    legacyHeading: 'Prediction log — not the verified record',
    legacyAll: (n: number) => `All ${n} rows below were`,
    legacySome: (n: number, total: number) => `${n} of the ${total} rows below were`,
    legacyBody:
      'recorded before the pricing-integrity cutoff. They are kept public because BetGlitch does not delete history, but their prices could not be verified against the exact market and bookmaker, so they are excluded from the accuracy and ROI figures above and from every public performance claim.',
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
      'Verify every result here, then join the free list for updates on published picks as the verified record develops.',
    capturePanelEyebrow: 'Proof-led funnel',
    capturePanelSeePublished: 'See the published picks',
    capturePanelSeeVerified: 'See the verified record',
    captureTitle: 'Get the weekly summary',
    captureBody:
      'A free weekly email covering the picks BetGlitch published and how they settled.',
    captureDefaultTitle: 'Follow the published picks by email',
    captureDefaultBody:
      'A free weekly email covering which picks BetGlitch published and how they settled — wins and losses both.',
  },

  footer: {
    tagline:
      'Football market signals across European competitions. Selected picks are frozen before kickoff with their recorded odds and stay public after settlement — win or lose.',
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
        'Semnalele live nu fac parte din istoricul verificat decât dacă BetGlitch le publică drept revendicare imutabilă.',
    },
    publishedPick: {
      label: 'Pontaj publicat',
      plural: 'Pontaje publicate',
      short: 'Publicat',
      definition:
        'Un pontaj înghețat de BetGlitch înainte de start — selecția, scorul de semnal, cota înregistrată, casa de pariuri și marcajele de timp nu se mai pot schimba.',
      frozenFields: [
        'Selecție', 'Scor semnal', 'Cota înregistrată', 'Casa de pariuri',
        'Marcaje de timp', 'Proveniență',
      ],
    },
    verifiedRecord: {
      label: 'Istoric verificat',
      definition:
        'Fiecare pontaj publicat care s-a încheiat, păstrat public împreună cu rezultatul — câștigat sau pierdut.',
      scope:
        'Contează doar pontajele publicate încheiate. Cele în așteptare sunt afișate separat, iar cele anulate sunt excluse din totaluri.',
    },
  },

  workflow: [
    {
      id: 'explore',
      title: 'Explorează',
      body: 'Vezi semnalele live curente pentru meciurile viitoare din competițiile europene.',
    },
    {
      id: 'publish',
      title: 'Publică',
      body: 'Pontajele selectate sunt înghețate înainte de start, cu cota înregistrată și casa de pariuri.',
    },
    {
      id: 'verify',
      title: 'Verifică',
      body: 'Rezultatele se adaugă după fluierul final. Și câștigurile, și pierderile rămân publice.',
    },
  ],

  hero: {
    eyebrow: 'BETA PUBLIC GRATUIT',
    headline: 'Semnale de piață pentru fotbal, verificabile.',
    supporting:
      'Explorează semnale derivate din datele furnizorului, vezi ce pontaje îngheață BetGlitch înainte de start și verifică fiecare rezultat încheiat — câștigat sau pierdut.',
    primaryCta: 'Explorează semnalele live',
    secondaryCta: 'Vezi istoricul verificat',
    zeroState: 'Construim istoricul verificat de la zero',
  },

  home: {
    signalsHeading: 'Semnale live acum',
    browseAll: 'Vezi toate meciurile',
    howHeading: 'Cum funcționează BetGlitch',
    differenceHeading: 'Nu orice semnal devine pontaj publicat',
    differenceBody:
      'BetGlitch afișează mult mai multe semnale live decât publică. Doar pontajele publicate contează pentru istoricul verificat, iar diferența se vede peste tot în produs.',
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
        body: 'Pontajele publicate păstrează o pagină publică permanentă cu ce a fost înghețat, când și la ce casă de pariuri. Cotele nu sunt rescrise, iar pierderile nu sunt șterse.',
      },
      {
        title: 'Decizi singur',
        body: 'BetGlitch nu îți dimensionează miza și nu îți spune să pariezi. Îți arată ce a clasat, la ce preț și ce a urmat.',
      },
    ],
    coverageHeading: 'Acoperire',
    coverageBody: 'competiții europene, cu până la 14 zile în avans. Inclusiv:',
    viewAllLeagues: 'Vezi toate competițiile',
    settledLabel: 'Pontaje publicate încheiate',
    openRecord: 'Deschide istoricul verificat',
    finalHeading: 'Gratuit cât timp construim istoricul verificat',
    finalBody:
      'Nu ai ce cumpăra și nu este necesară o metodă de plată. Creează un cont pentru a folosi instrumentele de bankroll și pentru a urmări pontajele publicate până se încheie.',
    createAccount: 'Creează un cont gratuit',
    signalsError: 'Semnalele live nu au putut fi încărcate',
    signalsErrorBody:
      'Cererea către serviciul de semnale a eșuat. Contul tău nu are nicio problemă și niciun pontaj publicat nu este afectat.',
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
        title: 'Înțelege dovada publicată',
        body: 'Vezi cum diferă o revendicare publicată imutabilă de o predicție live care se schimbă.',
        cta: 'Vezi pontajele publicate',
        href: '/track-record#published-picks',
      },
      {
        id: 'record',
        title: 'Urmărește istoricul verificat',
        body: 'Analizează pontajele publicate încheiate pe măsură ce eșantionul crește.',
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
      'Istoricul verificat este în construcție. Pontajele publicate și încheiate vor apărea aici, inclusiv câștigurile și pierderile.',
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
      'Istoricul public verificat începe de la un prag curat de integritate a prețului. Predicțiile făcute înainte de acesta sunt păstrate intern ca moștenire și excluse din fiecare cifră de pe această pagină.',
    scopeImmutable:
      'Doar pontajele publicate imutabile intră în istoric — pontaje înghețate înainte de start, cu selecția, scorul de semnal, cota înregistrată și casa de pariuri.',
    scopePending:
      'Pontajele în așteptare nu sunt numărate în performanța încheiată, iar cele anulate sau nule sunt excluse din numitorii relevanți.',
    scopeLive:
      'Semnalele live afișate în altă parte a produsului nu intră niciodată în acest istoric decât dacă sunt publicate.',

    publishedHeading: 'Pontaje publicate',
    publishedBody:
      'Fiecare pontaj pe care BetGlitch l-a înghețat înainte de start, indiferent ce a urmat. Un pontaj publicat își păstrează selecția, scorul de semnal, cota înregistrată și casa de pariuri exact cum erau la publicare — nu este niciodată editat sau retras.',
    publishedStates:
      'Un pontaj rămâne în așteptare până se termină meciul. Așteptarea nu este un rezultat: nu este numărată nicăieri în istoricul verificat de mai jos. După încheierea meciului se soluționează ca fiind câștigat sau pierdut, ori este marcat nul sau anulat și exclus din totalurile relevante.',
    publishedEmpty:
      'Niciun pontaj publicat nu s-a încheiat încă, așa că aici nu este listat nimic. Pontajele publicate apar imediat ce se încheie unul — câștig sau pierdere.',
    publishedCount: 'Pontaje publicate înregistrate',
    publishedLoading: 'Se încarcă pontajele publicate…',
    publishedError:
      'Pontajele publicate nu au putut fi încărcate. Istoricul în sine este intact — este o problemă de afișare și niciun pontaj nu s-a modificat. Reîncarcă peste puțin timp.',
    publishedRetry: 'Încearcă din nou',
    publishedProofLink: 'Vezi dovada',
    publishedOddsLabel: 'Cotă înregistrată',
    publishedAtLabel: 'Publicat',
    publishedNotCounted:
      'Nu este numărat în performanța verificată până la încheiere',
    publishedCountedIn: 'Numărat în istoricul verificat',

    verifiedHeading: 'Istoric verificat',
    verifiedBody:
      'Aceste cifre agregate sunt calculate exclusiv din pontaje publicate încheiate. Pontajele în așteptare, cele nule și anulate, precum și fiecare predicție de dinaintea pragului de integritate a prețului sunt excluse — deci acest istoric este mai mic decât numărul de predicții făcute de BetGlitch, iar asta este intenționat.',

    noAccuracy: 'Niciun rezultat verificat încă',
    accuracyAppears:
      'Acuratețea apare după ce se încheie primul pontaj publicat.',
    noSettled: 'Niciun pontaj încheiat încă',
    winsLosses:
      'Atât câștigurile cât și pierderile sunt publicate aici pe măsură ce se încheie.',
    roiRestarted:
      'Istoricul nostru verificat de prețuri a fost restartat și se completează pe măsură ce meciurile se încheie.',
    noBreakdown:
      'Nicio defalcare încă. După ce pontajele publicate se încheie, acuratețea este împărțită aici pe rezultat prezis.',

    legacyHeading: 'Jurnal de predicții — nu este istoricul verificat',
    legacyAll: (n: number) => `Toate cele ${n} rânduri de mai jos au fost`,
    legacySome: (n: number, total: number) => `${n} din cele ${total} rânduri de mai jos au fost`,
    legacyBody:
      'înregistrate înainte de pragul de integritate a prețului. Sunt păstrate public pentru că BetGlitch nu șterge istoricul, dar prețurile lor nu au putut fi verificate față de piața și casa de pariuri exacte, așa că sunt excluse din cifrele de acuratețe și ROI de mai sus și din orice afirmație publică de performanță.',
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
      'Verifică fiecare rezultat aici, apoi înscrie-te gratuit pentru actualizări despre pontajele publicate pe măsură ce istoricul verificat se dezvoltă.',
    capturePanelEyebrow: 'Canal bazat pe dovezi',
    capturePanelSeePublished: 'Vezi pontajele publicate',
    capturePanelSeeVerified: 'Vezi istoricul verificat',
    captureTitle: 'Primește rezumatul săptămânal',
    captureBody:
      'Un email săptămânal gratuit despre pontajele publicate de BetGlitch și cum s-au încheiat.',
    captureDefaultTitle: 'Urmărește pontajele publicate pe email',
    captureDefaultBody:
      'Un email săptămânal gratuit despre ce pontaje a publicat BetGlitch și cum s-au încheiat — și câștiguri, și pierderi.',
  },

  footer: {
    tagline:
      'Semnale de piață pentru fotbal din competițiile europene. Pontajele selectate sunt înghețate înainte de start cu cotele înregistrate și rămân publice după încheiere — câștig sau pierdere.',
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
