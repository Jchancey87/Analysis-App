'use client'
import dynamic from 'next/dynamic'

// Plotly must be client-side only (no SSR)
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false, loading: () => (
  <div className="flex items-center justify-center h-64 text-gray-500 text-sm">Loading heatmap…</div>
)})

interface Props {
  spec: { data: unknown[]; layout: Record<string, unknown> }
}

export default function HeatMap({ spec }: Props) {
  if (!spec?.data?.length) {
    return (
      <div className="flex items-center justify-center h-64 rounded-xl border border-gray-800 text-gray-500 text-sm">
        No heatmap data yet — run the ingestion job first.
      </div>
    )
  }

  return (
    <Plot
      data={spec.data as Plotly.Data[]}
      layout={{
        ...spec.layout,
        autosize: true,
        margin: { t: 40, b: 40, l: 60, r: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#e2e8f0', family: 'Inter, sans-serif' },
      }}
      config={{ responsive: true, displayModeBar: false }}
      style={{ width: '100%', height: '400px' }}
    />
  )
}
