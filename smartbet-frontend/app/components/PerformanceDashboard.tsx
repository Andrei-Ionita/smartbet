'use client'

import { useState, useEffect } from 'react'
import { 
  Activity, 
  Clock, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Zap,
  Database,
  RefreshCw
} from 'lucide-react'

interface PerformanceMetrics {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  averageResponseTime: number
  cacheHitRate: number
  rateLimitHits: number
  lastUpdated: Date
}

interface PerformanceReport {
  metrics: PerformanceMetrics
  recentRequests: any[]
  performanceScore: number
  recommendations: string[]
}

export default function PerformanceDashboard() {
  const [report, setReport] = useState<PerformanceReport | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/metrics')
      const data = await response.json()
      
      if (data.success) {
        setReport(data.data)
        setError(null)
      } else {
        setError(data.error || 'Failed to fetch metrics')
      }
    } catch (err) {
      setError('Failed to fetch performance metrics')
      console.error('Error fetching metrics:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const resetMetrics = async () => {
    try {
      const response = await fetch('/api/metrics', { method: 'DELETE' })
      const data = await response.json()
      
      if (data.success) {
        await fetchMetrics()
      } else {
        setError(data.error || 'Failed to reset metrics')
      }
    } catch (err) {
      setError('Failed to reset metrics')
      console.error('Error resetting metrics:', err)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(fetchMetrics, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [autoRefresh])

  const getPerformanceColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getPerformanceBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100'
    if (score >= 60) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-red-200">
        <div className="flex items-center gap-3 mb-4">
          <XCircle className="h-6 w-6 text-red-500" />
          <h2 className="text-xl font-bold text-red-900">Performance Monitoring Error</h2>
        </div>
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={fetchMetrics}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    )
  }

  if (!report || !report.metrics) return null

  const { metrics, performanceScore = 0, recommendations = [] } = report
  const successRate = metrics && metrics.totalRequests > 0 
    ? Math.round((metrics.successfulRequests / metrics.totalRequests) * 100) 
    : 0

  return (
    <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <Activity className="h-6 w-6 text-primary-600" />
          <h2 className="text-xl font-bold text-gray-900">Performance Dashboard</h2>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh
          </label>
          <button
            onClick={fetchMetrics}
            className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
            title="Refresh metrics"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={resetMetrics}
            className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Performance Score */}
      <div className={`${getPerformanceBgColor(performanceScore)} rounded-xl p-4 mb-6`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Performance Score</h3>
            <p className="text-sm text-gray-600">Overall system performance rating</p>
          </div>
          <div className={`text-3xl font-bold ${getPerformanceColor(performanceScore)}`}>
            {performanceScore}/100
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Database className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-700">Total Requests</span>
          </div>
          <div className="text-2xl font-bold text-blue-900">{metrics.totalRequests}</div>
        </div>

        <div className="bg-green-50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span className="text-sm font-medium text-green-700">Success Rate</span>
          </div>
          <div className="text-2xl font-bold text-green-900">{successRate}%</div>
        </div>

        <div className="bg-purple-50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="h-5 w-5 text-purple-600" />
            <span className="text-sm font-medium text-purple-700">Avg Response</span>
          </div>
          <div className="text-2xl font-bold text-purple-900">{metrics.averageResponseTime}ms</div>
        </div>

        <div className="bg-orange-50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-5 w-5 text-orange-600" />
            <span className="text-sm font-medium text-orange-700">Cache Hit Rate</span>
          </div>
          <div className="text-2xl font-bold text-orange-900">{metrics.cacheHitRate}%</div>
        </div>
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="text-sm font-medium text-gray-600 mb-1">Failed Requests</div>
          <div className="text-xl font-bold text-gray-900">{metrics.failedRequests}</div>
        </div>

        <div className="bg-red-50 rounded-xl p-4">
          <div className="text-sm font-medium text-red-600 mb-1">Rate Limit Hits</div>
          <div className="text-xl font-bold text-red-900">{metrics.rateLimitHits}</div>
        </div>

        <div className="bg-indigo-50 rounded-xl p-4">
          <div className="text-sm font-medium text-indigo-600 mb-1">Last Updated</div>
          <div className="text-sm font-bold text-indigo-900">
            {new Date(metrics.lastUpdated).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-blue-50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-blue-900">Recommendations</h3>
          </div>
          <ul className="space-y-2">
            {recommendations.map((rec, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-blue-800">
                <AlertTriangle className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
