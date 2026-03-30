/**
 * Smart API Client with Rate Limiting and Request Management
 */

import { performanceMonitor } from './performance-monitor'
import { logApiRequest, logRateLimit } from './performance-logger'

interface RequestQueue {
  [key: string]: Array<{
    resolve: (value: any) => void
    reject: (error: any) => void
    timestamp: number
  }>
}

interface RateLimitConfig {
  requestsPerMinute: number
  requestsPerSecond: number
  burstLimit: number
}

class SmartAPIClient {
  private requestQueue: RequestQueue = {}
  private rateLimitConfig: RateLimitConfig = {
    requestsPerMinute: 60,    // SportMonks allows 60 requests per minute
    requestsPerSecond: 2,     // Conservative: 2 requests per second
    burstLimit: 5             // Allow bursts of up to 5 requests
  }
  
  private requestCounts = {
    minute: 0,
    second: 0,
    lastMinuteReset: Date.now(),
    lastSecondReset: Date.now()
  }

  private pendingRequests = new Map<string, Promise<any>>()

  constructor() {
    // Reset counters every minute
    setInterval(() => {
      this.requestCounts.minute = 0
      this.requestCounts.lastMinuteReset = Date.now()
    }, 60000)

    // Reset second counter every second
    setInterval(() => {
      this.requestCounts.second = 0
      this.requestCounts.lastSecondReset = Date.now()
    }, 1000)
  }

  /**
   * Smart request with rate limiting, caching, and deduplication
   */
  async request(url: string, options: RequestInit = {}): Promise<any> {
    // Check if request is already pending (deduplication)
    const requestKey = this.getRequestKey(url, options)
    if (this.pendingRequests.has(requestKey)) {
      console.log(`🔄 Deduplicating request: ${url}`)
      return this.pendingRequests.get(requestKey)
    }

    // Create the request promise
    const requestPromise = this.executeRequest(url, options)
    this.pendingRequests.set(requestKey, requestPromise)

    try {
      const result = await requestPromise
      return result
    } finally {
      // Clean up pending request
      this.pendingRequests.delete(requestKey)
    }
  }

  /**
   * Execute request with rate limiting
   */
  private async executeRequest(url: string, options: RequestInit = {}): Promise<any> {
    // Start performance monitoring
    const requestMetrics = performanceMonitor.startRequest(url, options.method || 'GET')
    
    // Wait for rate limit
    await this.waitForRateLimit()

    console.log(`🚀 Making API request: ${url}`)
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'SmartBet/1.0',
          ...options.headers
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      this.incrementCounters()
      
      // Record successful request
      performanceMonitor.endRequest(requestMetrics, true)
      logApiRequest(url, options.method || 'GET', Date.now() - requestMetrics.startTime, true)
      
      return data
    } catch (error) {
      console.error(`❌ API request failed: ${url}`, error)
      
      // Record failed request
      performanceMonitor.endRequest(requestMetrics, false, error instanceof Error ? error.message : 'Unknown error')
      logApiRequest(url, options.method || 'GET', Date.now() - requestMetrics.startTime, false, error instanceof Error ? error.message : 'Unknown error')
      
      // Implement exponential backoff for failed requests
      if (this.shouldRetry(error)) {
        const delay = this.calculateBackoffDelay()
        console.log(`⏳ Retrying in ${delay}ms...`)
        await this.delay(delay)
        return this.executeRequest(url, options)
      }
      
      throw error
    }
  }

  /**
   * Wait for rate limit if necessary
   */
  private async waitForRateLimit(): Promise<void> {
    const now = Date.now()
    
    // Check minute limit
    if (this.requestCounts.minute >= this.rateLimitConfig.requestsPerMinute) {
      const timeUntilReset = 60000 - (now - this.requestCounts.lastMinuteReset)
      console.log(`⏳ Rate limit reached. Waiting ${timeUntilReset}ms...`)
      performanceMonitor.recordRateLimit()
      logRateLimit('hit', timeUntilReset)
      await this.delay(timeUntilReset)
    }

    // Check second limit
    if (this.requestCounts.second >= this.rateLimitConfig.requestsPerSecond) {
      const timeUntilReset = 1000 - (now - this.requestCounts.lastSecondReset)
      console.log(`⏳ Second limit reached. Waiting ${timeUntilReset}ms...`)
      performanceMonitor.recordRateLimit()
      logRateLimit('wait', timeUntilReset)
      await this.delay(timeUntilReset)
    }
  }

  /**
   * Increment request counters
   */
  private incrementCounters(): void {
    this.requestCounts.minute++
    this.requestCounts.second++
  }

  /**
   * Check if request should be retried
   */
  private shouldRetry(error: any): boolean {
    if (error.message.includes('HTTP 429')) return true // Too Many Requests
    if (error.message.includes('HTTP 5')) return true   // Server errors
    return false
  }

  /**
   * Calculate exponential backoff delay
   */
  private calculateBackoffDelay(): number {
    return Math.random() * 2000 + 1000 // 1-3 seconds
  }

  /**
   * Create unique key for request deduplication
   */
  private getRequestKey(url: string, options: RequestInit): string {
    const method = options.method || 'GET'
    const body = options.body ? JSON.stringify(options.body) : ''
    return `${method}:${url}:${body}`
  }

  /**
   * Utility delay function
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * Batch multiple requests efficiently
   */
  async batchRequests<T>(
    requests: Array<() => Promise<T>>,
    batchSize: number = 3,
    delayBetweenBatches: number = 1000
  ): Promise<T[]> {
    const results: T[] = []
    
    for (let i = 0; i < requests.length; i += batchSize) {
      const batch = requests.slice(i, i + batchSize)
      
      console.log(`📦 Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(requests.length / batchSize)}`)
      
      const batchPromises = batch.map(request => request())
      const batchResults = await Promise.all(batchPromises)
      results.push(...batchResults)
      
      // Delay between batches to respect rate limits
      if (i + batchSize < requests.length) {
        await this.delay(delayBetweenBatches)
      }
    }
    
    return results
  }

  /**
   * Get current rate limit status
   */
  getRateLimitStatus() {
    return {
      requestsThisMinute: this.requestCounts.minute,
      requestsThisSecond: this.requestCounts.second,
      minuteLimit: this.rateLimitConfig.requestsPerMinute,
      secondLimit: this.rateLimitConfig.requestsPerSecond,
      pendingRequests: this.pendingRequests.size
    }
  }
}

// Export singleton instance
export const apiClient = new SmartAPIClient()

// Export utility functions
export const createBatchedLeagueRequests = (leagueIds: number[], startDate: string, endDate: string) => {
  return leagueIds.map(leagueId => () => 
    apiClient.request(`https://api.sportmonks.com/v3/football/fixtures/between/${startDate}/${endDate}`, {
      method: 'GET',
      headers: {
        'api_token': process.env.SPORTMONKS_API_TOKEN || ''
      }
    })
  )
}
