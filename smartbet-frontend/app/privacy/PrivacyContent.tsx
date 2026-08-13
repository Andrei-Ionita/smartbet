'use client'

import { Cookie, Database, Lock, Mail, Shield, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { PUBLIC_LEGAL_IDENTITY_COMPLETE, publicLegalIdentity } from '@/app/lib/publicLegalIdentity'


export default function PrivacyContent() {
  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-12 text-center">
        <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary-100">
          <Lock className="h-8 w-8 text-primary-600" />
        </div>
        <h1 className="mb-4 text-3xl font-bold text-gray-900">Privacy Policy</h1>
        <p className="text-gray-600">Last updated: August 11, 2026</p>
      </div>

      <div className="space-y-8 rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <section>
          <h2 className="mb-4 text-xl font-bold text-gray-900">1. Who controls your data</h2>
          {PUBLIC_LEGAL_IDENTITY_COMPLETE ? (
            <p className="text-gray-600">
              <strong>{publicLegalIdentity.operatorName}</strong>, of {publicLegalIdentity.operatorAddress},{' '}
              {publicLegalIdentity.operatorCountry}, operates BetGlitch and determines why and how personal
              data submitted through the Service is processed. Privacy requests can be sent to{' '}
              <a href="mailto:privacy@betglitch.com" className="text-primary-600 hover:underline">privacy@betglitch.com</a>.
            </p>
          ) : (
            <div className="space-y-3 text-gray-600">
              <p>
                BetGlitch determines why and how personal data submitted through the Service is processed.
                The current free, accountless beta does not accept payments, registrations or newsletter
                sign-ups.
              </p>
              <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                The operator&apos;s legal name, service address and jurisdiction are not yet published. They must
                be completed before BetGlitch moves beyond a limited public beta or enables accounts, email
                collection or payments.
              </p>
              <p>
                Privacy requests can be sent to{' '}
                <a href="mailto:privacy@betglitch.com" className="text-primary-600 hover:underline">privacy@betglitch.com</a>.
              </p>
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900">
            <Database className="h-5 w-5 text-primary-600" /> 2. Data we process
          </h2>
          <ul className="ml-4 list-disc space-y-2 text-gray-600">
            <li><strong>Current public beta:</strong> registration, login, bankroll and newsletter collection are disabled. You can use the public research product without submitting an email address or creating an account.</li>
            <li><strong>Dormant records from earlier testing:</strong> previously submitted account details, password hashes, bankroll entries and newsletter preferences may remain until deletion is requested.</li>
            <li><strong>Security and delivery:</strong> IP address, request time, browser information and short-lived rate-limit identifiers in infrastructure logs or security controls.</li>
            <li><strong>Support:</strong> the content and contact details included in a message you send us.</li>
          </ul>
          <p className="mt-4 text-gray-600">
            Public football fixtures, prices, model observations and results are not linked to an account and are not personal data about BetGlitch users.
          </p>
        </section>

        <section>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900">
            <Shield className="h-5 w-5 text-primary-600" /> 3. Purpose and legal basis
          </h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-600"><tr><th className="px-3 py-2">Purpose</th><th className="px-3 py-2">Legal basis</th></tr></thead>
              <tbody className="divide-y divide-gray-100 text-gray-600">
                <tr><td className="px-3 py-3">Retain or delete dormant account and user-tool records from earlier testing</td><td className="px-3 py-3">Performance of the earlier user relationship and compliance with deletion requests</td></tr>
                <tr><td className="px-3 py-3">Prevent abuse and keep the public Service reliable</td><td className="px-3 py-3">Legitimate interests in security and service integrity</td></tr>
                <tr><td className="px-3 py-3">Retain or delete earlier newsletter preferences; no new sign-ups are collected</td><td className="px-3 py-3">Consent, withdrawable at any time</td></tr>
                <tr><td className="px-3 py-3">Respond to rights requests and lawful demands</td><td className="px-3 py-3">Legal obligation and legitimate interests</td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-xl font-bold text-gray-900">4. Processors and recipients</h2>
          <div className="space-y-3 text-sm text-gray-600">
            <div className="rounded-lg bg-gray-50 p-4"><strong className="text-gray-900">Railway</strong> — application hosting, PostgreSQL database, deployment and operational logs.</div>
            <div className="rounded-lg bg-gray-50 p-4"><strong className="text-gray-900">Brevo</strong> — dormant newsletter contacts and transactional email infrastructure from the earlier account beta. No public email form or password-recovery journey is currently enabled.</div>
            <div className="rounded-lg bg-gray-50 p-4"><strong className="text-gray-900">Analytics and error monitoring</strong> — no dedicated third-party analytics or error-monitoring service is currently enabled. Product events remain a local integration seam unless a provider is explicitly added and this policy is updated.</div>
          </div>
          <p className="mt-4 text-gray-600">
            We do not sell personal data. Football-data providers receive server-to-server fixture requests; BetGlitch does not send them your account identity, bankroll or selections.
          </p>
        </section>

        <section>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900">
            <Cookie className="h-5 w-5 text-primary-600" /> 5. Browser storage
          </h2>
          <p className="text-gray-600">
            BetGlitch currently uses browser local storage for age acknowledgement and language.
            Accountless mode removes stale authentication, account and bankroll state left by an earlier
            beta from the browser. These items remain until you clear site data or the product removes
            them. No advertising cookie network is currently installed.
          </p>
        </section>

        <section>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900">
            <Trash2 className="h-5 w-5 text-primary-600" /> 6. Retention and deletion
          </h2>
          <ul className="ml-4 list-disc space-y-2 text-gray-600">
            <li>Dormant account and bankroll records from earlier testing remain until deletion is requested at <a href="mailto:privacy@betglitch.com" className="text-primary-600 hover:underline">privacy@betglitch.com</a>. Self-service profile access is unavailable during the accountless beta.</li>
            <li>An earlier newsletter address remains until you unsubscribe or request deletion. No new newsletter addresses are collected in the current public journey.</li>
            <li>Password-reset rate-limit identifiers are hashed and expire after 15 minutes. Reset tokens are not stored as standalone database records and are configured to expire after one hour.</li>
            <li>Railway operational logs are retained according to the service plan: 7 days on Hobby/Trial, 30 days on Pro and up to 90 days on Enterprise.</li>
            <li>Non-personal, append-only football evidence may be retained indefinitely to preserve the integrity of the public methodology and results.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-4 text-xl font-bold text-gray-900">7. Your rights</h2>
          <p className="text-gray-600">
            Depending on applicable law, you may request access, correction, deletion, restriction,
            portability or objection, and may withdraw consent for email at any time. You may also complain
            to your competent data-protection authority. We may need to verify identity before fulfilling a request.
          </p>
        </section>

        <section>
          <h2 className="mb-4 text-xl font-bold text-gray-900">8. Security and international processing</h2>
          <p className="text-gray-600">
            Any dormant passwords are stored as one-way hashes, transport is protected with HTTPS, and access to production
            services is restricted. Railway and its authorized subprocessors may process data outside your country;
            contractual transfer safeguards apply where required. No internet service can guarantee absolute security.
          </p>
        </section>

        <section>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-gray-900">
            <Mail className="h-5 w-5 text-primary-600" /> 9. Contact
          </h2>
          <p className="text-gray-600">
            Privacy and rights requests:{' '}
            <a href="mailto:privacy@betglitch.com" className="text-primary-600 hover:underline">privacy@betglitch.com</a>.
            General support:{' '}
            <a href="mailto:support@betglitch.com" className="text-primary-600 hover:underline">support@betglitch.com</a>.
          </p>
        </section>
      </div>

      <div className="py-8 text-center">
        <Link href="/" className="font-medium text-primary-600 hover:text-primary-700">Return to Home</Link>
      </div>
    </div>
  )
}
