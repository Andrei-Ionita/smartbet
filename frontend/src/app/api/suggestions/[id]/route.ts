import { NextResponse } from 'next/server';

// GET function to return a single suggestion by ID
export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const id = params.id;
    
    // Build the backend URL
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const apiUrl = `${backendUrl}/api/suggestions/${id}/`;
    
    // Fetch data from the backend
    const response = await fetch(apiUrl, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Disable caching to always get fresh data
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ message: 'Suggestion not found' }, { status: 404 });
      }
      throw new Error(`Backend responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching suggestion details from backend:', error);
    
    // Return a more helpful error message
    return NextResponse.json(
      { 
        error: 'Failed to fetch suggestion details from backend',
        message: error instanceof Error ? error.message : 'Unknown error'
      }, 
      { status: 500 }
    );
  }
} 