import { NextResponse } from 'next/server';
import { BettingSuggestion } from '@/types';

// Export mockSuggestions only for testing
export const mockSuggestions: BettingSuggestion[] = [];

// GET function to return all suggestions and optionally filter by confidence level
export async function GET(request: Request) {
  try {
    // Get URL parameters
    const { searchParams } = new URL(request.url);
    const confidenceFilter = searchParams.get('confidence');
    const leagueFilter = searchParams.get('league');

    // Build the backend URL with query parameters
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    let apiUrl = `${backendUrl}/api/suggestions/`;
    
    // Create a new URLSearchParams object for backend query
    const params = new URLSearchParams();
    
    if (confidenceFilter && confidenceFilter !== 'All') {
      params.append('confidence', confidenceFilter);
    }
    
    if (leagueFilter && leagueFilter !== 'All') {
      params.append('league', leagueFilter);
    }
    
    // Add params to URL if any exist
    if (params.toString()) {
      apiUrl += `?${params.toString()}`;
    }
    
    // Fetch data from the backend
    const response = await fetch(apiUrl, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Disable caching to always get fresh data
    });
    
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching suggestions from backend:', error);
    
    // Return a more helpful error message
    return NextResponse.json(
      { 
        error: 'Failed to fetch suggestions from backend',
        message: error instanceof Error ? error.message : 'Unknown error'
      }, 
      { status: 500 }
    );
  }
} 