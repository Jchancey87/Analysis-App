'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Plus } from 'lucide-react'
import { getCharts, ChartCapture, chartImageUrl } from '@/lib/api'
import { VALID_TAGS, PatternTag } from '@/lib/geminiPrompt'
import ChartUpload from '@/components/ChartUpload'

export default function ChartsPage() {
  const [charts, setCharts]       = useState<ChartCapture[]>([])
  const [loading, setLoading]     = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [filterTag, setFilterTag] = useState<string>('')
  const [filterTicker, setFilterTicker] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [minCleanliness, setMinCleanliness] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filterTicker)   params.ticker          = filterTicker.toUpperCase()
      if (filterTag)      params.tag             = filterTag
      if (dateFrom)       params.date_from       = dateFrom
      if (dateTo)         params.date_to         = dateTo
      if (minCleanliness) params.min_cleanliness = Number(minCleanliness)
      setCharts(await getCharts(params))
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Chart Journal</h1>
          <p className="text-gray-400 text-sm mt-1">{charts.length} captures</p>
        </div>
        <button onClick={() => setShowUpload(v => !v)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors">
          <Plus size={15} /> {showUpload ? 'Hide Upload' : 'Upload Chart'}
        </button>
      </div>

      {showUpload && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">Upload New Chart</h2>
          <ChartUpload onSuccess={() => { setShowUpload(false); load() }} />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap bg-gray-900 border border-gray-800 rounded-xl p-4">
        <input value={filterTicker} onChange={e => setFilterTicker(e.target.value.toUpperCase())}
          placeholder="Ticker…"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 w-24" />
        <select value={filterTag} onChange={e => setFilterTag(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500">
          <option value="">All tags</option>
          {VALID_TAGS.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <div className="flex items-center gap-2">
          <span className="text-gray-500 text-sm">Date:</span>
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500" />
          <span className="text-gray-500 text-sm">to</span>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500" />
        </div>
        <input type="number" min={1} max={10} value={minCleanliness} onChange={e => setMinCleanliness(e.target.value)}
          placeholder="Min ⭐"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 w-24" />
        <button onClick={load}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors ml-auto">
          Filter
        </button>
      </div>

      {/* Gallery */}
      {loading ? (
        <div className="text-center text-gray-500 text-sm py-12">Loading…</div>
      ) : charts.length === 0 ? (
        <div className="text-center text-gray-500 text-sm py-16">
          No charts yet. Upload your first screenshot!
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {charts.map(c => {
            const tags: string[] = (() => { try { return JSON.parse(c.tags) } catch { return [] } })()
            return (
              <Link key={c.id} href={`/charts/${c.id}`}
                className="group bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-emerald-500/50 transition-all hover:shadow-lg hover:shadow-emerald-500/5">
                <div className="aspect-video bg-gray-800 overflow-hidden">
                  <img src={chartImageUrl(c.image_path)} alt={`${c.ticker} ${c.capture_date}`}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                </div>
                <div className="p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white text-sm">{c.ticker}</span>
                    {c.cleanliness_score && (
                      <span className="text-xs text-gray-400">⭐ {c.cleanliness_score}/10</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">{c.capture_date} {c.timeframe && `· ${c.timeframe}`}</div>
                  {tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {tags.slice(0, 2).map(t => (
                        <span key={t} className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">{t}</span>
                      ))}
                      {tags.length > 2 && <span className="text-xs text-gray-500">+{tags.length - 2}</span>}
                    </div>
                  )}
                  {c.gemini_annotation && (
                    <span className="inline-block text-xs bg-violet-500/15 text-violet-300 px-1.5 py-0.5 rounded">✦ Gemini</span>
                  )}
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
