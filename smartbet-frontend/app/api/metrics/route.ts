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
      errorRate: 0
    }
  },
  reset() {
    // Simplified reset implementation
    console.log('Performance monitor reset')
  }
}

export async function GET(request: NextRequest) {
  try {
    const report = performanceMonitor.getDetailedReport()
    
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
