import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navigation from '@/components/Navigation'
import { AuthProvider } from './contexts/AuthContext'
import Footer from '@/components/Footer'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'SmartBet - AI-Powered Football Predictions',
    template: '%s | SmartBet'
  },
  description: 'Monitor and explore model predictions across top football leagues with AI-powered insights and betting recommendations.',
  keywords: ['football predictions', 'AI betting', 'sports analytics', 'soccer stats', 'betting tips'],
  authors: [{ name: 'SmartBet Team' }],
  creator: 'SmartBet',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://smartbet.ai',
    title: 'SmartBet - AI-Powered Football Predictions',
    description: 'Get data-driven insights and betting recommendations with confidence scores and expected value analysis.',
    siteName: 'SmartBet',
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
    title: 'SmartBet - AI-Powered Football Predictions',
    description: 'AI-powered football predictions and betting insights.',
    images: ['/images/og-image.jpg'],
    creator: '@smartbet_ai',
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
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <div className="min-h-screen bg-gray-50 flex flex-col">
            <Navigation />
            <main className="container mx-auto px-4 py-8 flex-grow">
              {children}
            </main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  )
}