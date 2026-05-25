/**
 * Performance Logger for Development and Debugging
 */

interface LogEntry {
  timestamp: Date
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  data?: any
  duration?: number
  url?: string
}

class PerformanceLogger {
  private logs: LogEntry[] = []
  private maxLogs = 1000
  private isEnabled = process.env.NODE_ENV === 'development'

  /**
   * Log an info message
   */
  info(message: string, data?: any): void {
    this.log('info', message, data)
  }

  /**
   * Log a warning message
   */
  warn(message: string, data?: any): void {
    this.log('warn', message, data)
  }

  /**
   * Log an error message
   */
  error(message: string, data?: any): void {
    this.log('error', message, data)
  }

  /**
   * Log a debug message
   */
  debug(message: string, data?: any): void {
    this.log('debug', message, data)
  }

  /**
   * Log API request performance
   */
  logApiRequest(url: string, method: string, duration: number, success: boolean, error?: string): void {
    const level = success ? 'info' : 'error'
    const message = `${method} ${url} - ${duration}ms`
    const data = {
      url,
      method,
      duration,
      success,
      error
    }

    this.log(level, message, data)
  }

  /**
   * Log cache operation
   */
  logCacheOperation(operation: 'hit' | 'miss' | 'set', key: string, duration?: number): void {
    const message = `Cache ${operation}: ${key}`
    const data = {
      operation,
      key,
      duration
    }

    this.log('debug', message, data)
  }

  /**
   * Log rate limit event
   */
  logRateLimit(type: 'hit' | 'wait', duration?: number): void {
    const message = `Rate limit ${type}`
    const data = {
      type,
      duration
    }

    this.log('warn', message, data)
  }

  /**
   * Core logging method
   */
  private log(level: 'info' | 'warn' | 'error' | 'debug', message: string, data?: any): void {
    if (!this.isEnabled) return

    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      message,
      data
    }

    this.logs.push(entry)

    // Keep only the last maxLogs entries
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs)
    }

    // Console output with appropriate styling
    const timestamp = entry.timestamp.toISOString()
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`
    
    switch (level) {
      case 'info':
        console.log(`%c${prefix} ${message}`, 'color: #2563eb', data)
        break
      case 'warn':
        console.warn(`%c${prefix} ${message}`, 'color: #d97706', data)
        break
      case 'error':
        console.error(`%c${prefix} ${message}`, 'color: #dc2626', data)
        break
      case 'debug':
        console.debug(`%c${prefix} ${message}`, 'color: #6b7280', data)
        break
    }
  }

  /**
   * Get recent logs
   */
  getRecentLogs(count: number = 50): LogEntry[] {
    return this.logs.slice(-count)
  }

  /**
   * Get logs by level
   */
  getLogsByLevel(level: 'info' | 'warn' | 'error' | 'debug'): LogEntry[] {
    return this.logs.filter(log => log.level === level)
  }

  /**
   * Get performance summary
   */
  getPerformanceSummary(): {
    totalLogs: number
    errorCount: number
    warningCount: number
    averageApiResponseTime: number
    cacheHitRate: number
  } {
    const apiLogs = this.logs.filter(log => log.data?.duration && log.message.includes('ms'))
    const cacheLogs = this.logs.filter(log => log.data?.operation)
    const errorCount = this.logs.filter(log => log.level === 'error').length
    const warningCount = this.logs.filter(log => log.level === 'warn').length

    const averageApiResponseTime = apiLogs.length > 0
      ? Math.round(apiLogs.reduce((sum, log) => sum + (log.data?.duration || 0), 0) / apiLogs.length)
      : 0

    const cacheHits = cacheLogs.filter(log => log.data?.operation === 'hit').length
    const cacheMisses = cacheLogs.filter(log => log.data?.operation === 'miss').length
    const cacheHitRate = (cacheHits + cacheMisses) > 0 
      ? Math.round((cacheHits / (cacheHits + cacheMisses)) * 100)
      : 0

    return {
      totalLogs: this.logs.length,
      errorCount,
      warningCount,
      averageApiResponseTime,
      cacheHitRate
    }
  }

  /**
   * Clear all logs
   */
  clear(): void {
    this.logs = []
    console.clear()
    this.info('Performance logs cleared')
  }

  /**
   * Export logs as JSON
   */
  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2)
  }

  /**
   * Enable or disable logging
   */
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled
    this.info(`Performance logging ${enabled ? 'enabled' : 'disabled'}`)
  }
}

// Export singleton instance
export const performanceLogger = new PerformanceLogger()

// Convenience functions for global use
export const logInfo = (message: string, data?: any) => performanceLogger.info(message, data)
export const logWarn = (message: string, data?: any) => performanceLogger.warn(message, data)
export const logError = (message: string, data?: any) => performanceLogger.error(message, data)
export const logDebug = (message: string, data?: any) => performanceLogger.debug(message, data)
export const logApiRequest = (url: string, method: string, duration: number, success: boolean, error?: string) => 
  performanceLogger.logApiRequest(url, method, duration, success, error)
export const logCacheOperation = (operation: 'hit' | 'miss' | 'set', key: string, duration?: number) => 
  performanceLogger.logCacheOperation(operation, key, duration)
export const logRateLimit = (type: 'hit' | 'wait', duration?: number) => 
  performanceLogger.logRateLimit(type, duration)
