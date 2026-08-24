'use client'

import Link from 'next/link'
import { Cookie, Database, Lock, Mail, Shield, Trash2 } from 'lucide-react'

import { useLanguage } from '@/app/contexts/LanguageContext'
import { PUBLIC_LEGAL_IDENTITY_COMPLETE, publicLegalIdentity } from '@/app/lib/publicLegalIdentity'

const COPY = {
  en: {
    title: 'Privacy Policy', updated: 'Last updated: August 24, 2026', home: 'Return to Home',
    controllerTitle: '1. Who controls your data',
    controller: (name: string, address: string, country: string) => `${name}, of ${address}, ${country}, operates BetGlitch and determines why and how personal data submitted through the Service is processed.`,
    controllerBeta: 'BetGlitch determines why and how submitted personal data is processed. The current free, accountless beta does not accept payments, registrations or newsletter sign-ups.',
    identityPending: 'Commercial operator, service-address and jurisdiction fields are not yet published. They will be completed before accounts, email collection or payments are enabled. Privacy requests can be sent to the address below during the free beta.',
    requests: 'Privacy and rights requests:',
    dataTitle: '2. Data we process',
    data: ['Current beta: public research can be used without an account, payment or submitted email address.', 'Product measurement: coarse page routes, actions such as searches or shares, whether a search returned results and a broad page-dwell range. Search text, fixture choices, stake data, account identifiers and email addresses are not included.', 'Dormant earlier-test records: account details, password hashes, bankroll entries and newsletter preferences may remain until deletion is requested.', 'Security and delivery: IP address, request time, browser information and short-lived rate-limit identifiers may enter infrastructure logs.', 'Support: the content and contact details in a message you send us.'],
    nonPersonal: 'Public football fixtures, prices, model observations and results are not linked to a user account and are not personal data about BetGlitch visitors.',
    basisTitle: '3. Purpose and legal basis', purpose: 'Purpose', basis: 'Legal basis',
    purposes: [['Understand whether public pages and research tools are useful', 'Legitimate interests in improving the free Service, with data minimisation and Do Not Track respected'], ['Retain or delete dormant user-tool records from earlier testing', 'Earlier user relationship and compliance with deletion requests'], ['Prevent abuse and keep the public Service reliable', 'Legitimate interests in security and service integrity'], ['Retain or delete earlier newsletter preferences; no new sign-ups are collected', 'Consent, withdrawable at any time'], ['Respond to rights requests and lawful demands', 'Legal obligation and legitimate interests']],
    processorsTitle: '4. Processors and recipients',
    processors: [['Railway', 'Application hosting, PostgreSQL database, deployment and operational logs.'], ['Brevo', 'Dormant newsletter contacts and email infrastructure from the earlier beta. No public email or password-recovery journey is enabled.'], ['Analytics and error monitoring', 'No dedicated third-party analytics or error-monitoring service is currently enabled.']],
    noSale: 'We do not sell personal data. Football-data providers receive server-to-server fixture requests without your account identity, bankroll or selections.',
    storageTitle: '5. Browser storage', storage: 'BetGlitch uses local storage for age acknowledgement and language. A random measurement identifier exists only in session storage, is replaced when the browser session ends and is stored by BetGlitch only as a one-way server-side hash. Measurement is disabled when the browser sends Do Not Track. Accountless mode removes stale authentication, account and bankroll state from the earlier beta. No advertising cookie network is installed.',
    retentionTitle: '6. Retention and deletion',
    retention: ['Pseudonymous product-event records are retained only while needed to evaluate and improve the public beta; the browser-side identifier ends with the session.', 'Dormant account and bankroll records remain until deletion is requested.', 'Earlier newsletter addresses remain until unsubscribe or deletion; no new newsletter addresses are collected.', 'Password-reset rate-limit identifiers are hashed and expire after 15 minutes; reset links expire after one hour.', 'Operational logs are retained according to the active Railway service plan.', 'Non-personal append-only football evidence may be retained indefinitely to preserve public methodology integrity.'],
    rightsTitle: '7. Your rights', rights: 'Depending on applicable law, you may request access, correction, deletion, restriction, portability or objection, and withdraw email consent. You may complain to the competent data-protection authority. Identity verification may be required.',
    securityTitle: '8. Security and international processing', security: 'Dormant passwords are stored as one-way hashes, transport uses HTTPS and production access is restricted. Railway and authorized subprocessors may process data outside your country under required safeguards. No internet service can guarantee absolute security.',
    contactTitle: '9. Contact', general: 'General support:',
  },
  ro: {
    title: 'Politica de confidențialitate', updated: 'Ultima actualizare: 24 august 2026', home: 'Înapoi la pagina principală',
    controllerTitle: '1. Cine controlează datele tale',
    controller: (name: string, address: string, country: string) => `${name}, cu sediul la ${address}, ${country}, operează BetGlitch și stabilește de ce și cum sunt prelucrate datele personale transmise prin Serviciu.`,
    controllerBeta: 'BetGlitch stabilește de ce și cum sunt prelucrate datele personale transmise. Versiunea beta actuală, gratuită și fără conturi, nu acceptă plăți, înregistrări sau abonări la newsletter.',
    identityPending: 'Datele comerciale ale operatorului, adresa și jurisdicția nu sunt încă publicate. Acestea vor fi completate înainte de activarea conturilor, colectării adreselor de e-mail sau plăților. În versiunea beta gratuită, solicitările privind confidențialitatea pot fi trimise la adresa de mai jos.',
    requests: 'Solicitări privind confidențialitatea și drepturile tale:',
    dataTitle: '2. Datele pe care le prelucrăm',
    data: ['Versiunea beta actuală: cercetarea publică poate fi utilizată fără cont, plată sau furnizarea unei adrese de e-mail.', 'Măsurarea produsului: rute generale ale paginilor, acțiuni precum căutarea sau distribuirea, dacă o căutare a returnat rezultate și un interval larg al timpului petrecut pe pagină. Textul căutării, meciurile alese, datele despre miză, identificatorii de cont și adresele de e-mail nu sunt incluse.', 'Înregistrări inactive din testele anterioare: detalii de cont, hashuri de parole, înregistrări de buget și preferințe de newsletter pot rămâne până la solicitarea ștergerii.', 'Securitate și livrare: adresa IP, ora solicitării, informații despre browser și identificatori temporari de limitare a traficului pot apărea în jurnalele infrastructurii.', 'Asistență: conținutul și datele de contact incluse într-un mesaj trimis de tine.'],
    nonPersonal: 'Meciurile publice, cotele, observațiile modelului și rezultatele nu sunt asociate unui cont și nu reprezintă date personale despre vizitatorii BetGlitch.',
    basisTitle: '3. Scop și temei juridic', purpose: 'Scop', basis: 'Temei juridic',
    purposes: [['Înțelegerea utilității paginilor publice și a instrumentelor de cercetare', 'Interese legitime pentru îmbunătățirea Serviciului gratuit, cu minimizarea datelor și respectarea Do Not Track'], ['Păstrarea sau ștergerea înregistrărilor inactive din testele anterioare', 'Relația anterioară cu utilizatorul și respectarea solicitărilor de ștergere'], ['Prevenirea abuzurilor și menținerea fiabilității Serviciului', 'Interese legitime privind securitatea și integritatea serviciului'], ['Păstrarea sau ștergerea preferințelor vechi de newsletter; nu se colectează abonări noi', 'Consimțământ, care poate fi retras oricând'], ['Răspunsul la solicitări privind drepturile și la cereri legale', 'Obligație legală și interese legitime']],
    processorsTitle: '4. Persoane împuternicite și destinatari',
    processors: [['Railway', 'Găzduirea aplicației, baza de date PostgreSQL, implementări și jurnale operaționale.'], ['Brevo', 'Contacte inactive de newsletter și infrastructură de e-mail din etapa beta anterioară. Nu este activat niciun formular public de e-mail sau flux de recuperare a parolei.'], ['Analiză și monitorizarea erorilor', 'Nu este activat momentan niciun serviciu extern dedicat de analiză sau monitorizare a erorilor.']],
    noSale: 'Nu vindem date personale. Furnizorii de date fotbalistice primesc solicitări server-la-server fără identitatea contului, bugetul sau selecțiile tale.',
    storageTitle: '5. Stocarea în browser', storage: 'BetGlitch folosește stocarea locală pentru confirmarea vârstei și alegerea limbii. Un identificator aleatoriu de măsurare există doar în stocarea sesiunii, este înlocuit la încheierea sesiunii browserului și este păstrat de BetGlitch doar ca hash unidirecțional pe server. Măsurarea este dezactivată când browserul transmite Do Not Track. Modul fără cont elimină datele vechi de autentificare, cont și buget din etapa beta anterioară. Nu este instalată nicio rețea de cookie-uri publicitare.',
    retentionTitle: '6. Păstrare și ștergere',
    retention: ['Înregistrările pseudonime despre utilizarea produsului sunt păstrate doar cât este necesar pentru evaluarea și îmbunătățirea beta publică; identificatorul din browser se încheie odată cu sesiunea.', 'Înregistrările inactive de cont și buget rămân până la solicitarea ștergerii.', 'Adresele vechi de newsletter rămân până la dezabonare sau ștergere; nu sunt colectate adrese noi.', 'Identificatorii de limitare pentru resetarea parolei sunt stocați ca hash și expiră după 15 minute; linkurile expiră după o oră.', 'Jurnalele operaționale sunt păstrate conform planului Railway activ.', 'Dovezile fotbalistice nepersonale și append-only pot fi păstrate nelimitat pentru integritatea metodologiei publice.'],
    rightsTitle: '7. Drepturile tale', rights: 'În funcție de legea aplicabilă, poți solicita accesul, corectarea, ștergerea, restricționarea, portabilitatea sau opoziția și poți retrage consimțământul pentru e-mail. Poți depune o plângere la autoritatea competentă pentru protecția datelor. Poate fi necesară verificarea identității.',
    securityTitle: '8. Securitate și prelucrare internațională', security: 'Parolele inactive sunt stocate ca hashuri unidirecționale, transportul folosește HTTPS, iar accesul la producție este restricționat. Railway și subcontractanții autorizați pot prelucra date în afara țării tale, cu garanțiile necesare. Niciun serviciu online nu poate garanta securitate absolută.',
    contactTitle: '9. Contact', general: 'Asistență generală:',
  },
} as const

function Bullets({ items }: { items: readonly string[] }) { return <ul className="ml-4 list-disc space-y-2 text-gray-600">{items.map(item => <li key={item}>{item}</li>)}</ul> }

export default function PrivacyContent() {
  const { language } = useLanguage()
  const c = COPY[language === 'ro' ? 'ro' : 'en']
  return <div className="mx-auto max-w-4xl">
    <div className="mb-12 text-center"><div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-100"><Lock className="h-8 w-8 text-primary-600" /></div><h1 className="mb-4 text-3xl font-bold text-gray-900">{c.title}</h1><p className="text-gray-600">{c.updated}</p></div>
    <div className="space-y-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.controllerTitle}</h2><p className="text-gray-600">{PUBLIC_LEGAL_IDENTITY_COMPLETE ? c.controller(publicLegalIdentity.operatorName, publicLegalIdentity.operatorAddress, publicLegalIdentity.operatorCountry) : c.controllerBeta}</p>{!PUBLIC_LEGAL_IDENTITY_COMPLETE && <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{c.identityPending}</p>}<p className="mt-3 text-gray-600">{c.requests} <a href="mailto:privacy@betglitch.com" className="text-primary-600 hover:underline">privacy@betglitch.com</a></p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Database className="h-5 w-5 text-primary-600" />{c.dataTitle}</h2><Bullets items={c.data} /><p className="mt-4 text-gray-600">{c.nonPersonal}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Shield className="h-5 w-5 text-primary-600" />{c.basisTitle}</h2><div className="overflow-x-auto"><table className="min-w-full divide-y divide-gray-200 text-left text-sm"><thead className="bg-gray-50 text-gray-600"><tr><th className="px-3 py-2">{c.purpose}</th><th className="px-3 py-2">{c.basis}</th></tr></thead><tbody className="divide-y divide-gray-100 text-gray-600">{c.purposes.map(([purpose, basis]) => <tr key={purpose}><td className="px-3 py-3">{purpose}</td><td className="px-3 py-3">{basis}</td></tr>)}</tbody></table></div></section>
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.processorsTitle}</h2><div className="space-y-3 text-sm text-gray-600">{c.processors.map(([name, body]) => <div key={name} className="rounded-lg bg-gray-50 p-4"><strong className="text-gray-900">{name}</strong> — {body}</div>)}</div><p className="mt-4 text-gray-600">{c.noSale}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Cookie className="h-5 w-5 text-primary-600" />{c.storageTitle}</h2><p className="text-gray-600">{c.storage}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Trash2 className="h-5 w-5 text-primary-600" />{c.retentionTitle}</h2><Bullets items={c.retention} /></section>
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.rightsTitle}</h2><p className="text-gray-600">{c.rights}</p></section>
      <section><h2 className="mb-4 text-xl font-bold text-gray-900">{c.securityTitle}</h2><p className="text-gray-600">{c.security}</p></section>
      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Mail className="h-5 w-5 text-primary-600" />{c.contactTitle}</h2><p className="text-gray-600">{c.requests} <a href="mailto:privacy@betglitch.com" className="text-primary-600 hover:underline">privacy@betglitch.com</a>. {c.general} <a href="mailto:support@betglitch.com" className="text-primary-600 hover:underline">support@betglitch.com</a>.</p></section>
    </div>
    <div className="py-8 text-center"><Link href="/" className="font-medium text-primary-600 hover:text-primary-700">{c.home}</Link></div>
  </div>
}
