'use client'

export default function RecommendationCardSkeleton() {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20 animate-pulse">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
        <div className="h-8 bg-gray-200 rounded-full w-20"></div>
      </div>

      {/* Prediction Section */}
      <div className="mb-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-6 bg-gray-200 rounded w-16"></div>
          <div className="h-4 bg-gray-200 rounded w-24"></div>
        </div>
        <div className="h-3 bg-gray-200 rounded w-full mb-1"></div>
        <div className="h-3 bg-gray-200 rounded w-2/3"></div>
      </div>

      {/* Badges */}
      <div className="flex gap-2 mb-4">
        <div className="h-6 bg-gray-200 rounded-full w-20"></div>
        <div className="h-6 bg-gray-200 rounded-full w-24"></div>
      </div>

      {/* Odds Section */}
      <div className="mb-4">
        <div className="h-4 bg-gray-200 rounded w-24 mb-3"></div>
        <div className="grid grid-cols-3 gap-3">
          <div className="h-16 bg-gray-200 rounded-xl"></div>
          <div className="h-16 bg-gray-200 rounded-xl"></div>
          <div className="h-16 bg-gray-200 rounded-xl"></div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-between items-center">
        <div className="h-10 bg-gray-200 rounded-lg w-24"></div>
        <div className="h-10 bg-gray-200 rounded-lg w-20"></div>
      </div>
    </div>
  )
}
