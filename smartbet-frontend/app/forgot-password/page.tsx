import type { Metadata } from 'next'

import ForgotPasswordForm from './ForgotPasswordForm'


export const metadata: Metadata = {
  title: 'Reset password | BetGlitch',
  robots: { index: false, follow: false },
}

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-[70vh] bg-gradient-to-br from-slate-50 to-blue-50 px-4 py-12">
      <ForgotPasswordForm />
    </div>
  )
}
