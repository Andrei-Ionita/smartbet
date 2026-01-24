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
    default: 'OddsMind - AI-Powered Football Predictions',
    template: '%s | OddsMind'
  },
  description: 'Monitor and explore model predictions across top football leagues with AI-powered insights and betting recommendations.',
  keywords: ['football predictions', 'AI betting', 'sports analytics', 'soccer stats', 'betting tips'],
  authors: [{ name: 'OddsMind Team' }],
  creator: 'OddsMind',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://oddsmind.io',
    title: 'OddsMind - AI-Powered Football Predictions',
    description: 'Get data-driven insights and betting recommendations with confidence scores and expected value analysis.',
    siteName: 'OddsMind',
    images: [
      {
        url: '/images/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'SmartBet AI Predictions',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'OddsMind - AI-Powered Football Predictions',
    description: 'AI-powered football predictions and betting insights.',
    images: ['/images/og-image.jpg'],
    creator: '@oddsmind_ai',
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
    icon: '/images/logo-final-v4.png',
    apple: '/images/logo-final-v4.png',
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