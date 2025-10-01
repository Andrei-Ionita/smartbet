import { NextRequest, NextResponse } from 'next/server';
import type { Feedback } from '@/types/feedback';

export async function POST(request: NextRequest) {
  try {
    const feedbackData: Feedback = await request.json();
    
    // Validate the feedback data
    if (!feedbackData.predictionId || typeof feedbackData.didBet !== 'boolean') {
      return NextResponse.json(
        { success: false, message: 'Invalid feedback data' },
        { status: 400 }
      );
    }

    // In a real application, you would save this to a database
    // For now, we'll just log it and return success
    console.log('Feedback received:', feedbackData);
    
    // Simulate some processing time
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return NextResponse.json({
      success: true,
      message: 'Feedback submitted successfully'
    });
    
  } catch (error) {
    console.error('Error processing feedback:', error);
    return NextResponse.json(
      { success: false, message: 'Internal server error' },
      { status: 500 }
    );
  }
} 