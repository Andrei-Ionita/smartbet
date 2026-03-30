/**
 * Performance Monitor for API Usage and Rate Limiting
 */

interface PerformanceMetrics {
  totalRequests: number
  successfulRequests: number
  failedRequests: number
  averageResponseTime: number
  cacheHitRate: number
  rateLimitHits: number
  lastUpdated: Date
}

interface RequestMetrics {
  url: string
  method: string
  startTime: number
  endTime?: number
  success?: boolean
  error?: string
  fromCache?: boolean
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics = {
    totalRequests: 0,
    successfulRequests: 0,
    failedRequests: 0,
    averageResponseTime: 0,
    cacheHitRate: 0,
    rateLimitHits: 0,
    lastUpdated: new Date()
  }

  private requestHistory: RequestMetrics[] = []
  private responseTimes: number[] = []
  private cacheHits = 0
  private cacheMisses = 0

  /**
   * Start tracking a request
   */
  startRequest(url: string, method: string = 'GET'): RequestMetrics {
    const request: RequestMetrics = {
      url,
      method,
      startTime: Date.now()
    }

    this.requestHistory.push(request)
    this.metrics.totalRequests++

    return request
  }

  /**
   * End tracking a request
   */
  endRequest(request: RequestMetrics, success: boolean = true, error?: string, fromCache: boolean = false): void {
    const endTime = Date.now()
    const responseTime = endTime - request.startTime

    request.endTime = endTime
    request.success = success
    request.error = error
    request.fromCache = fromCache

    // Update metrics
    if (success) {
      this.metrics.successfulRequests++
    } else {
      this.metrics.failedRequests++
    }

    if (!fromCache) {
      this.responseTimes.push(responseTime)
      this.updateAverageResponseTime()
    }

    if (fromCache) {
      this.cacheHits++
    } else {
      this.cacheMisses++
    }

    this.updateCacheHitRate()
    this.metrics.lastUpdated = new Date()

    // Log performance
    this.logRequest(request, responseTime)
  }

  /**
   * Record a rate limit hit
   */
  recordRateLimit(): void {
    this.metrics.rateLimitHits++
    console.log(`🚫 Rate limit hit! Total: ${this.metrics.rateLimitHits}`)
  }

  /**
   * Update average response time
   */
  private updateAverageResponseTime(): void {
    if (this.responseTimes.length > 0) {
      const sum = this.responseTimes.reduce((a, b) => a + b, 0)
      this.metrics.averageResponseTime = Math.round(sum / this.responseTimes.length)
    }
  }

  /**
   * Update cache hit rate
   */
  private updateCacheHitRate(): void {
    const totalCacheRequests = this.cacheHits + this.cacheMisses
    if (totalCacheRequests > 0) {
      this.metrics.cacheHitRate = Math.round((this.cacheHits / totalCacheRequests) * 100)
    }
  }

  /**
   * Log request performance
   */
  private logRequest(request: RequestMetrics, responseTime: number): void {
    const status = request.success ? '✅' : '❌'
    const cache = request.fromCache ? '🎯' : '🚀'
    const method = request.method.padEnd(4)
    const time = `${responseTime}ms`.padStart(6)
    const url = request.url.replace('https://api.sportmonks.com/v3/football/', '')

    console.log(`${status} ${cache} ${method} ${time} ${url}`)
  }

  /**
   * Get current performance metrics
   */
  getMetrics(): PerformanceMetrics {
    return { ...this.metrics }
  }

  /**
   * Get detailed performance report
   */
  getDetailedReport(): {
    metrics: PerformanceMetrics
    recentRequests: RequestMetrics[]
    performanceScore: number
    recommendations: string[]
  } {
    const recentRequests = this.requestHistory.slice(-20) // Last 20 requests
    const performanceScore = this.calculatePerformanceScore()
    const recommendations = this.generateRecommendations()

    return {
      metrics: this.getMetrics(),
      recentRequests,
      performanceScore,
      recommendations
    }
  }

  /**
   * Calculate overall performance score (0-100)
   */
  private calculatePerformanceScore(): number {
    let score = 100

    // Deduct for failed requests
    if (this.metrics.totalRequests > 0) {
      const failureRate = (this.metrics.failedRequests / this.metrics.totalRequests) * 100
      score -= failureRate * 2 // Each failed request costs 2 points
    }

    // Deduct for slow response times
    if (this.metrics.averageResponseTime > 3000) {
      score -= 20 // Very slow responses
    } else if (this.metrics.averageResponseTime > 2000) {
      score -= 10 // Slow responses
    }

    // Deduct for rate limit hits
    score -= this.metrics.rateLimitHits * 5 // Each rate limit hit costs 5 points

    // Bonus for high cache hit rate
    if (this.metrics.cacheHitRate > 70) {
      score += 10
    } else if (this.metrics.cacheHitRate > 50) {
      score += 5
    }

    return Math.max(0, Math.min(100, Math.round(score)))
  }

  /**
   * Generate performance recommendations
   */
  private generateRecommendations(): string[] {
    const recommendations: string[] = []

    if (this.metrics.cacheHitRate < 30) {
      recommendations.push('Consider increasing cache duration for better performance')
    }

    if (this.metrics.averageResponseTime > 2000) {
      recommendations.push('Response times are slow - consider optimizing API calls')
    }

    if (this.metrics.rateLimitHits > 5) {
      recommendations.push('High rate limit hits - consider reducing request frequency')
    }

    if (this.metrics.failedRequests > this.metrics.totalRequests * 0.1) {
      recommendations.push('High failure rate - check API stability and error handling')
    }

    if (recommendations.length === 0) {
      recommendations.push('Performance is optimal! 🎉')
    }

    return recommendations
  }

  /**
   * Reset metrics
   */
  reset(): void {
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
      cacheHitRate: 0,
      rateLimitHits: 0,
      lastUpdated: new Date()
    }

    this.requestHistory = []
    this.responseTimes = []
    this.cacheHits = 0
    this.cacheMisses = 0

    console.log('📊 Performance metrics reset')
  }

  /**
   * Export metrics for analysis
   */
  exportMetrics(): string {
    const report = this.getDetailedReport()
    return JSON.stringify(report, null, 2)
  }
}

// Export singleton instance
export const performanceMonitor = new PerformanceMonitor()

// Utility function to log performance metrics
export const logPerformanceMetrics = () => {
  const report = performanceMonitor.getDetailedReport()
  console.log('📊 Performance Report:')
  console.log(`   Score: ${report.performanceScore}/100`)
  console.log(`   Total Requests: ${report.metrics.totalRequests}`)
  console.log(`   Success Rate: ${Math.round((report.metrics.successfulRequests / report.metrics.totalRequests) * 100)}%`)
  console.log(`   Cache Hit Rate: ${report.metrics.cacheHitRate}%`)
  console.log(`   Avg Response Time: ${report.metrics.averageResponseTime}ms`)
  console.log(`   Rate Limit Hits: ${report.metrics.rateLimitHits}`)
  console.log('📋 Recommendations:')
  report.recommendations.forEach(rec => console.log(`   • ${rec}`))
}
