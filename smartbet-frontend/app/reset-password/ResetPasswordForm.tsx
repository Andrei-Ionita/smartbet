'use client'

import { useState } from 'react'
import Link from 'next/link'
import { KeyRound } from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'


export default function ResetPasswordForm({ uid, token }: { uid: string; token: string }) {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [complete, setComplete] = useState(false)
  const [loading, setLoading] = useState(false)
  const linkComplete = Boolean(uid && token)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    if (password !== confirmation) {
      setError(ro ? 'Parolele nu coincid.' : 'Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${api}/api/auth/password-reset/confirm/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, token, password }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Password reset failed.')
      setComplete(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password reset failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700">
        <KeyRound className="h-5 w-5" />
      </div>
      <h1 className="mt-4 text-2xl font-bold text-slate-950">
        {ro ? 'Alege o parolă nouă' : 'Choose a new password'}
      </h1>

      {!linkComplete ? (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {ro ? 'Linkul de resetare este incomplet.' : 'This reset link is incomplete.'}
        </div>
      ) : complete ? (
        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          {ro ? 'Parola a fost actualizată.' : 'Your password has been updated.'}
        </div>
      ) : (
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm font-semibold text-slate-700" htmlFor="new-password">
            {ro ? 'Parolă nouă' : 'New password'}
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="min-h-[46px] w-full rounded-xl border border-slate-300 px-3 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
          <label className="block text-sm font-semibold text-slate-700" htmlFor="confirm-new-password">
            {ro ? 'Confirmă parola' : 'Confirm new password'}
          </label>
          <input
            id="confirm-new-password"
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            className="min-h-[46px] w-full rounded-xl border border-slate-300 px-3 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          />
          {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="min-h-[48px] w-full rounded-xl bg-blue-600 px-4 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? (ro ? 'Se actualizează…' : 'Updating…') : (ro ? 'Actualizează parola' : 'Update password')}
          </button>
        </form>
      )}

      <Link href="/login" className="mt-6 inline-flex min-h-[44px] items-center text-sm font-semibold text-blue-700 hover:underline">
        {ro ? 'Mergi la autentificare' : 'Go to sign in'}
      </Link>
    </div>
  )
}
