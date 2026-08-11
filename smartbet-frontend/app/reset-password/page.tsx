import type { Metadata } from 'next'

import ResetPasswordForm from './ResetPasswordForm'


export const metadata: Metadata = {
  title: 'Choose a new password | BetGlitch',
  robots: { index: false, follow: false },
}

export default function ResetPasswordPage({
  searchParams,
}: {
  searchParams: { uid?: string; token?: string }
}) {
  return (
    <div className="min-h-[70vh] bg-gradient-to-br from-slate-50 to-blue-50 px-4 py-12">
      <ResetPasswordForm uid={searchParams.uid ?? ''} token={searchParams.token ?? ''} />
    </div>
  )
}
