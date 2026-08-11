import { MetadataRoute } from 'next'

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://betglitch.com'

export default function robots(): MetadataRoute.Robots {
    return {
        rules: [
            {
                userAgent: '*',
                allow: '/',
                disallow: [
                    '/private/', '/dashboard/', '/profile/', '/login/',
                    '/register/', '/forgot-password/', '/reset-password/',
                    '/bankroll/', '/pricing/',
                ],
            },
        ],
        sitemap: `${BASE_URL}/sitemap.xml`,
    }
}
