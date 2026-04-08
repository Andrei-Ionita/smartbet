import type { Metadata } from 'next'
import './globals.css'
import Navigation from '@/components/Navigation'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import Footer from '@/components/Footer'
import AgeGateModal from './components/AgeGateModal'

export const metadata: Metadata = {
  metadataBase: new URL('https://betglitch.com'),
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

const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "BetGlitch",
  "url": "https://betglitch.com",
  "logo": "https://betglitch.com/images/logo-final-v6.png",
  "description": "AI-powered football predictions and betting insights for 27 European leagues.",
  "sameAs": [],
}

const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "BetGlitch",
  "url": "https://betglitch.com",
  "description": "AI-powered football predictions across 27 European leagues",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://betglitch.com/explore?q={search_term_string}",
    "query-input": "required name=search_term_string",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
        />
      </head>
      <body className="font-sans">
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