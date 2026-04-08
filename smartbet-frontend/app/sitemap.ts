import { MetadataRoute } from 'next'
import { getAllPosts } from './blog/posts'

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://betglitch.com'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    // Static routes
    const staticRoutes = [
        '',
        '/explore',
        '/track-record',
        '/about',
        '/bankroll',
        '/monitoring',
        '/pricing',
        '/responsible-gambling',
        '/terms',
        '/privacy',
        '/disclaimer',
        '/blog',
    ].map((route) => ({
        url: `${BASE_URL}${route}`,
        lastModified: new Date(),
        changeFrequency: route === '' ? 'daily' as const : 'weekly' as const,
        priority: route === '' ? 1 : route === '/explore' ? 0.9 : 0.7,
    }))

    // Blog posts
    const posts = getAllPosts()
    const blogRoutes = posts.map((post) => ({
        url: `${BASE_URL}/blog/${post.slug}`,
        lastModified: new Date(post.date),
        changeFrequency: 'monthly' as const,
        priority: 0.6,
    }))

    // Dynamic prediction routes - try to fetch from API
    let predictionRoutes: MetadataRoute.Sitemap = []
    try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://betglitch.com/api'
        const res = await fetch(`${API_URL}/recommendations/`, { next: { revalidate: 3600 } })
        if (res.ok) {
            const data = await res.json()
            predictionRoutes = (data.results || data.recommendations || []).slice(0, 100).map((fixture: any) => ({
                url: `${BASE_URL}/prediction/${fixture.league ? fixture.league.toLowerCase().replace(/[^a-z0-9]+/g, '-') : 'league'}/${fixture.home_team?.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-vs-${fixture.away_team?.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${fixture.kickoff?.split('T')[0]}-${fixture.fixture_id || fixture.id}`,
                lastModified: new Date(),
                changeFrequency: 'daily' as const,
                priority: 0.8,
            }))
        }
    } catch (e) {
        console.error('Failed to fetch predictions for sitemap:', e)
    }

    return [...staticRoutes, ...blogRoutes, ...predictionRoutes]
}
