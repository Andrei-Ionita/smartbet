'use client'

import Link from 'next/link'
import { AlertTriangle, Ban, FileText, Scale, Shield } from 'lucide-react'

import { useLanguage } from '@/app/contexts/LanguageContext'
import { PUBLIC_LEGAL_IDENTITY_COMPLETE, publicLegalIdentity } from '@/app/lib/publicLegalIdentity'

const COPY = {
  en: {
    title: 'Terms of Service', updated: 'Last updated: August 2026', home: 'Return to Home',
    identity: (name: string, address: string, country: string) => `BetGlitch is operated by ${name}, of ${address}, ${country}.`,
    identityPending: 'BetGlitch is currently a free, accountless public beta. Commercial operator and service-address fields will be completed before accounts, email collection or payments are enabled.',
    agreementTitle: '1. Agreement to Terms', agreement: 'By accessing or using BetGlitch (“the Service”), you agree to these Terms. If you do not agree, do not use the Service. We may update these Terms; continued use after an update constitutes acceptance of the revised Terms.',
    serviceTitle: '2. Service Description', notOperator: 'BetGlitch is not a betting operator, bookmaker or gambling site. We do not accept bets, wagers, deposits or gambling payments.',
    service: 'BetGlitch ranks football probability data supplied by a third-party data provider into informational signals. The Service is a free public beta for informational and entertainment purposes only.',
    includes: ['Live signals for upcoming fixtures', 'Published Gems frozen before kickoff with recorded price provenance', 'Public results containing every eligible settled published Gem', 'Historical research evidence and educational sports-analytics content'],
    scoreTitle: 'What the signal score is not.',
    scoreBody: 'It is a relative ranking within one market, not a calibrated probability or guarantee. BetGlitch does not train or own the underlying predictive model, has not demonstrated a predictive or pricing edge, and does not provide bet/no-bet or stake instructions. No output guarantees profit. You may lose all money wagered.',
    userTitle: '3. User Responsibilities', userIntro: 'By using the Service, you confirm that:',
    user: ['You meet the applicable legal age, and are at least 18', 'You may legally access gambling-related information in your jurisdiction', 'You will comply with applicable laws', 'You understand that betting involves substantial risk and no signal guarantees an outcome', 'You will not use the Service unlawfully', 'Every betting decision remains your responsibility'],
    warrantyTitle: '4. Disclaimer of Warranties', warranty: 'THE SERVICE IS PROVIDED “AS IS” WITHOUT EXPRESS OR IMPLIED WARRANTIES. We do not guarantee:',
    warranties: ['The accuracy, completeness or reliability of any signal', 'Profit from using any signal', 'That a signal identifies a mispriced market or bookmaker disadvantage', 'Uninterrupted or error-free operation', 'That every analysis contains the latest available data'],
    warrantyTail: 'Past results do not indicate future results. Betting can cause the loss of your entire stake and is not suitable for everyone.',
    liabilityTitle: '5. Limitation of Liability', liability: 'To the fullest extent permitted by law, BetGlitch and its affiliates are not liable for:',
    liabilities: ['Financial losses resulting from betting decisions', 'Indirect, incidental, special or consequential damages', 'Loss of profits, data or other intangible loss', 'Loss caused by unauthorized access outside our reasonable control'],
    prohibitedTitle: '6. Prohibited Uses', prohibited: 'You must not:',
    prohibitedItems: ['Use the Service while under the applicable legal age', 'Access it where gambling-related content is prohibited', 'Resell or redistribute signals without permission', 'Bypass access controls, rate limits or security measures', 'Scrape or copy content using unauthorized automation', 'Interfere with the Service'],
    ipTitle: '7. Intellectual Property', ip: 'The Service’s text, graphics, logo, ranking logic and software belong to BetGlitch and are protected by applicable intellectual-property laws. Underlying football probability data is licensed from a third-party provider and is not owned by BetGlitch.',
    lawTitle: '8. Governing Law', law: (law: string, courts: string) => `These Terms are governed by ${law}. Disputes are subject to ${courts}, except where mandatory consumer law provides otherwise.`,
    lawPending: 'Governing law and competent courts will be stated with the operator’s legal identity before accounts, email collection or payments are enabled. Mandatory consumer protections are not excluded.',
    contactTitle: '9. Contact', contact: 'Questions about these Terms:',
  },
  ro: {
    title: 'Termeni și condiții', updated: 'Ultima actualizare: august 2026', home: 'Înapoi la pagina principală',
    identity: (name: string, address: string, country: string) => `BetGlitch este operat de ${name}, cu sediul la ${address}, ${country}.`,
    identityPending: 'BetGlitch este momentan o versiune beta publică, gratuită și fără conturi. Datele comerciale ale operatorului și adresa vor fi completate înainte de activarea conturilor, colectării adreselor de e-mail sau plăților.',
    agreementTitle: '1. Acceptarea termenilor', agreement: 'Prin accesarea sau utilizarea BetGlitch („Serviciul”), accepți acești Termeni. Dacă nu ești de acord, nu utiliza Serviciul. Putem actualiza Termenii; continuarea utilizării după o actualizare reprezintă acceptarea versiunii revizuite.',
    serviceTitle: '2. Descrierea serviciului', notOperator: 'BetGlitch nu este operator de pariuri, casă de pariuri sau platformă de jocuri de noroc. Nu acceptăm pariuri, mize, depozite sau plăți pentru jocuri de noroc.',
    service: 'BetGlitch ordonează date despre probabilitățile meciurilor de fotbal furnizate de un furnizor extern și le prezintă ca semnale informative. Serviciul este o versiune beta publică și gratuită, destinată exclusiv informării și divertismentului.',
    includes: ['Semnale live pentru meciurile viitoare', 'Gem-uri publicate și fixate înainte de start, cu proveniența cotei înregistrată', 'Rezultate publice care includ fiecare Gem eligibil și încheiat', 'Dovezi istorice de cercetare și conținut educațional despre analiza sportivă'],
    scoreTitle: 'Ce nu reprezintă scorul semnalului.',
    scoreBody: 'Este o clasificare relativă în cadrul unei piețe, nu o probabilitate calibrată sau o garanție. BetGlitch nu antrenează și nu deține modelul predictiv de bază, nu a demonstrat un avantaj predictiv sau de preț și nu oferă instrucțiuni de pariere sau de stabilire a mizei. Niciun rezultat nu garantează profitul. Poți pierde întreaga sumă pariată.',
    userTitle: '3. Responsabilitățile utilizatorului', userIntro: 'Prin utilizarea Serviciului confirmi că:',
    user: ['Ai vârsta legală aplicabilă și cel puțin 18 ani', 'Poți accesa legal informații despre jocuri de noroc în jurisdicția ta', 'Vei respecta legislația aplicabilă', 'Înțelegi riscul substanțial al pariurilor și faptul că niciun semnal nu garantează rezultatul', 'Nu vei utiliza Serviciul în scopuri ilegale', 'Fiecare decizie de pariere îți aparține'],
    warrantyTitle: '4. Lipsa garanțiilor', warranty: 'SERVICIUL ESTE OFERIT „CA ATARE”, FĂRĂ GARANȚII EXPRESE SAU IMPLICITE. Nu garantăm:',
    warranties: ['Acuratețea, caracterul complet sau fiabilitatea unui semnal', 'Obținerea unui profit prin utilizarea semnalelor', 'Că un semnal identifică o piață cotată greșit sau un dezavantaj al casei de pariuri', 'Funcționarea neîntreruptă sau fără erori', 'Că fiecare analiză include cele mai recente date disponibile'],
    warrantyTail: 'Rezultatele anterioare nu indică rezultate viitoare. Pariurile pot duce la pierderea întregii mize și nu sunt potrivite pentru toată lumea.',
    liabilityTitle: '5. Limitarea răspunderii', liability: 'În limita maximă permisă de lege, BetGlitch și entitățile afiliate nu răspund pentru:',
    liabilities: ['Pierderi financiare rezultate din decizii de pariere', 'Daune indirecte, incidentale, speciale sau consecutive', 'Pierderea profiturilor, datelor sau a altor beneficii necorporale', 'Pierderi cauzate de acces neautorizat în afara controlului nostru rezonabil'],
    prohibitedTitle: '6. Utilizări interzise', prohibited: 'Nu ai voie să:',
    prohibitedItems: ['Utilizezi Serviciul sub vârsta legală aplicabilă', 'Îl accesezi acolo unde conținutul despre jocuri de noroc este interzis', 'Revinzi sau redistribui semnalele fără permisiune', 'Ocolești controalele de acces, limitele de trafic sau măsurile de securitate', 'Extragi sau copiezi conținutul prin automatizări neautorizate', 'Interferezi cu funcționarea Serviciului'],
    ipTitle: '7. Proprietate intelectuală', ip: 'Textele, elementele grafice, sigla, logica de clasificare și software-ul Serviciului aparțin BetGlitch și sunt protejate de legislația aplicabilă. Datele de bază privind probabilitățile fotbalistice sunt licențiate de la un furnizor extern și nu aparțin BetGlitch.',
    lawTitle: '8. Legea aplicabilă', law: (law: string, courts: string) => `Acești Termeni sunt guvernați de ${law}. Litigiile sunt supuse competenței ${courts}, cu excepția situațiilor în care legislația obligatorie privind protecția consumatorilor prevede altfel.`,
    lawPending: 'Legea aplicabilă și instanțele competente vor fi precizate împreună cu identitatea juridică a operatorului înainte de activarea conturilor, colectării adreselor de e-mail sau plăților. Protecțiile obligatorii ale consumatorilor nu sunt excluse.',
    contactTitle: '9. Contact', contact: 'Întrebări despre acești Termeni:',
  },
} as const

function Bullets({ items }: { items: readonly string[] }) {
  return <ul className="ml-4 list-disc space-y-2 text-gray-600">{items.map(item => <li key={item}>{item}</li>)}</ul>
}

export default function TermsContent() {
  const { language } = useLanguage()
  const c = COPY[language === 'ro' ? 'ro' : 'en']
  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-12 text-center"><div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-100"><FileText className="h-8 w-8 text-primary-600" /></div><h1 className="mb-4 text-3xl font-bold text-gray-900">{c.title}</h1><p className="text-gray-600">{c.updated}</p></div>
      <div className="space-y-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Scale className="h-5 w-5 text-primary-600" />{c.agreementTitle}</h2><p className="text-gray-600">{c.agreement}</p><p className={`mt-4 rounded-lg border p-4 text-sm ${PUBLIC_LEGAL_IDENTITY_COMPLETE ? 'border-gray-200 bg-gray-50 text-gray-700' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>{PUBLIC_LEGAL_IDENTITY_COMPLETE ? c.identity(publicLegalIdentity.operatorName, publicLegalIdentity.operatorAddress, publicLegalIdentity.operatorCountry) : c.identityPending}</p></section>
        <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.serviceTitle}</h2><div className="mb-4 flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4"><AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" /><p className="text-sm font-semibold text-amber-900">{c.notOperator}</p></div><p className="mb-4 text-gray-600">{c.service}</p><Bullets items={c.includes} /><p className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700"><strong>{c.scoreTitle}</strong> {c.scoreBody}</p></section>
        <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Shield className="h-5 w-5 text-primary-600" />{c.userTitle}</h2><p className="mb-4 text-gray-600">{c.userIntro}</p><Bullets items={c.user} /></section>
        <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><AlertTriangle className="h-5 w-5 text-amber-500" />{c.warrantyTitle}</h2><p className="mb-4 text-gray-600">{c.warranty}</p><Bullets items={c.warranties} /><p className="mt-4 text-gray-600">{c.warrantyTail}</p></section>
        <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.liabilityTitle}</h2><p className="mb-4 text-gray-600">{c.liability}</p><Bullets items={c.liabilities} /></section>
        <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Ban className="h-5 w-5 text-red-500" />{c.prohibitedTitle}</h2><p className="mb-4 text-gray-600">{c.prohibited}</p><Bullets items={c.prohibitedItems} /></section>
        <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.ipTitle}</h2><p className="text-gray-600">{c.ip}</p></section>
        <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.lawTitle}</h2><p className="text-gray-600">{PUBLIC_LEGAL_IDENTITY_COMPLETE ? c.law(publicLegalIdentity.governingLaw, publicLegalIdentity.competentCourts) : c.lawPending}</p></section>
        <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.contactTitle}</h2><p className="text-gray-600">{c.contact} <a href="mailto:legal@betglitch.com" className="text-primary-600 hover:underline">legal@betglitch.com</a></p></section>
      </div>
      <div className="py-8 text-center"><Link href="/" className="font-medium text-primary-600 hover:text-primary-700">{c.home}</Link></div>
    </div>
  )
}
