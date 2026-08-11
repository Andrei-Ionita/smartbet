'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Mail } from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'


export default function ForgotPasswordForm() {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${api}/api/auth/password-reset/request/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Password recovery failed.')
      setSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password recovery failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
        <Mail className="h-5 w-5" />
      </div>
      <h1 className="mt-4 text-2xl font-bold text-slate-950">
        {ro ? 'Resetează parola' : 'Reset your password'}
      </h1>
      <p className="mt-2 text-sm leading-relaxed text-slate-600">
        {ro
          ? 'Introdu adresa contului. Dacă există un cont activ, vei primi un link securizat.'
          : 'Enter the account email. If an active account exists, we will send a secure reset link.'}
      </p>

      {sent ? (
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-relaxed text-emerald-900">
          {ro
            ? 'Verifică inboxul. Același răspuns este afișat indiferent dacă adresa aparține unui cont.'
            : 'Check your inbox. The same response is shown whether or not the address belongs to an account.'}
        </div>
      ) : (
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm font-semibold text-slate-700" htmlFor="reset-email">
            {ro ? 'Adresă de email' : 'Email address'}
          </label>
          <input
            id="reset-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="min-h-[46px] w-full rounded-xl border border-slate-300 px-3 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
          {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="min-h-[48px] w-full rounded-xl bg-blue-600 px-4 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? (ro ? 'Se trimite…' : 'Sending…') : (ro ? 'Trimite linkul' : 'Send reset link')}
          </button>
        </form>
      )}

      <Link href="/login" className="mt-6 inline-flex min-h-[44px] items-center text-sm font-semibold text-blue-700 hover:underline">
        {ro ? 'Înapoi la autentificare' : 'Back to sign in'}
      </Link>
    </div>
  )
}
