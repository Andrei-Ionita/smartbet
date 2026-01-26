import { MetadataRoute } from 'next'

// Base URL from environment or hardcoded fallback
const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://oddsmind.io'

export default function sitemap(): MetadataRoute.Sitemap {
    // Static routes
    const routes = [
        '',
        '/explore',
        '/track-record',
        '/about',
        '/bankroll',
        '/monitoring',
    ].map((route) => ({
        url: `${BASE_URL}${route}`,
        lastModified: new Date(),
        changeFrequency: 'daily' as const,
        priority: route === '' ? 1 : 0.8,
    }))

    // Dynamic routes (predictions)
    // In a real automated setup, we would fetch the list of *active* prediction slugs here.
    // Since we don't have a database of pre-generated slugs easily accessible without
    // querying the entire DB, we might want to just list the static ones for now
    // and rely on Google discovering the dynamic ones via internal links.
    // 
    // However, if we wanted to be exhaustive, we would fetch "upcoming match IDs"
    // from an API and generate slugs.

    return [...routes]
}
