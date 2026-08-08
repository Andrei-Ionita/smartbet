/**
 * Route-level loading state for /prediction/[...slug].
 *
 * This page is a server component that fetches fixture detail from the data
 * provider before it can render anything, which takes seconds. Without a
 * loading boundary the browser sat on the previous page with no feedback, so
 * a public reviewer (2026-08-08) reported that "View full match analysis"
 * did nothing when clicked — the navigation had in fact started. The
 * neighbouring "View Analysis" control felt fine only because it is a local
 * expand toggle.
 */
export default function Loading() {
  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-4xl animate-pulse">
        <div className="mb-6 h-4 w-64 rounded bg-gray-200" />

        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 h-10 w-3/4 rounded bg-gray-200" />
          <div className="flex flex-wrap justify-center gap-4">
            <div className="h-9 w-36 rounded-full bg-gray-200" />
            <div className="h-9 w-44 rounded-full bg-gray-200" />
            <div className="h-9 w-40 rounded-full bg-gray-200" />
          </div>
        </div>

        <div className="mb-12 h-96 rounded-2xl border border-gray-200 bg-white" />

        <div className="grid gap-8 md:grid-cols-2">
          <div className="h-48 rounded-2xl border border-gray-200 bg-white" />
          <div className="h-48 rounded-2xl border border-gray-200 bg-white" />
        </div>

        <p className="mt-8 text-center text-sm text-gray-500">
          Loading fixture detail…
        </p>
      </div>
    </div>
  )
}
