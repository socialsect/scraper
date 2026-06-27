export default function Loading() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="h-8 w-48 bg-zinc-800 rounded animate-pulse mb-8"></div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
            <div className="h-4 w-24 bg-zinc-800 rounded animate-pulse mb-2"></div>
            <div className="h-8 w-32 bg-zinc-800 rounded animate-pulse"></div>
          </div>
        ))}
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 mb-8">
        <div className="h-[300px] bg-zinc-800 rounded animate-pulse"></div>
      </div>
      
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <div className="h-6 w-32 bg-zinc-800 rounded animate-pulse mb-6"></div>
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-zinc-800 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    </div>
  )
}
