"use client";

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { usePredictions } from "@/hooks/usePredictions";
import { Loader2, AlertCircle, RefreshCw, TrendingUp, Search, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Dynamic imports to avoid SSR issues
const TopPickCard = dynamic(() => import("@/components/TopPickCard"), {
  loading: () => <div className="animate-pulse bg-gray-200 rounded-xl h-96"></div>,
  ssr: false
});

const ExploreMatch = dynamic(() => import("@/components/ExploreMatch"), {
  loading: () => <div className="animate-pulse bg-gray-200 rounded-lg h-96"></div>,
  ssr: false
});

type TabType = 'picks' | 'explore';

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('picks');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { data: predictions, isLoading, error, refetch } = usePredictions();

  // Enhanced refresh handler with loading state
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      console.log("🔄 User clicked refresh button");
      await refetch();
      console.log("✅ Refresh completed successfully");
    } catch (error) {
      console.error("❌ Refresh failed:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Debug logging for predictions data
  useEffect(() => {
    console.log("🔍 Dashboard data state:", {
      predictions: predictions,
      isLoading: isLoading,
      error: error,
      predictionsLength: predictions?.length || 0
    });
    
    if (predictions && predictions.length > 0) {
      console.log("📊 Live predictions in dashboard:", predictions);
      console.log("🎯 Sample prediction structure:", predictions[0]);
    }
  }, [predictions, isLoading, error]);

  const topPicks = predictions || []; // Show all predictions (backend returns max 10 high-quality ones)

  const tabs = [
    {
      id: 'picks' as TabType,
      label: 'Top Smart Picks',
      icon: TrendingUp,
      description: 'AI-recommended bets'
    },
    {
      id: 'explore' as TabType,
      label: 'Explore Any Match',
      icon: Search,
      description: 'Custom predictions'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-4 sm:py-6 gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-2 sm:gap-3">
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-1.5 sm:p-2 rounded-lg">
                  <Star className="h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                SmartBet Co-Pilot
              </h1>
              <p className="text-sm sm:text-base text-gray-600 mt-1">Elite betting intelligence at your fingertips</p>
              
              {/* Connection Status Indicator */}
              <div className="mt-2 flex items-center gap-2">
                {isLoading ? (
                  <div className="flex items-center gap-1 text-xs text-yellow-600">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                    Connecting to live data...
                  </div>
                ) : error ? (
                  <div className="flex items-center gap-1 text-xs text-red-600">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    Offline - Using cached data
                  </div>
                ) : predictions && predictions.length > 0 ? (
                  <div className="flex items-center gap-1 text-xs text-green-600">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    Live data from Django backend ({predictions.length} predictions)
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-xs text-gray-600">
                    <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                    No predictions available
                  </div>
                )}
              </div>
            </div>
            <Button 
              onClick={handleRefresh} 
              variant="outline" 
              size="sm"
              className="self-start sm:self-auto"
              disabled={isRefreshing || isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              {isRefreshing ? 'Refreshing...' : 'Refresh Data'}
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
        {/* Tabs */}
        <div className="mb-6 sm:mb-8">
          <nav className="flex flex-col sm:flex-row sm:space-x-8 space-y-2 sm:space-y-0" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center gap-3 py-3 sm:py-4 px-3 sm:px-1 rounded-lg sm:rounded-none sm:border-b-2 font-medium text-sm transition-colors duration-200 text-left",
                    activeTab === tab.id
                      ? "bg-blue-50 text-blue-600 sm:bg-transparent sm:border-blue-500"
                      : "bg-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50 sm:hover:bg-transparent sm:border-transparent sm:hover:border-gray-300"
                  )}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  <div className="text-left">
                    <div className="font-semibold">{tab.label}</div>
                    <div className="text-xs text-gray-500">{tab.description}</div>
                  </div>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'picks' && (
          <div className="space-y-6 sm:space-y-8">
            {/* Top Smart Picks Section */}
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 sm:mb-6 gap-4">
                <div>
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2 sm:gap-3">
                    <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 text-blue-600" />
                    Top Smart Picks – Recommended Bets
                  </h2>
                  <p className="text-sm sm:text-base text-gray-600 mt-1">
                    Our AI has identified the best betting opportunities for you
                  </p>
                </div>
              </div>

              {isLoading ? (
                <div className="flex items-center justify-center py-8 sm:py-12">
                  <div className="text-center">
                    <Loader2 className="h-6 w-6 sm:h-8 sm:w-8 animate-spin text-blue-600 mx-auto mb-3 sm:mb-4" />
                    <p className="text-base sm:text-lg text-gray-600">Analyzing matches...</p>
                    <p className="text-xs sm:text-sm text-gray-500">Finding the best betting opportunities</p>
                  </div>
                </div>
              ) : error ? (
                <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8">
                  <div className="text-center">
                    <AlertCircle className="h-8 w-8 sm:h-12 sm:w-12 text-red-500 mx-auto mb-3 sm:mb-4" />
                    <h3 className="text-base sm:text-lg font-semibold text-red-600 mb-2">
                      Failed to load predictions
                    </h3>
                    <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-6">
                      {error instanceof Error ? error.message : 'Unable to connect to backend'}
                    </p>
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 text-left">
                      <h4 className="font-semibold text-red-800 mb-2">Debug Information:</h4>
                      <p className="text-sm text-red-700">
                        ✅ Attempting to connect to: <code className="bg-red-100 px-1 rounded">http://localhost:8000/api/predictions/</code>
                      </p>
                      <p className="text-sm text-red-700 mt-1">
                        ❓ Make sure Django server is running: <code className="bg-red-100 px-1 rounded">python manage.py runserver</code>
                      </p>
                      <p className="text-sm text-red-700 mt-1">
                        🔍 Check browser console for detailed error logs
                      </p>
                    </div>
                    <Button onClick={handleRefresh} variant="outline" disabled={isRefreshing}>
                      <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                      {isRefreshing ? 'Refreshing...' : 'Try Again'}
                    </Button>
                  </div>
                </div>
              ) : topPicks.length > 0 ? (
                <div className="grid gap-4 sm:gap-6 md:grid-cols-2 xl:grid-cols-3">
                  {topPicks.map((prediction, index) => (
                    <TopPickCard 
                      key={prediction.id} 
                      prediction={prediction} 
                      rank={index + 1} 
                    />
                  ))}
                </div>
              ) : (
                <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8">
                  <div className="text-center">
                    <TrendingUp className="h-8 w-8 sm:h-12 sm:w-12 text-gray-400 mx-auto mb-3 sm:mb-4" />
                    <h3 className="text-base sm:text-lg font-semibold text-gray-600 mb-2">
                      No predictions available
                    </h3>
                    <p className="text-sm sm:text-base text-gray-500">
                      Check back later for new betting opportunities.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'explore' && (
          <div className="space-y-6 sm:space-y-8">
            {/* Explore Any Match Section */}
            <div>
              <div className="mb-4 sm:mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2 sm:gap-3">
                  <Search className="h-5 w-5 sm:h-6 sm:w-6 text-blue-600" />
                  Explore Your Own Match
                </h2>
                <p className="text-sm sm:text-base text-gray-600 mt-1">
                  Get custom predictions for any match and betting market
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-4 sm:p-6 lg:p-8">
                <ExploreMatch />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 