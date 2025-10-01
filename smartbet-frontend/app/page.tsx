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
import { leagues } from '@/lib/mockData'
import RecommendationCard from './components/RecommendationCard'
import EmptyState from './components/EmptyState'
import RecommendationSkeleton from './components/RecommendationSkeleton'
import { Recommendation } from '../src/types/recommendation'
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function HomePage() {
  const [selectedLeague, setSelectedLeague] = useState('')
  const router = useRouter()

  // Fetch recommendations with SWR
  const { data, error, isLoading, mutate } = useSWR('/api/recommendations', fetcher, {
    refreshInterval: 60000, // Refresh every 60 seconds
    revalidateOnFocus: true,
  })

  const handleExplorePredictions = () => {
    if (selectedLeague) {
      router.push(`/predictions?league=${selectedLeague}`)
    } else {
      router.push('/predictions')
    }
  }

  const handleViewDetails = (fixtureId: number) => {
    router.push(`/predictions?fixture=${fixtureId}`)
  }

  const handleBrowseAll = () => {
    router.push('/predictions')
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
          </div>
          
          <p className="text-xl md:text-2xl text-gray-600 mb-12 max-w-4xl mx-auto leading-relaxed">
            Get data-driven insights and betting recommendations with confidence scores, 
            expected value analysis, and real-time market intelligence across top European leagues.
          </p>

          {/* Performance Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12 max-w-4xl mx-auto">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-primary-600 mb-1">74.4%</div>
              <div className="text-sm text-gray-600">Hit Rate</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-green-600 mb-1">138.9%</div>
              <div className="text-sm text-gray-600">ROI</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-blue-600 mb-1">5</div>
              <div className="text-sm text-gray-600">Leagues</div>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 shadow-lg border border-white/20">
              <div className="text-2xl font-bold text-purple-600 mb-1">24/7</div>
              <div className="text-sm text-gray-600">Updates</div>
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
                <RecommendationSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <div className="bg-gradient-to-r from-red-50 to-pink-50 border border-red-200 rounded-2xl p-8 text-center">
              <div className="bg-white rounded-full p-4 w-16 h-16 mx-auto mb-6 shadow-lg">
                <AlertCircle className="h-8 w-8 text-red-500" />
              </div>
              <h3 className="text-xl font-semibold text-red-900 mb-3">
                Unable to Load Recommendations
              </h3>
              <p className="text-red-700 mb-6 max-w-md mx-auto">
                We're experiencing some technical difficulties. Please try again in a moment.
              </p>
              <button
                onClick={handleRetry}
                className="bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-xl transition-colors inline-flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Try Again
              </button>
            </div>
          )}

          {data && data.recommendations && data.recommendations.length > 0 && (
            <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
              {data.recommendations.map((recommendation: Recommendation) => (
                <RecommendationCard
                  key={recommendation.fixture_id}
                  recommendation={recommendation}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          )}

          {data && data.recommendations && data.recommendations.length === 0 && (
            <EmptyState onBrowseAll={handleBrowseAll} onRetry={handleRetry} />
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
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {leagues.map((league) => (
              <button
                key={league.id}
                onClick={() => setSelectedLeague(league.name)}
                className={`group p-6 rounded-2xl border-2 transition-all duration-300 hover:scale-105 ${
                  selectedLeague === league.name
                    ? 'border-primary-500 bg-gradient-to-br from-primary-50 to-blue-50 shadow-lg'
                    : 'border-gray-200 hover:border-primary-300 hover:bg-white/80 hover:shadow-lg'
                }`}
              >
                <div className="text-center">
                  <div className="text-3xl mb-3 group-hover:scale-110 transition-transform">
                    {league.flag}
                  </div>
                  <div className="font-semibold text-gray-900 mb-1">{league.name}</div>
                  <div className="text-sm text-gray-500 mb-3">{league.country}</div>
                  <div className={`text-xs px-3 py-1 rounded-full font-medium ${
                    league.status === 'PRODUCTION' 
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
              <span>5 Leagues Live</span>
            </span>
            <span>SportMonks Predictions</span>
            <span>60s Refresh Rate</span>
            <span>24/7 Monitoring</span>
          </div>
        </div>
      </div>
    </div>
  )
} 