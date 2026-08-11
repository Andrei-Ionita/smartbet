import { NextRequest, NextResponse } from 'next/server'
import { ACCOUNT_FEATURES_ENABLED } from '@/app/lib/commercialMode'

/** Keep dormant personal-product pages out of the accountless public journey. */
export function middleware(request: NextRequest) {
  if (ACCOUNT_FEATURES_ENABLED) return NextResponse.next()

  return NextResponse.redirect(new URL('/explore', request.url), 307)
}

export const config = {
  matcher: [
    '/login/:path*',
    '/register/:path*',
    '/forgot-password/:path*',
    '/reset-password/:path*',
    '/profile/:path*',
    '/dashboard/:path*',
    '/bankroll/:path*',
    '/pricing/:path*',
  ],
}
