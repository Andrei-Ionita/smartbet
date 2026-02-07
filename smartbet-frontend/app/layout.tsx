import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navigation from '@/components/Navigation'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import Footer from '@/components/Footer'
import AgeGateModal from './components/AgeGateModal'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'BetGlitch - AI-Powered Football Predictions',
    template: '%s | BetGlitch'
  },
  description: 'Find the edge. Monitor model predictions across top football leagues with AI-powered insights and betting recommendations.',
  keywords: ['football predictions', 'AI betting', 'sports analytics', 'soccer stats', 'betting tips', 'value betting'],
  authors: [{ name: 'BetGlitch Team' }],
  creator: 'BetGlitch',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://betglitch.com',
    title: 'BetGlitch - AI-Powered Football Predictions',
    description: 'The system has a glitch. We found it. Data-driven insights and betting recommendations.',
    siteName: 'BetGlitch',
    images: [
      {
        url: '/images/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'BetGlitch AI Predictions',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'BetGlitch - AI-Powered Football Predictions',
    description: 'AI-powered football predictions and betting insights.',
    images: ['/images/og-image.jpg'],
    creator: '@BetGlitch',
  },
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: '/images/logo-final-v6.png',
    apple: '/images/logo-final-v6.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AgeGateModal />
        <AuthProvider>
          <LanguageProvider>
            <div className="min-h-screen bg-gray-50 flex flex-col">
              <Navigation />
              <main className="container mx-auto px-4 py-8 flex-grow">
                {children}
              </main>
              <Footer />
            </div>
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  )
}