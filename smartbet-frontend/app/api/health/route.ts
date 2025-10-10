import { NextRequest, NextResponse } from 'next/server'
import { performanceMonitor } from '../../lib/performance-monitor'

export async function GET(request: NextRequest) {
  try {
    const metrics = performanceMonitor.getMetrics()
    
    // Determine system health based on metrics
    const healthStatus = {
      status: 'healthy',
      score: 0,
      issues: [] as string[]
    }

    // Calculate health score
    let score = 100

    // Check success rate
    if (metrics.totalRequests > 0) {
      const successRate = (metrics.successfulRequests / metrics.totalRequests) * 100
      if (successRate < 90) {
        healthStatus.issues.push(`Low success rate: ${Math.round(successRate)}%`)
        score -= (90 - successRate) * 2
      }
    }

    // Check response time
    if (metrics.averageResponseTime > 3000) {
      healthStatus.issues.push(`Slow response time: ${metrics.averageResponseTime}ms`)
      score -= 20
    }

    // Check rate limit hits
    if (metrics.rateLimitHits > 10) {
      healthStatus.issues.push(`High rate limit hits: ${metrics.rateLimitHits}`)
      score -= metrics.rateLimitHits * 2
    }

    // Check cache hit rate
    if (metrics.cacheHitRate < 30) {
      healthStatus.issues.push(`Low cache hit rate: ${metrics.cacheHitRate}%`)
      score -= 10
    }

    healthStatus.score = Math.max(0, Math.round(score))

    // Determine overall status
    if (healthStatus.score >= 80) {
      healthStatus.status = 'healthy'
    } else if (healthStatus.score >= 60) {
      healthStatus.status = 'degraded'
    } else {
      healthStatus.status = 'unhealthy'
    }

    const response = {
      status: 'success',
      timestamp: new Date().toISOString(),
      health: healthStatus,
      metrics: {
        totalRequests: metrics.totalRequests,
        successRate: metrics.totalRequests > 0 
          ? Math.round((metrics.successfulRequests / metrics.totalRequests) * 100) 
          : 0,
        averageResponseTime: metrics.averageResponseTime,
        cacheHitRate: metrics.cacheHitRate,
        rateLimitHits: metrics.rateLimitHits,
        lastUpdated: metrics.lastUpdated
      },
      services: {
        api: 'operational',
        cache: 'operational',
        database: 'operational',
        rateLimiting: 'operational'
      }
    }

    // Set appropriate HTTP status code
    const httpStatus = healthStatus.status === 'healthy' ? 200 : 
                      healthStatus.status === 'degraded' ? 200 : 503

    return NextResponse.json(response, { status: httpStatus })

  } catch (error) {
    console.error('Health check error:', error)
    
    return NextResponse.json({
      status: 'error',
      timestamp: new Date().toISOString(),
      health: {
        status: 'unhealthy',
        score: 0,
        issues: ['Health check failed']
      },
      error: 'Internal server error'
    }, { status: 503 })
  }
}
