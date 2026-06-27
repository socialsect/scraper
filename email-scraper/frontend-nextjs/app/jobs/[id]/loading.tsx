export default function Loading() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="h-9 w-96 bg-zinc-800 rounded animate-pulse mb-2"></div>
          <div className="h-6 w-64 bg-zinc-800 rounded animate-pulse"></div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
            <div className="h-4 w-24 bg-zinc-800 rounded animate-pulse mb-2"></div>
            <div className="h-9 w-20 bg-zinc-800 rounded animate-pulse"></div>
          </div>
        ))}
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 mb-8">
        <div className="h-16 border-b border-zinc-800 bg-zinc-800/50 animate-pulse"></div>
        <div className="h-96 p-4 space-y-2">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="h-4 bg-zinc-800 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    </div>
  )
}
