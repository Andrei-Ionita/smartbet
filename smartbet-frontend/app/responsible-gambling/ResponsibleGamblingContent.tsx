'use client'

import Link from 'next/link'
import { AlertTriangle, CheckCircle, ExternalLink, Heart, HelpCircle, Shield } from 'lucide-react'

import { useLanguage } from '@/app/contexts/LanguageContext'

const COPY = {
  en: {
    title: 'Responsible Gambling', intro: 'Gambling should be entertainment, never a source of harm or a way to solve financial problems.',
    reminderTitle: 'Important Reminder', reminder: 'BetGlitch provides informational research only. It is not a bookmaker, does not accept bets, wagers or deposits, and its signal score is not a calibrated probability. No output guarantees profit. You may lose all money wagered.',
    principlesTitle: 'Key Principles', principles: ['Only wager money you can afford to lose', 'Set a budget and stop when it is reached', 'Never chase losses', 'Take regular breaks', 'Do not gamble while upset, stressed or impaired', 'Balance gambling with other activities', 'Track the time and money spent', 'Never borrow money to gamble'],
    signsTitle: 'Warning Signs of Problem Gambling', signsIntro: 'Seek help if you recognize these signs in yourself or someone close to you:', signs: ['Spending more time or money than you can afford', 'Difficulty reducing or stopping gambling', 'Arguments about gambling and money', 'Loss of interest in normal activities', 'Thinking about gambling constantly', 'Hiding or lying about gambling', 'Chasing losses or gambling to escape problems', 'Neglecting work, education or family'],
    helpTitle: 'Free and Confidential Support', helpIntro: 'These independent organizations offer information and support:', visit: 'Visit',
    resources: [
      ['Joc Responsabil România', 'Romanian-language counselling and specialist support', '0800 800 099', 'https://jocresponsabil.ro/'],
      ['GamCare', 'UK gambling-support information and helpline', '0808 8020 133', 'https://www.gamcare.org.uk/'],
      ['Gambling Therapy', 'International online support in multiple languages', 'Online support', 'https://www.gamblingtherapy.org/'],
      ['Gamblers Anonymous', 'Peer-support fellowship and local meetings', 'International', 'https://www.gamblersanonymous.org/'],
    ],
    exclusionTitle: 'Self-Exclusion and Blocking', exclusion: 'Licensed operators normally provide self-exclusion controls. Contact the operator directly and use an appropriate national exclusion scheme. BetBlocker also offers free device-level blocking.',
    final: 'Stopping is always an acceptable decision. If gambling is causing harm, seek support now.', home: 'Return to Home',
  },
  ro: {
    title: 'Joc responsabil', intro: 'Jocurile de noroc ar trebui să fie divertisment, niciodată o sursă de suferință sau o soluție pentru probleme financiare.',
    reminderTitle: 'Atenționare importantă', reminder: 'BetGlitch oferă exclusiv cercetare informativă. Nu este casă de pariuri, nu acceptă pariuri, mize sau depozite, iar scorul semnalului nu este o probabilitate calibrată. Niciun rezultat nu garantează profitul. Poți pierde toți banii pariați.',
    principlesTitle: 'Principii esențiale', principles: ['Pariază doar bani pe care îți permiți să îi pierzi', 'Stabilește un buget și oprește-te când îl atingi', 'Nu urmări niciodată pierderile', 'Ia pauze regulate', 'Nu juca atunci când ești supărat, stresat sau sub influență', 'Păstrează un echilibru cu alte activități', 'Urmărește timpul și banii cheltuiți', 'Nu împrumuta niciodată bani pentru jocuri de noroc'],
    signsTitle: 'Semne ale jocului problematic', signsIntro: 'Solicită ajutor dacă recunoști aceste semne la tine sau la cineva apropiat:', signs: ['Cheltuiești mai mult timp sau bani decât îți permiți', 'Îți este greu să reduci sau să oprești jocul', 'Apar conflicte despre jocuri și bani', 'Îți pierzi interesul pentru activitățile obișnuite', 'Te gândești permanent la jocuri de noroc', 'Ascunzi sau minți despre joc', 'Urmărești pierderile sau joci pentru a evita problemele', 'Neglijezi munca, educația sau familia'],
    helpTitle: 'Ajutor gratuit și confidențial', helpIntro: 'Aceste organizații independente oferă informații și sprijin:', visit: 'Accesează',
    resources: [
      ['Joc Responsabil România', 'Consiliere în limba română și sprijin specializat', '0800 800 099', 'https://jocresponsabil.ro/'],
      ['GamCare', 'Informații și linie de asistență din Regatul Unit', '0808 8020 133', 'https://www.gamcare.org.uk/'],
      ['Gambling Therapy', 'Sprijin online internațional în mai multe limbi', 'Sprijin online', 'https://www.gamblingtherapy.org/'],
      ['Gamblers Anonymous', 'Grupuri de sprijin între persoane cu experiențe similare', 'Internațional', 'https://www.gamblersanonymous.org/'],
    ],
    exclusionTitle: 'Autoexcludere și blocare', exclusion: 'Operatorii licențiați oferă în mod normal instrumente de autoexcludere. Contactează direct operatorul și folosește schema națională potrivită. BetBlocker oferă și blocarea gratuită a site-urilor pe dispozitive.',
    final: 'Oprirea este întotdeauna o decizie acceptabilă. Dacă jocurile de noroc îți provoacă probleme, solicită ajutor acum.', home: 'Înapoi la pagina principală',
  },
} as const

function Items({ items, tone = 'neutral' }: { items: readonly string[]; tone?: 'neutral' | 'danger' }) { return <div className="grid gap-3 md:grid-cols-2">{items.map(item => <div key={item} className={`flex items-start gap-3 rounded-lg p-3 ${tone === 'danger' ? 'bg-red-50 text-red-800' : 'bg-gray-50 text-gray-700'}`}><CheckCircle className={`mt-0.5 h-5 w-5 shrink-0 ${tone === 'danger' ? 'text-red-500' : 'text-green-600'}`} /><span className="text-sm">{item}</span></div>)}</div> }

export default function ResponsibleGamblingContent() {
  const { language } = useLanguage(); const c = COPY[language === 'ro' ? 'ro' : 'en']
  return <div className="mx-auto max-w-4xl">
    <div className="mb-12 text-center"><div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-100"><Shield className="h-8 w-8 text-primary-600" /></div><h1 className="mb-4 text-3xl font-bold text-gray-900">{c.title}</h1><p className="mx-auto max-w-2xl text-lg text-gray-600">{c.intro}</p></div>
    <section className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-6"><div className="flex gap-4"><AlertTriangle className="h-6 w-6 shrink-0 text-amber-600" /><div><h2 className="mb-2 font-bold text-amber-900">{c.reminderTitle}</h2><p className="text-amber-800">{c.reminder}</p></div></div></section>
    <section className="mb-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"><h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900"><Heart className="h-5 w-5 text-red-500" />{c.principlesTitle}</h2><Items items={c.principles} /></section>
    <section className="mb-8 rounded-xl border border-red-200 bg-red-50 p-6"><h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-red-900"><AlertTriangle className="h-5 w-5" />{c.signsTitle}</h2><p className="mb-4 text-red-800">{c.signsIntro}</p><Items items={c.signs} tone="danger" /></section>
    <section className="mb-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"><h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-gray-900"><HelpCircle className="h-5 w-5 text-primary-600" />{c.helpTitle}</h2><p className="mb-6 text-gray-600">{c.helpIntro}</p><div className="grid gap-4">{c.resources.map(([name, description, contact, url]) => <article key={name} className="rounded-lg border border-gray-200 p-4"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><div><h3 className="font-bold text-gray-900">{name}</h3><p className="mt-1 text-sm text-gray-600">{description}</p><p className="mt-2 text-sm font-semibold text-primary-700">{contact}</p></div><a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-primary-600 hover:underline">{c.visit}<ExternalLink className="h-3.5 w-3.5" /></a></div></article>)}</div></section>
    <section className="mb-8 rounded-xl bg-gray-50 p-6"><h2 className="mb-3 text-xl font-bold text-gray-900">{c.exclusionTitle}</h2><p className="text-gray-600">{c.exclusion}</p></section>
    <div className="py-8 text-center"><p className="mb-4 text-gray-600">{c.final}</p><Link href="/" className="font-medium text-primary-600 hover:text-primary-700">{c.home}</Link></div>
  </div>
}
