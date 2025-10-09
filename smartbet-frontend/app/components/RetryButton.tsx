'use client'

import { useState } from 'react'
import { RefreshCw } from 'lucide-react'

interface RetryButtonProps {
  onRetry: () => Promise<void> | void
  text?: string
  className?: string
}

export default function RetryButton({ onRetry, text = 'Retry', className = '' }: RetryButtonProps) {
  const [isRetrying, setIsRetrying] = useState(false)

  const handleRetry = async () => {
    setIsRetrying(true)
    try {
      await onRetry()
    } finally {
      setIsRetrying(false)
    }
  }

  return (
    <button
      onClick={handleRetry}
      disabled={isRetrying}
      className={`inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${className}`}
    >
      <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
      {isRetrying ? 'Retrying...' : text}
    </button>
  )
}
