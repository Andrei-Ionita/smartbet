export default function RecommendationSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-16 bg-gray-200 rounded"></div>
            <div className="h-4 w-24 bg-gray-200 rounded"></div>
          </div>
          <div className="h-6 w-48 bg-gray-200 rounded mb-2"></div>
        </div>
        <div className="h-8 w-8 bg-gray-200 rounded-full"></div>
      </div>

      {/* Prediction bar */}
      <div className="mb-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="h-4 w-12 bg-gray-200 rounded"></div>
          <div className="flex-1 h-2 bg-gray-200 rounded-full"></div>
          <div className="h-4 w-8 bg-gray-200 rounded"></div>
        </div>
        <div className="h-6 w-20 bg-gray-200 rounded mb-3"></div>
      </div>

      {/* Explanation */}
      <div className="space-y-2 mb-4">
        <div className="h-4 w-full bg-gray-200 rounded"></div>
        <div className="h-4 w-3/4 bg-gray-200 rounded"></div>
      </div>

      {/* Actions */}
      <div className="flex justify-between items-center">
        <div className="h-4 w-24 bg-gray-200 rounded"></div>
        <div className="h-4 w-16 bg-gray-200 rounded"></div>
      </div>
    </div>
  )
}
