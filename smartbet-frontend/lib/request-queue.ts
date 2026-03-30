/**
 * Request Queue Manager for Efficient API Call Management
 */

interface QueuedRequest {
  id: string
  url: string
  options: RequestInit
  priority: 'high' | 'medium' | 'low'
  timestamp: number
  resolve: (value: any) => void
  reject: (error: any) => void
}

interface QueueConfig {
  maxConcurrent: number
  highPriorityLimit: number
  processingInterval: number
}

class RequestQueueManager {
  private queue: QueuedRequest[] = []
  private processing: Set<string> = new Set()
  private config: QueueConfig = {
    maxConcurrent: 3,        // Max 3 concurrent requests
    highPriorityLimit: 1,    // Max 1 high priority request at a time
    processingInterval: 100  // Process queue every 100ms
  }

  private processingInterval?: NodeJS.Timeout

  constructor() {
    this.startProcessing()
  }

  /**
   * Add request to queue
   */
  enqueue(
    id: string,
    url: string,
    options: RequestInit,
    priority: 'high' | 'medium' | 'low' = 'medium'
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const request: QueuedRequest = {
        id,
        url,
        options,
        priority,
        timestamp: Date.now(),
        resolve,
        reject
      }

      // Insert based on priority
      this.insertByPriority(request)
      console.log(`📥 Queued request: ${id} (priority: ${priority}, position: ${this.getQueuePosition(id)})`)
    })
  }

  /**
   * Insert request based on priority
   */
  private insertByPriority(request: QueuedRequest): void {
    const priorityOrder = { high: 3, medium: 2, low: 1 }
    
    let insertIndex = this.queue.length
    for (let i = 0; i < this.queue.length; i++) {
      if (priorityOrder[request.priority] > priorityOrder[this.queue[i].priority]) {
        insertIndex = i
        break
      }
    }
    
    this.queue.splice(insertIndex, 0, request)
  }

  /**
   * Get queue position for a request
   */
  private getQueuePosition(id: string): number {
    return this.queue.findIndex(req => req.id === id) + 1
  }

  /**
   * Start processing the queue
   */
  private startProcessing(): void {
    this.processingInterval = setInterval(() => {
      this.processQueue()
    }, this.config.processingInterval)
  }

  /**
   * Process queued requests
   */
  private async processQueue(): Promise<void> {
    // Don't process if we're at the concurrent limit
    if (this.processing.size >= this.config.maxConcurrent) {
      return
    }

    // Find next request to process
    const nextRequest = this.getNextRequest()
    if (!nextRequest) {
      return
    }

    // Start processing the request
    this.processing.add(nextRequest.id)
    this.queue = this.queue.filter(req => req.id !== nextRequest.id)

    console.log(`🚀 Processing request: ${nextRequest.id}`)

    try {
      const result = await this.executeRequest(nextRequest)
      nextRequest.resolve(result)
      console.log(`✅ Completed request: ${nextRequest.id}`)
    } catch (error) {
      nextRequest.reject(error)
      console.error(`❌ Failed request: ${nextRequest.id}`, error)
    } finally {
      this.processing.delete(nextRequest.id)
    }
  }

  /**
   * Get next request to process based on priority and limits
   */
  private getNextRequest(): QueuedRequest | null {
    // Check if we can process high priority requests
    const highPriorityCount = Array.from(this.processing).filter(id => 
      this.queue.find(req => req.id === id)?.priority === 'high'
    ).length

    // Find highest priority request we can process
    for (const request of this.queue) {
      if (request.priority === 'high' && highPriorityCount < this.config.highPriorityLimit) {
        return request
      }
      if (request.priority !== 'high') {
        return request
      }
    }

    return null
  }

  /**
   * Execute the actual request
   */
  private async executeRequest(request: QueuedRequest): Promise<any> {
    const response = await fetch(request.url, {
      ...request.options,
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'SmartBet/1.0',
        ...request.options.headers
      }
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get queue status
   */
  getQueueStatus() {
    return {
      queueLength: this.queue.length,
      processing: Array.from(this.processing),
      queue: this.queue.map(req => ({
        id: req.id,
        priority: req.priority,
        timestamp: req.timestamp,
        waitTime: Date.now() - req.timestamp
      }))
    }
  }

  /**
   * Clear the queue
   */
  clearQueue(): void {
    this.queue.forEach(request => {
      request.reject(new Error('Queue cleared'))
    })
    this.queue = []
    console.log('🧹 Queue cleared')
  }

  /**
   * Stop processing
   */
  stop(): void {
    if (this.processingInterval) {
      clearInterval(this.processingInterval)
    }
    this.clearQueue()
  }
}

// Export singleton instance
export const requestQueue = new RequestQueueManager()

// Utility function to create request IDs
export const createRequestId = (url: string, options?: RequestInit): string => {
  const method = options?.method || 'GET'
  const body = options?.body ? JSON.stringify(options.body) : ''
  return `${method}:${url}:${body}`.replace(/[^a-zA-Z0-9]/g, '_')
}
