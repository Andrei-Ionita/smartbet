'use client'

import Link from 'next/link'
import { AlertTriangle, Ban, Globe, Scale, Shield, TrendingDown } from 'lucide-react'

import { useLanguage } from '@/app/contexts/LanguageContext'

const COPY = {
  en: {
    title: 'Disclaimer', subtitle: 'Read this notice carefully before using BetGlitch', home: 'Return to Home',
    operatorTitle: 'BetGlitch is not a betting operator', operatorBody: 'BetGlitch does not accept bets, wagers, deposits or gambling payments and is not licensed as a bookmaker, betting exchange or gambling operator.',
    analytics: 'It is a data-analysis service that ranks third-party football probability data into informational signals. No output guarantees profit, and you may lose all money wagered.',
    adviceTitle: 'No Financial or Betting Advice', advice: 'Signals, analysis and information do not constitute financial advice, betting advice or a recommendation to place a wager. A signal is not a tip.',
    ownRisk: 'Any betting decision is made at your own risk. You should:', ownRiskItems: ['Research independently before betting', 'Use only licensed and regulated operators', 'Never wager more than you can afford to lose', 'Seek professional help when needed'],
    limitsTitle: 'Accuracy Limitations', limits: 'BetGlitch does not build, train or own the underlying predictive model. Signals rank probability data supplied by a third-party football-data provider. We do not guarantee:',
    limitItems: ['The accuracy of an individual signal', 'Complete or timely data', 'That past results predict future results', 'Profit from following signals', 'That a signal identifies a mispriced market or bookmaker disadvantage'],
    scoreTitle: 'The signal score is not a probability.', score: 'It is a relative ranking within one market. A score of 66 does not mean a 66% chance. We do not claim calibrated fair odds, proven expected value or a predictive edge, and we do not size stakes.',
    unpredictable: 'Sports outcomes are inherently uncertain. Even the highest-ranked signal can be wrong.',
    riskTitle: 'Risk Warning', riskLead: 'GAMBLING INVOLVES SUBSTANTIAL RISK OF LOSS',
    risks: ['You may lose some or all money wagered', 'Gambling can be addictive', 'Never chase losses or use essential money', 'Past results do not guarantee future outcomes', 'Bookmaker prices include a margin'],
    ageTitle: 'Age Restriction', age: 'This Service is for adults only. You must be at least 18, or the higher legal age in your jurisdiction, and legally permitted to access gambling-related information.',
    jurisdictionTitle: 'Jurisdiction Notice', jurisdiction: 'Gambling laws vary. You are responsible for confirming that accessing gambling-related information and using any gambling service is legal where you are. Do not use BetGlitch where this content is prohibited.',
    liabilityTitle: 'Limitation of Liability', liability: 'To the maximum extent permitted by law, BetGlitch and its affiliates are not liable for:',
    liabilities: ['Financial loss caused by betting decisions', 'Errors, inaccuracies or omissions', 'Service interruption', 'Damage resulting from reliance on the information', 'Third-party actions, products or services'],
    linksTitle: 'Third-Party Links', links: 'Links to third-party sites do not imply endorsement. BetGlitch is not responsible for their content, privacy practices or terms.',
    changesTitle: 'Changes to This Disclaimer', changes: 'We may update this notice. Changes take effect when posted; continued use constitutes acceptance.',
    help: 'If you or someone you know has a gambling problem, confidential help is available.', resources: 'Responsible Gambling Resources',
  },
  ro: {
    title: 'Declinarea răspunderii', subtitle: 'Citește cu atenție această informare înainte de a utiliza BetGlitch', home: 'Înapoi la pagina principală',
    operatorTitle: 'BetGlitch nu este operator de pariuri', operatorBody: 'BetGlitch nu acceptă pariuri, mize, depozite sau plăți pentru jocuri de noroc și nu este licențiat ca operator de pariuri, bursă de pariuri sau operator de jocuri de noroc.',
    analytics: 'Este un serviciu de analiză care clasifică date externe privind probabilitățile fotbalistice și le prezintă ca semnale informative. Niciun rezultat nu garantează profitul și poți pierde toți banii pariați.',
    adviceTitle: 'Fără recomandări financiare sau de pariere', advice: 'Semnalele, analizele și informațiile nu constituie consultanță financiară, recomandări de pariere sau îndemnuri de a plasa o miză. Un semnal nu este un pont.',
    ownRisk: 'Orice decizie de pariere este luată pe propriul risc. Ar trebui să:', ownRiskItems: ['Analizezi independent înainte de a paria', 'Folosești doar operatori licențiați și reglementați', 'Nu mizezi niciodată mai mult decât îți permiți să pierzi', 'Soliciți ajutor specializat atunci când este necesar'],
    limitsTitle: 'Limitele acurateței', limits: 'BetGlitch nu construiește, nu antrenează și nu deține modelul predictiv de bază. Semnalele clasifică date de probabilitate furnizate de un furnizor extern. Nu garantăm:',
    limitItems: ['Acuratețea unui semnal individual', 'Caracterul complet sau actual al datelor', 'Că rezultatele anterioare prezic rezultate viitoare', 'Profitul prin urmarea semnalelor', 'Că un semnal identifică o piață cotată greșit sau un dezavantaj al casei de pariuri'],
    scoreTitle: 'Scorul semnalului nu este o probabilitate.', score: 'Este o clasificare relativă în cadrul unei piețe. Un scor de 66 nu înseamnă o șansă de 66%. Nu pretindem cote corecte calibrate, valoare așteptată demonstrată sau avantaj predictiv și nu stabilim mize.',
    unpredictable: 'Rezultatele sportive sunt inerent incerte. Chiar și semnalul cel mai bine clasificat poate fi greșit.',
    riskTitle: 'Avertisment de risc', riskLead: 'JOCURILE DE NOROC IMPLICĂ UN RISC SUBSTANȚIAL DE PIERDERE',
    risks: ['Poți pierde o parte sau toți banii pariați', 'Jocurile de noroc pot crea dependență', 'Nu urmări pierderile și nu folosi bani necesari traiului', 'Rezultatele anterioare nu garantează rezultate viitoare', 'Cotele caselor de pariuri includ o marjă'],
    ageTitle: 'Restricție de vârstă', age: 'Serviciul este destinat exclusiv adulților. Trebuie să ai cel puțin 18 ani sau vârsta legală mai mare din jurisdicția ta și să poți accesa legal informații despre jocuri de noroc.',
    jurisdictionTitle: 'Informare privind jurisdicția', jurisdiction: 'Legislația privind jocurile de noroc diferă. Tu trebuie să verifici dacă accesarea informațiilor și utilizarea unui serviciu de jocuri de noroc sunt legale în locația ta. Nu utiliza BetGlitch acolo unde acest conținut este interzis.',
    liabilityTitle: 'Limitarea răspunderii', liability: 'În limita maximă permisă de lege, BetGlitch și entitățile afiliate nu răspund pentru:',
    liabilities: ['Pierderi financiare cauzate de decizii de pariere', 'Erori, inexactități sau omisiuni', 'Întreruperea Serviciului', 'Daune rezultate din utilizarea informațiilor', 'Acțiuni, produse sau servicii ale terților'],
    linksTitle: 'Linkuri externe', links: 'Linkurile către site-uri externe nu reprezintă o recomandare. BetGlitch nu răspunde pentru conținutul, practicile de confidențialitate sau termenii acestora.',
    changesTitle: 'Modificarea acestei informări', changes: 'Putem actualiza această informare. Modificările se aplică de la publicare; continuarea utilizării reprezintă acceptarea lor.',
    help: 'Dacă tu sau cineva apropiat are probleme cu jocurile de noroc, există ajutor confidențial.', resources: 'Resurse pentru joc responsabil',
  },
} as const

function Bullets({ items, tone = 'gray' }: { items: readonly string[]; tone?: 'gray' | 'red' }) { return <ul className={`ml-4 list-disc space-y-2 ${tone === 'red' ? 'text-red-700' : 'text-gray-600'}`}>{items.map(item => <li key={item}>{item}</li>)}</ul> }

export default function DisclaimerContent() {
  const { language } = useLanguage(); const c = COPY[language === 'ro' ? 'ro' : 'en']
  return <div className="mx-auto max-w-4xl">
    <div className="mb-12 text-center"><div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-amber-100"><AlertTriangle className="h-8 w-8 text-amber-600" /></div><h1 className="mb-4 text-3xl font-bold text-gray-900">{c.title}</h1><p className="text-gray-600">{c.subtitle}</p></div>
    <div className="mb-8 rounded-xl border-2 border-red-200 bg-red-50 p-6"><div className="flex gap-4"><Ban className="h-8 w-8 shrink-0 text-red-600" /><div><h2 className="mb-3 text-xl font-bold text-red-800">{c.operatorTitle}</h2><p className="text-red-700">{c.operatorBody}</p><p className="mt-3 text-red-700">{c.analytics}</p></div></div></div>
    <div className="space-y-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><TrendingDown className="h-5 w-5 text-amber-500" />{c.adviceTitle}</h2><p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">{c.advice}</p><p className="mb-4 text-gray-600">{c.ownRisk}</p><Bullets items={c.ownRiskItems} /></section>
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.limitsTitle}</h2><p className="mb-4 text-gray-600">{c.limits}</p><Bullets items={c.limitItems} /><p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><strong>{c.scoreTitle}</strong> {c.score}</p><p className="mt-4 text-gray-600">{c.unpredictable}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><AlertTriangle className="h-5 w-5 text-red-500" />{c.riskTitle}</h2><div className="rounded-lg border border-red-200 bg-red-50 p-5"><p className="mb-3 font-bold text-red-800">{c.riskLead}</p><Bullets items={c.risks} tone="red" /></div></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Shield className="h-5 w-5 text-primary-600" />{c.ageTitle}</h2><p className="text-gray-600">{c.age}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Globe className="h-5 w-5 text-primary-600" />{c.jurisdictionTitle}</h2><p className="text-gray-600">{c.jurisdiction}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Scale className="h-5 w-5 text-primary-600" />{c.liabilityTitle}</h2><p className="mb-4 text-gray-600">{c.liability}</p><Bullets items={c.liabilities} /></section>
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.linksTitle}</h2><p className="text-gray-600">{c.links}</p></section>
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.changesTitle}</h2><p className="text-gray-600">{c.changes}</p></section>
    </div>
    <div className="mt-8 rounded-xl border border-primary-200 bg-primary-50 p-6 text-center"><p className="mb-4 text-primary-900">{c.help}</p><Link href="/responsible-gambling" className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white hover:bg-primary-700"><Shield className="h-5 w-5" />{c.resources}</Link></div>
    <div className="py-8 text-center"><Link href="/" className="font-medium text-primary-600 hover:text-primary-700">{c.home}</Link></div>
  </div>
}
