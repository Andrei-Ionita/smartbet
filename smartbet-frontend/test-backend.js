// Simple test script to verify backend connection
const fetch = require('node-fetch');

async function testBackend() {
  console.log('🚀 Testing Django backend connection...');
  
  try {
    const response = await fetch('http://localhost:8000/api/predictions/');
    
    if (!response.ok) {
      console.error('❌ HTTP Error:', response.status, response.statusText);
      return;
    }
    
    const data = await response.json();
    console.log('✅ Backend connection successful!');
    console.log('📊 Response structure:', {
      hasResults: !!data.results,
      resultsLength: data.results?.length || 0,
      keys: Object.keys(data)
    });
    
    if (data.results && data.results.length > 0) {
      console.log('🎯 Sample prediction structure:');
      console.log(JSON.stringify(data.results[0], null, 2));
    } else {
      console.log('⚠️  No predictions found in response');
    }
    
  } catch (error) {
    console.error('❌ Connection failed:', error.message);
    console.log('💡 Make sure Django server is running: python manage.py runserver');
  }
}

testBackend(); 