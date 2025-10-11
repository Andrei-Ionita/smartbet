import { NextRequest, NextResponse } from 'next/server'
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const execAsync = promisify(exec)

export async function GET(request: NextRequest) {
  try {
    // Path to the Django project root (one level up from smartbet-frontend)
    const projectRoot = path.join(process.cwd(), '..')
    const scriptPath = path.join(projectRoot, 'production', 'scripts', 'get_performance_stats.py')
    
    // Execute the Python script to get performance stats
    const { stdout, stderr } = await execAsync(
      `python "${scriptPath}" --json`,
      { 
        cwd: projectRoot,
        timeout: 30000 // 30 second timeout
      }
    )
    
    if (stderr && !stderr.includes('UserWarning')) {
      console.error('Performance stats stderr:', stderr)
    }
    
    // Parse the JSON output
    const stats = JSON.parse(stdout)
    
    return NextResponse.json({
      success: true,
      data: stats,
      timestamp: new Date().toISOString()
    })
    
  } catch (error: any) {
    console.error('Error fetching performance stats:', error)
    
    // Return empty stats structure if no data yet
    return NextResponse.json({
      success: true,
      data: {
        overall: {
          total_predictions: 0,
          correct_predictions: 0,
          accuracy_percent: 0.0,
          total_profit_loss: 0.0,
          roi_percent: 0.0,
          average_confidence: 0.0
        },
        by_outcome: {
          home: { total: 0, correct: 0, accuracy_percent: 0.0 },
          draw: { total: 0, correct: 0, accuracy_percent: 0.0 },
          away: { total: 0, correct: 0, accuracy_percent: 0.0 }
        },
        by_confidence_level: {
          high: { total: 0, correct: 0, accuracy_percent: 0.0, roi_percent: 0.0 },
          medium: { total: 0, correct: 0, accuracy_percent: 0.0, roi_percent: 0.0 },
          low: { total: 0, correct: 0, accuracy_percent: 0.0, roi_percent: 0.0 }
        },
        by_league: [],
        recent_predictions: []
      },
      message: 'No data available yet. Predictions will be tracked starting soon.',
      timestamp: new Date().toISOString()
    })
  }
}

