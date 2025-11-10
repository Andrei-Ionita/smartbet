'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Trophy, Search, Activity, Wallet, LogIn, LogOut, User } from 'lucide-react'
import { useAuth } from '../app/contexts/AuthContext'

export default function Navigation() {
  const pathname = usePathname()
  const { user, logout, isAuthenticated } = useAuth()

  const navItems = [
    { href: '/', label: 'Home', icon: Trophy },
    { href: '/explore', label: 'Explore', icon: Search },
    { href: '/monitoring', label: 'Monitoring', icon: Activity },
    { href: '/bankroll', label: 'Bankroll', icon: Wallet },
  ]

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="flex items-center space-x-2">
            <Trophy className="h-8 w-8 text-primary-600" />
            <span className="text-xl font-bold text-gray-900">SmartBet</span>
          </Link>
          
          <div className="hidden md:flex space-x-8">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              )
            })}
          </div>
          
          {/* Auth Section */}
          <div className="flex items-center gap-3">
            {isAuthenticated && user ? (
              <>
                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
                  <User className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">{user.username}</span>
                </div>
                <button
                  onClick={logout}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden md:inline">Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <LogIn className="h-4 w-4" />
                  <span>Login</span>
                </Link>
                <Link
                  href="/register"
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                  <span>Sign Up</span>
                </Link>
              </>
            )}
          </div>
          
          {/* Mobile menu button */}
          <div className="md:hidden">
            <button className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
} 