import { NextRequest, NextResponse } from 'next/server'
import { ACCOUNT_FEATURES_ENABLED } from '@/app/lib/commercialMode'

const DORMANT_ACCOUNT_PATHS = [
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/profile',
  '/dashboard',
  '/bankroll',
  '/pricing',
]

/** Canonicalize the domain and keep dormant personal-product pages private. */
export function middleware(request: NextRequest) {
  const host = request.headers.get('host')?.split(':')[0].toLowerCase()
  if (host === 'betglitch.com') {
    const canonical = request.nextUrl.clone()
    canonical.protocol = 'https:'
    canonical.host = 'www.betglitch.com'
    return NextResponse.redirect(canonical, 308)
  }

  const isDormantAccountPath = DORMANT_ACCOUNT_PATHS.some(
    (path) =>
      request.nextUrl.pathname === path ||
      request.nextUrl.pathname.startsWith(`${path}/`),
  )
  if (!ACCOUNT_FEATURES_ENABLED && isDormantAccountPath) {
    return NextResponse.redirect(new URL('/explore', request.url), 307)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|images/|favicon.ico).*)'],
}
