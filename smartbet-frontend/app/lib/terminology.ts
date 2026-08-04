/**
 * THE single source of public product vocabulary.
 *
 * BetGlitch has exactly three public concepts. Every page must describe them
 * with these words — previously each page invented its own ("recommendations",
 * "smart picks", "top quality bets", "predictions"), which made a mutable model
 * output and an immutable published claim look like the same object.
 *
 *   1. LIVE MODEL SIGNAL  — current model output for an upcoming fixture.
 *                           MUTABLE. Not part of public performance.
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
      label: 'Live model signal',
      plural: 'Live model signals',
      short: 'Live signal',
      definition:
        'The model’s current output for an upcoming fixture. It can change before kickoff.',
      mutability:
        'Live signals update when models rerun, odds move, new data arrives or a newer snapshot is generated.',
      notInRecord:
        'Live signals are not part of the verified record unless BetGlitch publishes them as an immutable claim.',
    },
    publishedPick: {
      label: 'Published pick',
      plural: 'Published picks',
      short: 'Published',
      definition:
        'A pick BetGlitch froze before kickoff — selection, model score, recorded odds, bookmaker and timestamps can no longer change.',
      frozenFields: [
        'Selection', 'Model score', 'Recorded odds', 'Bookmaker', 'Timestamps',
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
      body: 'Browse current model signals for upcoming fixtures across European leagues.',
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
    headline: 'Football model signals with a record you can verify.',
    supporting:
      'Explore AI-generated football predictions across European leagues. Selected picks are frozen before kickoff and remain public after settlement—win or lose.',
    primaryCta: 'Explore live signals',
    secondaryCta: 'View verified record',
    zeroState: 'Building the verified record from zero',
  },

  home: {
    signalsHeading: 'Live model signals right now',
    browseAll: 'Browse all fixtures',
    howHeading: 'How BetGlitch works',
    differenceHeading: 'Not every signal becomes a published pick',
    differenceBody:
      'BetGlitch shows far more model output than it publishes. Only published picks count towards the verified record, and you can tell the two apart everywhere in the product.',
    notInPerformance: 'Not part of public performance.',
    frozenIntro: 'Frozen before kickoff. These can never change:',
    benefitsHeading: 'What you can do here',
    benefits: [
      {
        title: 'Read the model, not a tip',
        body: 'Every fixture shows its model score, the market signal behind it and the recorded price — not just a selection.',
      },
      {
        title: 'Check the receipts',
        body: 'Published picks keep a permanent public page showing what was frozen, when, and at which bookmaker.',
      },
      {
        title: 'Size your own stakes',
        body: 'The bankroll tools apply Kelly staking to a bankroll you set. BetGlitch never places a bet.',
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
      'Explore live model signals, use the bankroll tools and follow BetGlitch’s verified public record as it develops.',
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
        body: 'Browse upcoming fixtures and current model outputs.',
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
      'The verified record is being built. Published picks will appear here after settlement, including both wins and losses.',
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
      'Only immutable published picks enter the record — picks frozen before kickoff with their selection, model score, recorded odds and bookmaker.',
    scopePending:
      'Pending picks are not counted in settled performance, and void or cancelled picks are excluded from the relevant denominators.',
    scopeLive:
      'Live model signals shown elsewhere in the product never enter this record unless they are published.',

    publishedHeading: 'Published picks',
    publishedBody:
      'Every pick BetGlitch froze before kickoff, whatever happened next. A published pick keeps its selection, model score, recorded odds and bookmaker exactly as they were at publication — it is never edited or withdrawn.',
    publishedStates:
      'A pick stays pending until the match finishes. Pending is not a result: it is counted nowhere in the verified record below. Once the match ends it settles as won or lost, or is marked void or cancelled and excluded from the relevant totals.',
    publishedEmpty:
      'No published pick has settled yet, so nothing is listed here. Published picks appear as soon as one does — win or lose.',
    publishedCount: 'Settled published picks listed below',

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
  },

  footer: {
    tagline:
      'Football model signals across European leagues. Selected picks are frozen before kickoff with their recorded odds and stay public after settlement — win or lose.',
    emailSupport: 'Email BetGlitch support',
    platform: 'Platform',
    explore: 'Explore predictions',
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
    noticeOperatorRest: ' We do not accept bets, wagers, or deposits of any kind. Our predictions are provided for ',
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
    'BetGlitch publishes model analysis for information only. It does not place bets and no outcome is guaranteed. 18+. Please gamble responsibly.',

  modelScoreNote:
    'A model score ranks BetGlitch’s relative confidence. It is not a calibrated probability and should not be read as a percentage chance.',
}

const RO: typeof EN = {
  terms: {
    liveSignal: {
      label: 'Semnal live al modelului',
      plural: 'Semnale live ale modelului',
      short: 'Semnal live',
      definition:
        'Rezultatul curent al modelului pentru un meci viitor. Se poate schimba până la start.',
      mutability:
        'Semnalele live se actualizează când modelele rulează din nou, când cotele se mișcă, când apar date noi sau când se generează un snapshot mai recent.',
      notInRecord:
        'Semnalele live nu fac parte din istoricul verificat decât dacă BetGlitch le publică drept revendicare imutabilă.',
    },
    publishedPick: {
      label: 'Pontaj publicat',
      plural: 'Pontaje publicate',
      short: 'Publicat',
      definition:
        'Un pontaj înghețat de BetGlitch înainte de start — selecția, scorul modelului, cota înregistrată, casa de pariuri și marcajele de timp nu se mai pot schimba.',
      frozenFields: [
        'Selecție', 'Scorul modelului', 'Cota înregistrată', 'Casa de pariuri',
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
      body: 'Vezi semnalele curente ale modelului pentru meciurile viitoare din ligile europene.',
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
    headline: 'Semnale de model pentru fotbal, cu un istoric pe care îl poți verifica.',
    supporting:
      'Explorează predicții de fotbal generate de AI din ligile europene. Pontajele selectate sunt înghețate înainte de start și rămân publice după încheiere—câștigate sau pierdute.',
    primaryCta: 'Explorează semnalele live',
    secondaryCta: 'Vezi istoricul verificat',
    zeroState: 'Construim istoricul verificat de la zero',
  },

  home: {
    signalsHeading: 'Semnale live ale modelului acum',
    browseAll: 'Vezi toate meciurile',
    howHeading: 'Cum funcționează BetGlitch',
    differenceHeading: 'Nu orice semnal devine pontaj publicat',
    differenceBody:
      'BetGlitch afișează mult mai multe rezultate ale modelului decât publică. Doar pontajele publicate contează pentru istoricul verificat, iar diferența se vede peste tot în produs.',
    notInPerformance: 'Nu face parte din performanța publică.',
    frozenIntro: 'Înghețate înainte de start. Acestea nu se mai pot schimba:',
    benefitsHeading: 'Ce poți face aici',
    benefits: [
      {
        title: 'Citește modelul, nu un pont',
        body: 'Fiecare meci arată scorul modelului, semnalul de piață din spate și prețul înregistrat — nu doar o selecție.',
      },
      {
        title: 'Verifică dovezile',
        body: 'Pontajele publicate păstrează o pagină publică permanentă cu ce a fost înghețat, când și la ce casă de pariuri.',
      },
      {
        title: 'Îți dimensionezi singur miza',
        body: 'Instrumentele de bankroll aplică staking Kelly pe un bankroll setat de tine. BetGlitch nu plasează niciodată un pariu.',
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
      'Explorează semnalele live ale modelului, folosește instrumentele de bankroll și urmărește istoricul public verificat BetGlitch pe măsură ce se dezvoltă.',
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
        body: 'Vezi meciurile viitoare și rezultatele curente ale modelului.',
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
      'Istoricul verificat este în construcție. Pontajele publicate apar aici după încheiere, atât câștigurile cât și pierderile.',
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
      'Doar pontajele publicate imutabile intră în istoric — pontaje înghețate înainte de start, cu selecția, scorul modelului, cota înregistrată și casa de pariuri.',
    scopePending:
      'Pontajele în așteptare nu sunt numărate în performanța încheiată, iar cele anulate sau nule sunt excluse din numitorii relevanți.',
    scopeLive:
      'Semnalele live ale modelului afișate în altă parte a produsului nu intră niciodată în acest istoric decât dacă sunt publicate.',

    publishedHeading: 'Pontaje publicate',
    publishedBody:
      'Fiecare pontaj pe care BetGlitch l-a înghețat înainte de start, indiferent ce a urmat. Un pontaj publicat își păstrează selecția, scorul modelului, cota înregistrată și casa de pariuri exact cum erau la publicare — nu este niciodată editat sau retras.',
    publishedStates:
      'Un pontaj rămâne în așteptare până se termină meciul. Așteptarea nu este un rezultat: nu este numărată nicăieri în istoricul verificat de mai jos. După încheierea meciului se soluționează ca fiind câștigat sau pierdut, ori este marcat nul sau anulat și exclus din totalurile relevante.',
    publishedEmpty:
      'Niciun pontaj publicat nu s-a încheiat încă, așa că aici nu este listat nimic. Pontajele publicate apar imediat ce se încheie unul — câștig sau pierdere.',
    publishedCount: 'Pontaje publicate încheiate, listate mai jos',

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
  },

  footer: {
    tagline:
      'Semnale de model pentru fotbal din campionatele europene. Pontajele selectate sunt înghețate înainte de start cu cotele înregistrate și rămân publice după încheiere — câștig sau pierdere.',
    emailSupport: 'Scrie echipei de suport BetGlitch',
    platform: 'Platformă',
    explore: 'Explorează predicțiile',
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
      ' Nu acceptăm pariuri, mize sau depuneri de niciun fel. Predicțiile noastre sunt oferite ',
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
    'BetGlitch publică analize de model doar cu scop informativ. Nu plasează pariuri și niciun rezultat nu este garantat. 18+. Joacă responsabil.',

  modelScoreNote:
    'Scorul modelului exprimă încrederea relativă a BetGlitch. Nu este o probabilitate calibrată și nu trebuie citit ca șansă procentuală.',
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
  'singura platformă',
  'matematic corect',
  'mii de utilizatori',
] as const
