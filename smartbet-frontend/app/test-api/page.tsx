'use client'

import { useEffect, useState } from 'react'

export default function TestAPI() {
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    console.log('🔍 Testing API connection...')
    
    fetch('/api/django/recommendations/')
      .then(res => {
        console.log('✅ Response received:', res.status)
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`)
        }
        return res.json()
      })
      .then(data => {
        console.log('✅ Data parsed:', data)
        setResult(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('❌ Error:', err)
        setError(err.message)
        setLoading(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">API Connection Test</h1>
        
        {loading && (
          <div className="bg-blue-100 border border-blue-400 rounded-lg p-4">
            <p className="text-blue-800">⏳ Loading...</p>
          </div>
        )}
        
        {error && (
          <div className="bg-red-100 border border-red-400 rounded-lg p-4">
            <h2 className="text-xl font-bold text-red-800 mb-2">❌ Error</h2>
            <p className="text-red-700">{error}</p>
          </div>
        )}
        
        {result && (
          <div className="bg-green-100 border border-green-400 rounded-lg p-4">
            <h2 className="text-xl font-bold text-green-800 mb-2">✅ Success!</h2>
            <div className="text-green-700">
              <p><strong>Success:</strong> {result.success ? 'Yes' : 'No'}</p>
              <p><strong>Count:</strong> {result.count}</p>
              <p><strong>Data items:</strong> {result.data?.length || 0}</p>
              {result.data && result.data.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-semibold mb-2">First Recommendation:</h3>
                  <pre className="bg-white p-2 rounded text-xs overflow-auto max-h-96">
                    {JSON.stringify(result.data[0], null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

