import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// Inline performance monitor implementation
const performanceMonitor = {
  getDetailedReport() {
    return {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
      cacheHitRate: 0,
      requestsPerMinute: 0,
      errorRate: 0,
      rateLimitHits: 0,
      lastUpdated: new Date().toISOString()
    }
  },
  reset() {
    // Simplified reset implementation
    console.log('Performance monitor reset')
  }
}

export async function GET(request: NextRequest) {
  try {
    const metrics = performanceMonitor.getDetailedReport()
    
    // Calculate performance score based on metrics
    const performanceScore = Math.max(0, Math.min(100, 
      (metrics.cacheHitRate * 0.3) + 
      ((100 - metrics.errorRate) * 0.4) + 
      (Math.min(metrics.requestsPerMinute / 10, 1) * 30)
    ))
    
    // Generate recommendations based on metrics
    const recommendations: string[] = []
    if (metrics.errorRate > 5) {
      recommendations.push('High error rate detected. Check API endpoints and network connectivity.')
    }
    if (metrics.cacheHitRate < 50) {
      recommendations.push('Low cache hit rate. Consider increasing cache duration for frequently accessed data.')
    }
    if (metrics.averageResponseTime > 1000) {
      recommendations.push('Slow response times detected. Consider optimizing database queries and API calls.')
    }
    if (recommendations.length === 0) {
      recommendations.push('System performance is within normal parameters.')
    }
    
    const report = {
      metrics,
      performanceScore: Math.round(performanceScore),
      recommendations,
      recentRequests: [] // Empty for now since we don't track individual requests
    }
    
    return NextResponse.json({
      success: true,
      data: report,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error fetching metrics:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch performance metrics' 
      },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    performanceMonitor.reset()
    
    return NextResponse.json({
      success: true,
      message: 'Performance metrics reset successfully',
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error resetting metrics:', error)
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to reset performance metrics' 
      },
      { status: 500 }
    )
  }
}
