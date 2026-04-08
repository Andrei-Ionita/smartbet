import { Metadata } from 'next'
import Link from 'next/link'
import { getAllPosts } from './posts'
import { ArrowRight, Clock, Calendar } from 'lucide-react'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'Blog — AI Betting Insights & Strategy',
  description: 'Expert articles on AI-powered football predictions, value betting strategy, and transparent sports analytics from the BetGlitch team.',
  openGraph: {
    title: 'Blog — AI Betting Insights & Strategy | BetGlitch',
    description: 'Expert articles on AI-powered football predictions, value betting, and sports analytics.',
    url: 'https://betglitch.com/blog',
  },
}

export default function BlogPage() {
  const posts = getAllPosts()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'Blog', url: 'https://betglitch.com/blog' },
      ]} />
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">BetGlitch Blog</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Insights on AI-powered football predictions, value betting strategy, and transparent sports analytics.
          </p>
        </div>

        <div className="grid gap-8">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group bg-white rounded-2xl p-8 shadow-sm border border-gray-200 hover:shadow-lg hover:border-primary-200 transition-all duration-300"
            >
              <div className="flex flex-wrap gap-2 mb-4">
                {post.tags.map((tag) => (
                  <span key={tag} className="px-3 py-1 bg-primary-50 text-primary-700 text-xs font-medium rounded-full">
                    {tag}
                  </span>
                ))}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 group-hover:text-primary-600 transition-colors mb-3">
                {post.title}
              </h2>
              <p className="text-gray-600 mb-4 leading-relaxed">{post.description}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {new Date(post.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {post.readTime}
                  </span>
                </div>
                <span className="flex items-center gap-1 text-primary-600 font-medium text-sm group-hover:gap-2 transition-all">
                  Read article <ArrowRight className="h-4 w-4" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
