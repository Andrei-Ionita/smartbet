'use client'

import Link from 'next/link'
import { PAYMENTS_ENABLED } from '@/app/lib/commercialMode'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { useState, useEffect, useRef } from 'react'
import { Trophy, Search, Activity, Wallet, LogIn, LogOut, User, LayoutDashboard, Menu, X, Globe, Tag, Zap, ScrollText, Gauge } from 'lucide-react'
import { useAuth } from '../app/contexts/AuthContext'
import { useLanguage } from '../app/contexts/LanguageContext'
import { ProBadge } from '../app/components/ProGate'

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const pathname = usePathname()
  const { user, logout, isAuthenticated, isPro } = useAuth()
  const { t, language, setLanguage } = useLanguage()

  // Ordered by what a new visitor needs: what is this → what can I look at →
  // why should I trust it → my own tools. The verified record was previously
  // reachable only from the homepage, despite being the trust surface the whole
  // product rests on.
  const navItems = [
    { href: '/', label: t('nav.home'), icon: Trophy },
    ...(isAuthenticated ? [{ href: '/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard }] : []),
    { href: '/explore', label: t('nav.explore'), icon: Search },
    { href: '/track-record', label: t('nav.trackRecord'), icon: ScrollText },
    { href: '/calibration', label: t('nav.calibration'), icon: Gauge },
    { href: '/bankroll', label: t('nav.bankroll'), icon: Wallet },
    { href: '/monitoring', label: t('nav.monitoring'), icon: Activity },
    // Hidden while BetGlitch is a free public beta. One flag controls every
    // commercial surface — see app/lib/commercialMode.ts.
    ...(PAYMENTS_ENABLED
      ? [{ href: '/pricing', label: t('nav.pricing'), icon: Tag }]
      : []),
  ]


  // Close mobile menu when route changes
  useEffect(() => {
    setIsMenuOpen(false)
  }, [pathname])

  // Escape closes the menu and returns focus to the toggle. Keyboard users had
  // no way to dismiss it without tabbing through every link first.
  useEffect(() => {
    if (!isMenuOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsMenuOpen(false)
        menuButtonRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [isMenuOpen])

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen)

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="flex items-center space-x-2">
            <div className="relative h-10 w-10">
              <Image
                src="/images/logo-final-v6.png"
                alt="BetGlitch Logo"
                fill
                className="object-contain"
              />
            </div>
            <span className="text-xl font-bold text-gray-900">BetGlitch</span>
          </Link>

          {/* Desktop Navigation.
              Breakpoint is xl, not md. The full bar — logo, five links, the
              EN/RO toggle and two auth buttons — needs ~1215px in Romanian,
              where "Autentificare"/"Înregistrare" are far longer than
              "Login"/"Sign Up". Switching at md meant the bar overflowed the
              page at 768, 1024 and 1120, so iPad portrait and small laptops
              scrolled sideways. Below xl the (accessible) hamburger is used. */}
          <div className="hidden xl:flex space-x-4">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </div>


          {/* Auth Section & Language Switcher */}
          <div className="hidden xl:flex items-center gap-3">
            {/* Language Switcher */}
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 mr-2">
              <button
                onClick={() => setLanguage('en')}
                aria-pressed={language === 'en'}
                className={`min-h-[44px] min-w-[44px] px-2 text-xs font-bold rounded ${language === 'en' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage('ro')}
                aria-pressed={language === 'ro'}
                className={`min-h-[44px] min-w-[44px] px-2 text-xs font-bold rounded ${language === 'ro' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
              >
                RO
              </button>
            </div>

            {isAuthenticated && user ? (
              <>
                {PAYMENTS_ENABLED && !isPro && (
                  <Link
                    href="/pricing"
                    className="flex items-center gap-1.5 px-3 py-2 text-sm font-semibold text-white bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 rounded-lg transition-all shadow-sm"
                  >
                    <Zap className="h-4 w-4" />
                    <span>{t('nav.upgradeToPro')}</span>
                  </Link>
                )}
                <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
                  <User className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">{user.username}</span>
                  {PAYMENTS_ENABLED && isPro && <ProBadge />}
                </div>
                <button
                  onClick={logout}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>{t('nav.logout')}</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <LogIn className="h-4 w-4" />
                  <span>{t('nav.login')}</span>
                </Link>
                <Link
                  href="/register"
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                  <span>{t('nav.signup')}</span>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="xl:hidden flex items-center gap-4">
            {/* Show user avatar on mobile if logged in, but not the whole auth block */}
            {isAuthenticated && user && (
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold">
                {user.username.charAt(0).toUpperCase()}
              </div>
            )}
            <button
              ref={menuButtonRef}
              onClick={toggleMenu}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
              aria-expanded={isMenuOpen}
              aria-controls="mobile-menu"
              aria-label={isMenuOpen ? 'Close main menu' : 'Open main menu'}
            >
              {/* Was a rotated LogOut icon standing in for an X — which read as
                  "sign out" on the one control every mobile user has to press. */}
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isMenuOpen && (
        <div id="mobile-menu" className="xl:hidden border-t border-gray-100 bg-white">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-3 px-3 py-3 rounded-md text-base font-medium ${isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </Link>
              )
            })}
            {/* Mobile Language Switcher */}
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-sm font-medium text-gray-500">Language / Limbă</span>
              <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setLanguage('en')}
                  aria-pressed={language === 'en'}
                  className={`min-h-[44px] px-4 text-xs font-bold rounded ${language === 'en' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  English
                </button>
                <button
                  onClick={() => setLanguage('ro')}
                  aria-pressed={language === 'ro'}
                  className={`min-h-[44px] px-4 text-xs font-bold rounded ${language === 'ro' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  Română
                </button>
              </div>
            </div>

            <hr className="my-2 border-gray-200" />

            {isAuthenticated ? (
              <>
                {PAYMENTS_ENABLED && !isPro && (
                  <Link
                    href="/pricing"
                    className="flex items-center space-x-3 px-3 py-3 mb-2 rounded-md text-base font-semibold text-white bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700"
                  >
                    <Zap className="h-5 w-5" />
                    <span>{t('nav.upgradeToPro')}</span>
                  </Link>
                )}
                {isPro && (
                  <div className="flex items-center space-x-3 px-3 py-2 mb-2">
                    <ProBadge />
                    <span className="text-sm text-gray-600">{user?.username}</span>
                  </div>
                )}
                <button
                  onClick={logout}
                  className="w-full flex items-center space-x-3 px-3 py-3 rounded-md text-base font-medium text-red-600 hover:bg-red-50 text-left"
                >
                  <LogOut className="h-5 w-5" />
                  <span>{t('nav.logout')}</span>
                </button>
              </>
            ) : (
              <div className="flex flex-col gap-2 p-2">
                <Link
                  href="/login"
                  className="min-h-[44px] flex justify-center items-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  {t('nav.login')}
                </Link>
                <Link
                  href="/register"
                  className="min-h-[44px] flex justify-center items-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  {t('nav.signup')}
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
