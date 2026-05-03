'use client'
import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X } from 'lucide-react'
import TagSelector from './TagSelector'
import { uploadChart } from '@/lib/api'
import { PatternTag, VALID_TAGS } from '@/lib/geminiPrompt'

interface Props {
  onSuccess?: (id: number) => void
}

const SETUP_TYPES = ['gap-up', 'gap-down', 'breakout', 'breakdown', 'continuation', 'reversal']
const TIMEFRAMES  = ['1m', '2m', '5m', '15m', '30m', '1h', 'daily']

export default function ChartUpload({ onSuccess }: Props) {
  const [file, setFile]       = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [ticker, setTicker]   = useState('')
  const [date, setDate]       = useState('')
  const [timeframe, setTimeframe] = useState('')
  const [setupType, setSetupType] = useState('')
  const [score, setScore]     = useState<number>(5)
  const [notes, setNotes]     = useState('')
  const [tags, setTags]       = useState<PatternTag[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setSuccess(false)
    setError(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] }, maxFiles: 1,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !ticker || !date) {
      setError('Image, ticker, and date are required.')
      return
    }
    setLoading(true); setError(null)
    try {
      const fd = new FormData()
      fd.append('image', file)
      fd.append('ticker', ticker.toUpperCase())
      fd.append('capture_date', date)
      fd.append('timeframe', timeframe)
      fd.append('setup_type', setupType)
      fd.append('cleanliness_score', String(score))
      fd.append('notes', notes)
      fd.append('tags', JSON.stringify(tags))
      const res = await uploadChart(fd)
      setSuccess(true)
      onSuccess?.(res.id)
      // Reset
      setFile(null); setPreview(null); setTicker(''); setDate('')
      setTimeframe(''); setSetupType(''); setScore(5); setNotes(''); setTags([])
    } catch (err: any) {
      setError(err?.response?.data?.error ?? 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-emerald-500 bg-emerald-500/5' : 'border-gray-700 hover:border-gray-500'}`}
      >
        <input {...getInputProps()} />
        {preview ? (
          <div className="relative inline-block">
            <img src={preview} alt="preview" className="max-h-48 rounded-lg mx-auto" />
            <button type="button" onClick={e => { e.stopPropagation(); setFile(null); setPreview(null) }}
              className="absolute -top-2 -right-2 bg-red-600 rounded-full p-0.5">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="space-y-2 text-gray-500">
            <Upload className="mx-auto" size={32} />
            <p className="text-sm">Drop chart screenshot here or click to browse</p>
            <p className="text-xs">PNG, JPG, WEBP — max 10 MB</p>
          </div>
        )}
      </div>

      {/* Fields */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Ticker *</label>
          <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
            placeholder="NVDA" maxLength={10}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500" />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Date *</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500" />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Timeframe</label>
          <select value={timeframe} onChange={e => setTimeframe(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500">
            <option value="">— select —</option>
            {TIMEFRAMES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Setup Type</label>
          <select value={setupType} onChange={e => setSetupType(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500">
            <option value="">— select —</option>
            {SETUP_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {/* Cleanliness score */}
      <div>
        <label className="text-xs text-gray-400 mb-1 block">Cleanliness Score: <span className="text-white font-semibold">{score}/10</span></label>
        <input type="range" min={1} max={10} value={score} onChange={e => setScore(Number(e.target.value))}
          className="w-full accent-emerald-500" />
      </div>

      {/* Tags */}
      <div>
        <label className="text-xs text-gray-400 mb-2 block">Pattern Tags</label>
        <TagSelector selected={tags} onChange={setTags} />
      </div>

      {/* Notes */}
      <div>
        <label className="text-xs text-gray-400 mb-1 block">Notes</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
          placeholder="Trade notes, observations…"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 resize-none" />
      </div>

      {error   && <p className="text-red-400 text-sm">{error}</p>}
      {success && <p className="text-emerald-400 text-sm">✓ Chart uploaded successfully</p>}

      <button type="submit" disabled={loading}
        className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm">
        {loading ? 'Uploading…' : 'Upload Chart'}
      </button>
    </form>
  )
}
