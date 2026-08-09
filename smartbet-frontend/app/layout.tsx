import type { Metadata, Viewport } from 'next'
import './globals.css'
import Navigation from '@/components/Navigation'
import { AuthProvider } from './contexts/AuthContext'
import { LanguageProvider } from './contexts/LanguageContext'
import Footer from '@/components/Footer'
import AgeGateModal from './components/AgeGateModal'

export const metadata: Metadata = {
  metadataBase: new URL('https://betglitch.com'),
  title: {
    default: 'BetGlitch — every signal explained, every result visible',
    template: '%s | BetGlitch'
  },
  description: 'A public football-signal lab with fixture context, verified market prices, versioned methodology and a permanent record of every eligible result — win or lose.',
  keywords: ['football signals', 'public commitments', 'verified record', 'sports analytics', 'football statistics', 'settled results'],
  authors: [{ name: 'BetGlitch Team' }],
  creator: 'BetGlitch',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://betglitch.com',
    title: 'BetGlitch — every signal explained, every result visible',
    description: 'Fixture context, verified prices and versioned public commitments. Every eligible result stays visible — win or lose.',
    siteName: 'BetGlitch',
    images: [
      {
        url: '/images/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'BetGlitch — verifiable football market signals',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'BetGlitch — every signal explained, every result visible',
    description: 'Fixture context, verified prices and versioned public commitments, settled in public after full-time.',
    images: ['/images/og-image.jpg'],
    creator: '@BetGlitch',
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
  "description": "A public football-signal lab with fixture context, verified prices, versioned methodology and a permanent result record.",
  "sameAs": [],
}

const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "BetGlitch",
  "url": "https://betglitch.com",
  "description": "Transparent football signals, public commitments and a verified result record",
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

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}
