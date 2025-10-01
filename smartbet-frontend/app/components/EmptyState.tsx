'use client'

import { Trophy, RefreshCw } from 'lucide-react'

interface EmptyStateProps {
  onRetry?: () => void
  onBrowseAll?: () => void
}

export default function EmptyState({ onRetry, onBrowseAll }: EmptyStateProps) {
  return (
    <div className="text-center py-16">
      <div className="relative inline-block mb-8">
        <div className="absolute -inset-4 bg-gradient-to-r from-gray-200 to-gray-300 rounded-full blur opacity-30"></div>
        <div className="relative bg-white p-6 rounded-full shadow-lg">
          <Trophy className="h-16 w-16 text-gray-400" />
        </div>
      </div>
      
      <h3 className="text-2xl font-bold text-gray-900 mb-4">
        No Recommended Picks Available
      </h3>
      <p className="text-lg text-gray-600 mb-8 max-w-lg mx-auto leading-relaxed">
        We'll surface new recommendations as soon as upcoming fixtures have predictions. 
        Check back later or browse all available fixtures.
      </p>
      
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        {onBrowseAll && (
          <button
            onClick={onBrowseAll}
            className="group bg-gradient-to-r from-primary-600 to-blue-600 hover:from-primary-700 hover:to-blue-700 text-white font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
          >
            Browse All Upcoming Fixtures
          </button>
        )}
        {onRetry && (
          <button
            onClick={onRetry}
            className="group bg-white/80 backdrop-blur-sm hover:bg-white text-gray-700 font-semibold py-3 px-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200 inline-flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4 group-hover:rotate-180 transition-transform" />
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}
