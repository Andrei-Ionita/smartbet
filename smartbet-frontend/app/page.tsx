'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Trophy,
  TrendingUp,
  Shield,
  Zap,
  AlertCircle,
  RefreshCw,
  Star,
  Users,
  Target,
  BarChart3,
  Clock,
  CheckCircle,
  ArrowRight,
  Sparkles
} from 'lucide-react'
import RecommendationCard from './components/RecommendationCard'
import EmptyState from './components/EmptyState'
import RecommendationSkeleton from './components/RecommendationSkeleton'
import RecommendationCardSkeleton from './components/RecommendationCardSkeleton'
import LoadingSpinner from './components/LoadingSpinner'
import ErrorBoundary from './components/ErrorBoundary'
import RetryButton from './components/RetryButton'
import { Recommendation } from '../src/types/recommendation'
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function HomePage() {
  const [selectedLeague, setSelectedLeague] = useState('')
  const router = useRouter()

  // Get session_id from localStorage for personalized recommendations
  const getSessionId = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('smartbet_session_id') || ''
    }
    return ''
  }

  // Enhanced fetcher with error handling
  const enhancedFetcher = async (url: string) => {
    try {
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    } catch (error) {
      console.error('Fetch error:', error)
      throw error
    }
  }

  // Build API URL with session_id for personalized stake recommendations
  const sessionId = getSessionId()
  const apiUrl = sessionId
    ? `/api/recommendations/?session_id=${sessionId}`
    : '/api/recommendations/'

  // Fetch recommendations with SWR - using Django backend
  const { data, error, isLoading, mutate } = useSWR(apiUrl, enhancedFetcher, {
    refreshInterval: 60000, // Refresh every 60 seconds
    revalidateOnFocus: true,
    errorRetryCount: 3,
    errorRetryInterval: 2000,
    shouldRetryOnError: true,
  })

  // Fetch performance stats for live accuracy badge
  const { data: performanceData } = useSWR('/api/performance', fetcher, {
    refreshInterval: 120000, // Refresh every 2 minutes
  })

  const handleExplorePredictions = () => {
    router.push('/explore')
  }

  const handleViewDetails = (fixtureId: number) => {
    router.push(`/explore?fixture=${fixtureId}`)
  }

  const handleBrowseAll = () => {
    router.push('/explore')
  }

  const handleRetry = () => {
    mutate()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Modern Hero Section */}
        <div className="text-center mb-16">
          <div className="relative inline-block mb-8">
            <div className="absolute -inset-4 bg-gradient-to-r from-primary-500 to-blue-600 rounded-full blur opacity-20"></div>
            <div className="relative bg-white p-6 rounded-full shadow-xl">
              <Trophy className="h-16 w-16 text-primary-600" />
            </div>
          </div>

          <div className="space-y-4 mb-8">
            <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-gray-900 via-primary-600 to-blue-600 bg-clip-text text-transparent">
              SmartBet
            </h1>
            <div className="flex items-center justify-center gap-2 text-primary-600 font-medium">
              <Sparkles className="h-5 w-5" />
              <span>AI-Powered Football Predictions</span>
            </div>
            {/* Live Accuracy Badge */}
            {performanceData?.data?.overall?.total_predictions > 0 && (
              <div
                onClick={() => router.push('/track-record')}
                className="inline-flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer hover:scale-105"
              >
                <Shield className="h-5 w-5" />
                <div className="text-left">
                  <div className="text-sm font-medium opacity-90">Verified Smart Picks</div>
                  <div className="text-lg font-bold">
                    {performanceData.data.overall.accuracy_percent}% Accuracy
                    <span className="text-sm font-normal opacity-90 ml-2 block text-xs">
                      (&gt;60% confidence models)
                    </span>
                  </div>
                </div>
                <ArrowRight className="h-5 w-5" />
              </div>
            )}
          </div>

          <p className="text-xl md:text-2xl text-gray-600 mb-12 max-w-4xl mx-auto leading-relaxed">
            Get data-driven insights and betting recommendations with confidence scores,
            expected value analysis, and real-time market intelligence across top European leagues.
          </p>

          {/* Performance Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12 max-w-4xl mx-auto">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-primary-600 mb-1">55%+</div>
              <div className="text-sm text-gray-600">Confidence Threshold</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-green-600 mb-1">27</div>
              <div className="text-sm text-gray-600">Leagues Covered</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-blue-600 mb-1">14</div>
              <div className="text-sm text-gray-600">Days Ahead</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-purple-600 mb-1">3</div>
              <div className="text-sm text-gray-600">AI Ensemble</div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={handleExplorePredictions}
              className="group bg-gradient-to-r from-primary-600 to-blue-600 hover:from-primary-700 hover:to-blue-700 text-white font-semibold py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
            >
              <span className="flex items-center gap-2">
                Explore Predictions
                <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
            <button
              onClick={() => router.push('/track-record')}
              className="group bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
            >
              <span className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Track Record
              </span>
            </button>
            <button
              onClick={() => router.push('/about')}
              className="bg-white/80 backdrop-blur-sm hover:bg-white text-gray-700 font-semibold py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-200"
            >
              Learn More
            </button>
          </div>
        </div>

        {/* Featured Recommendations Section */}
        <div className="mb-16">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-primary-100 text-primary-700 px-4 py-2 rounded-full text-sm font-medium mb-4">
              <Star className="h-4 w-4" />
              <span>Featured Picks</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Today's Top Recommendations
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Hand-picked predictions with the highest confidence scores and expected value
            </p>
          </div>

          {isLoading && (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <RecommendationCardSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <ErrorBoundary>
              <div className="bg-gradient-to-r from-red-50 to-pink-50 border border-red-200 rounded-2xl p-8 text-center">
                <div className="bg-white rounded-full p-4 w-16 h-16 mx-auto mb-6 shadow-lg">
                  <AlertCircle className="h-8 w-8 text-red-500" />
                </div>
                <h3 className="text-xl font-semibold text-red-900 mb-3">
                  Unable to Load Recommendations
                </h3>
                <p className="text-red-700 mb-6 max-w-md mx-auto">
                  {error.message.includes('HTTP')
                    ? `Server error: ${error.message}`
                    : 'We\'re experiencing some technical difficulties. Please try again in a moment.'}
                </p>
                <RetryButton
                  onRetry={handleRetry}
                  text="Try Again"
                  className="bg-red-600 hover:bg-red-700"
                />
              </div>
            </ErrorBoundary>
          )}

          {data && data.recommendations && data.recommendations.length > 0 && (
            <>
              {/* Transparency Notice */}
              <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-lg">
                <p className="text-sm text-center text-blue-900">
                  🔍 <strong>100% Transparent:</strong> These recommendations are logged & tracked on our{' '}
                  <a href="/track-record" className="underline font-semibold hover:text-blue-700">public track record</a>
                  {' '}• All predictions timestamped before kickoff • Real results verified via SportMonks API
                </p>
              </div>

              {/* Stats Summary */}
              <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-2xl p-6 mb-8 border border-primary-200">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-primary-600">{data.recommendations.length}</div>
                    <div className="text-sm text-primary-700">Top Picks Today</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-green-600">{data.confidence_threshold}%+</div>
                    <div className="text-sm text-green-700">Confidence Threshold</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-blue-600">{data.fixtures_analyzed || 0}</div>
                    <div className="text-sm text-blue-700">Total Fixtures</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-purple-600">
                      {data.recommendations.length > 0
                        ? (Math.max(...data.recommendations.map((r: any) => r.confidence)) * 100).toFixed(0) + '%'
                        : '0%'}
                    </div>
                    <div className="text-sm text-purple-700">Highest Confidence</div>
                  </div>
                </div>
              </div>

              {/* Recommendations Grid */}
              <div className="grid gap-4 sm:gap-6 grid-cols-1 lg:grid-cols-2">
                {data.recommendations.map((recommendation: Recommendation) => (
                  <RecommendationCard
                    key={recommendation.fixture_id}
                    recommendation={recommendation}
                    onViewDetails={handleViewDetails}
                  />
                ))}
              </div>

              {/* League Diversity Info */}
              {data.debug_info?.top_5_predictions && (
                <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl p-6 mt-8 border border-gray-200">
                  <h3 className="text-lg font-bold text-gray-900 mb-4 text-center">League Coverage</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {data.debug_info.top_5_predictions.map((prediction: any, index: number) => (
                      <div key={index} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                        <div className="text-sm font-medium text-gray-600 mb-1">{prediction.league}</div>
                        <div className="text-sm text-gray-500 truncate">{prediction.match}</div>
                        <div className="text-xs text-primary-600 font-semibold mt-1">
                          {Math.round(prediction.confidence)}% confidence
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* View All Button */}
              <div className="text-center mt-8">
                <button
                  onClick={handleBrowseAll}
                  className="bg-gradient-to-r from-primary-600 to-blue-600 hover:from-primary-700 hover:to-blue-700 text-white font-semibold py-3 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
                >
                  View All Predictions
                </button>
              </div>
            </>
          )}

          {data && data.recommendations && data.recommendations.length === 0 && (
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-8 text-center">
              <div className="bg-white rounded-full p-4 w-16 h-16 mx-auto mb-6 shadow-lg">
                <AlertCircle className="h-8 w-8 text-amber-500" />
              </div>
              <h3 className="text-xl font-semibold text-amber-900 mb-3">
                {data.status === 'no_predictions_available'
                  ? 'AI Predictions Not Available'
                  : data.status === 'no_fixtures_found'
                    ? 'No Upcoming Fixtures'
                    : 'No Top Quality Bets Available'}
              </h3>
              <p className="text-amber-700 mb-6 max-w-md mx-auto">
                {data.status_details || 'We\'re working to bring you the best predictions. Please check back soon.'}
              </p>
              {data.status === 'no_predictions_available' && (
                <div className="bg-amber-100 rounded-lg p-4 mb-6 text-left">
                  <p className="text-sm text-amber-800 font-medium mb-2">Possible Solutions:</p>
                  <ul className="text-sm text-amber-700 space-y-1">
                    <li>• Enable the Predictions Addon in your SportMonks account</li>
                    <li>• Upgrade your SportMonks subscription plan</li>
                    <li>• Contact SportMonks support for assistance</li>
                  </ul>
                </div>
              )}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={handleRetry}
                  className="bg-amber-600 hover:bg-amber-700 text-white font-semibold py-3 px-6 rounded-xl transition-colors inline-flex items-center gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </button>
                <button
                  onClick={handleBrowseAll}
                  className="bg-white hover:bg-gray-50 text-amber-700 font-semibold py-3 px-6 rounded-xl transition-colors border border-amber-200"
                >
                  View All Fixtures
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Features Section */}
        <div className="mb-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Why Choose SmartBet?
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Our advanced AI system combines machine learning with real-time market data to deliver superior predictions
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="group bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-white/20 hover:-translate-y-1">
              <div className="bg-gradient-to-br from-primary-500 to-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <TrendingUp className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Data-Driven Intelligence</h3>
              <p className="text-gray-600 leading-relaxed">
                Advanced ML models trained on millions of historical matches with real-time market analysis and player statistics
              </p>
            </div>

            <div className="group bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-white/20 hover:-translate-y-1">
              <div className="bg-gradient-to-br from-green-500 to-emerald-600 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Shield className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Smart Risk Management</h3>
              <p className="text-gray-600 leading-relaxed">
                Confidence thresholds and expected value calculations help you make informed decisions with proper bankroll management
              </p>
            </div>

            <div className="group bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 border border-white/20 hover:-translate-y-1">
              <div className="bg-gradient-to-br from-purple-500 to-pink-600 w-16 h-16 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Zap className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Real-Time Updates</h3>
              <p className="text-gray-600 leading-relaxed">
                Live predictions with SHAP explanations, feature importance breakdown, and instant market updates
              </p>
            </div>
          </div>
        </div>

        {/* League Selector */}
        <div className="mb-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Choose Your League
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Select from our supported European leagues to get tailored predictions
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {[
              { id: 'premier-league', name: 'Premier League', country: 'England', status: 'PRODUCTION' },
              { id: 'la-liga', name: 'La Liga', country: 'Spain', status: 'PRODUCTION' },
              { id: 'bundesliga', name: 'Bundesliga', country: 'Germany', status: 'PRODUCTION' },
              { id: 'serie-a', name: 'Serie A', country: 'Italy', status: 'PRODUCTION' },
              { id: 'ligue-1', name: 'Ligue 1', country: 'France', status: 'PRODUCTION' },
              { id: 'championship', name: 'Championship', country: 'England', status: 'PRODUCTION' },
              { id: 'fa-cup', name: 'FA Cup', country: 'England', status: 'PRODUCTION' },
              { id: 'carabao-cup', name: 'Carabao Cup', country: 'England', status: 'PRODUCTION' },
              { id: 'eredivisie', name: 'Eredivisie', country: 'Netherlands', status: 'PRODUCTION' },
              { id: 'admiral-bundesliga', name: 'Admiral Bundesliga', country: 'Austria', status: 'PRODUCTION' },
              { id: 'pro-league', name: 'Pro League', country: 'Belgium', status: 'PRODUCTION' },
              { id: '1-hnl', name: '1. HNL', country: 'Croatia', status: 'PRODUCTION' },
              { id: 'superliga', name: 'Superliga', country: 'Denmark', status: 'PRODUCTION' },
              { id: 'serie-b', name: 'Serie B', country: 'Italy', status: 'PRODUCTION' },
              { id: 'coppa-italia', name: 'Coppa Italia', country: 'Italy', status: 'PRODUCTION' },
              { id: 'eliteserien', name: 'Eliteserien', country: 'Norway', status: 'PRODUCTION' },
              { id: 'ekstraklasa', name: 'Ekstraklasa', country: 'Poland', status: 'PRODUCTION' },
              { id: 'liga-portugal', name: 'Liga Portugal', country: 'Portugal', status: 'PRODUCTION' },
              { id: 'premier-league-ro', name: 'Premier League', country: 'Romania', status: 'PRODUCTION' },
              { id: 'premiership', name: 'Premiership', country: 'Scotland', status: 'PRODUCTION' },
              { id: 'la-liga-2', name: 'La Liga 2', country: 'Spain', status: 'PRODUCTION' },
              { id: 'copa-del-rey', name: 'Copa Del Rey', country: 'Spain', status: 'PRODUCTION' },
              { id: 'allsvenskan', name: 'Allsvenskan', country: 'Sweden', status: 'PRODUCTION' },
              { id: 'super-league', name: 'Super League', country: 'Switzerland', status: 'PRODUCTION' },
              { id: 'super-lig', name: 'Super Lig', country: 'Turkey', status: 'PRODUCTION' },
              { id: 'premier-league-additional', name: 'Premier League', country: 'Additional', status: 'PRODUCTION' },
              { id: 'uefa-europa-league', name: 'UEFA Europa League', country: 'Europe', status: 'PRODUCTION' }
            ].map((league) => (
              <button
                key={league.id}
                onClick={() => setSelectedLeague(league.name)}
                className={`group p-6 rounded-2xl border-2 transition-all duration-300 hover:scale-105 ${selectedLeague === league.name
                  ? 'border-primary-500 bg-gradient-to-br from-primary-50 to-blue-50 shadow-lg'
                  : 'border-gray-200 hover:border-primary-300 hover:bg-white/80 hover:shadow-lg'
                  }`}
              >
                <div className="text-center">
                  <div className="font-semibold text-gray-900 mb-1">{league.name}</div>
                  <div className="text-sm text-gray-500 mb-3">{league.country}</div>
                  <div className={`text-xs px-3 py-1 rounded-full font-medium ${league.status === 'PRODUCTION'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-yellow-100 text-yellow-700'
                    }`}>
                    {league.status}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* How It Works */}
        <div className="mb-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              How We Pick Recommendations
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Our AI analyzes multiple data points to deliver the most accurate predictions
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <BarChart3 className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Data Analysis</h3>
              <p className="text-gray-600">
                Confidence scores from SportMonks Predictions API with advanced ML models
              </p>
            </div>

            <div className="text-center">
              <div className="bg-gradient-to-br from-green-500 to-teal-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Target className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Value Assessment</h3>
              <p className="text-gray-600">
                Expected value calculations when odds are available for optimal betting decisions
              </p>
            </div>

            <div className="text-center">
              <div className="bg-gradient-to-br from-orange-500 to-red-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Quality Filter</h3>
              <p className="text-gray-600">
                Only top European leagues with verified data sources and proven accuracy
              </p>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center mb-16">
          <div className="bg-gradient-to-r from-primary-600 to-blue-600 rounded-3xl p-12 text-white">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to Start Winning?
            </h2>
            <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
              Join thousands of users who trust SmartBet for their football predictions
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={handleExplorePredictions}
                className="bg-white text-primary-600 font-semibold py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
              >
                <span className="flex items-center gap-2">
                  Explore Predictions
                  <ArrowRight className="h-5 w-5" />
                </span>
              </button>
              {selectedLeague && (
                <div className="text-sm opacity-75">
                  Showing predictions for {selectedLeague}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Transparency Section */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg border border-white/20 mb-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">Transparency & Trust</h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-blue-100 w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Clock className="h-6 w-6 text-blue-600" />
              </div>
              <div className="font-semibold text-gray-900 mb-2">Live Predictions Only</div>
              <div className="text-sm text-gray-600">No backfilled performance data - all results are genuine</div>
            </div>
            <div className="text-center">
              <div className="bg-green-100 w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="h-6 w-6 text-green-600" />
              </div>
              <div className="font-semibold text-gray-900 mb-2">Accuracy Tracking</div>
              <div className="text-sm text-gray-600">We'll publish detailed accuracy reports once we have sufficient live outcomes</div>
            </div>
            <div className="text-center">
              <div className="bg-purple-100 w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Users className="h-6 w-6 text-purple-600" />
              </div>
              <div className="font-semibold text-gray-900 mb-2">Data Sources</div>
              <div className="text-sm text-gray-600">SportMonks Predictions API • Updates every 60 seconds</div>
            </div>
          </div>
        </div>

        {/* Footer Status */}
        <div className="text-center py-8 border-t border-gray-200">
          <div className="flex flex-wrap justify-center items-center gap-6 text-sm text-gray-500">
            <span className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>27 Leagues Covered</span>
            </span>
            <span>Consensus Ensemble</span>
            <span>3 AI Models</span>
            <span>60s Refresh Rate</span>
            <span>14-Day Window</span>
          </div>
        </div>
      </div>
    </div>
  )
}