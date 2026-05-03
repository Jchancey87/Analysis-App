import HeatMap from '@/components/HeatMap'
import ResearchPanel from '@/components/ResearchPanel'
import { getHeatmap, getArchetypes } from '@/lib/api'

export const dynamic = 'force-dynamic'

export default async function DashboardPage() {
  let heatmapSpec = null
  let archetypes: any[] = []

  try { heatmapSpec = await getHeatmap() }      catch { /* no data yet */ }
  try { archetypes  = await getArchetypes() }   catch { /* no data yet */ }

  const today = new Date().toISOString().split('T')[0]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Float × RVOL performance heatmap + post-close research</p>
      </div>

      {/* Research panel — full width, has its own internal two-col layout */}
      <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-5">Groq Research</h2>
        <ResearchPanel defaultDate={today} />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Archetype stats */}
        <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">Archetype Stats</h2>
          {archetypes.length === 0 ? (
            <p className="text-gray-500 text-sm">No chart captures yet. Upload your first chart to see patterns.</p>
          ) : (
            <div className="space-y-2">
              {archetypes.map((a: any) => (
                <div key={a.tag} className="flex items-center justify-between bg-gray-800/60 rounded-lg px-3 py-2">
                  <span className="text-sm font-medium text-gray-200">{a.tag}</span>
                  <div className="flex gap-4 text-xs text-gray-400">
                    <span>n={a.count}</span>
                    {a.avg_gap_pct   != null && <span className="text-emerald-400">+{a.avg_gap_pct}%</span>}
                    {a.avg_cleanliness != null && <span>⭐ {a.avg_cleanliness}/10</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Heatmap */}
        <section className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">Float × RVOL Heatmap</h2>
          <HeatMap spec={heatmapSpec} />
        </section>
      </div>

    </div>
  )
}
