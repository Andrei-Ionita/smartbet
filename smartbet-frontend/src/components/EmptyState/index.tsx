'use client'

import { Trophy, RefreshCw } from 'lucide-react'

interface EmptyStateProps {
  onRetry?: () => void
  onBrowseAll?: () => void
}

export default function EmptyState({ onRetry, onBrowseAll }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <div className="flex justify-center mb-6">
        <Trophy className="h-16 w-16 text-gray-300" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        No recommended picks right now
      </h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        We'll surface new recommendations as soon as upcoming fixtures have predictions.
      </p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        {onBrowseAll && (
          <button
            onClick={onBrowseAll}
            className="btn-primary"
          >
            Browse All Upcoming Fixtures
          </button>
        )}
        {onRetry && (
          <button
            onClick={onRetry}
            className="btn-secondary inline-flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}
