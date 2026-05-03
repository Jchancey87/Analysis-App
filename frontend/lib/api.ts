import axios from 'axios'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5000'

const api = axios.create({ baseURL: BASE })

// ── Types ─────────────────────────────────────────────────────────────────

export interface Gainer {
  id: number
  date: string
  ticker: string
  gap_pct: number | null
  float_shares: number | null
  rvol_15m: number | null
  sector: string | null
  market_cap: number | null
  news_headline: string | null
  news_fresh: boolean | null
  close_price: number | null
  open_price: number | null
  created_at: string
}

export interface ChartCapture {
  id: number
  ticker: string
  capture_date: string
  timeframe: string | null
  image_path: string
  setup_type: string | null
  cleanliness_score: number | null
  tags: string           // JSON array string
  notes: string | null
  gemini_annotation: string | null
  gemini_image_path: string | null
  gemini_imported_at: string | null
  created_at: string
}

export interface LLMJob {
  id: string
  type: string
  status: 'pending' | 'running' | 'done' | 'error'
  input_ref: string | null
  output: string | null
  model_used: string | null
  created_at: string
  updated_at: string
}

export interface ArchetypeStat {
  tag: string
  count: number
  avg_gap_pct: number | null
  avg_float_m: number | null
  avg_rvol: number | null
  avg_cleanliness: number | null
}

// ── Gainers ───────────────────────────────────────────────────────────────

export const getGainers = (params?: {
  date?: string
  min_gap?: number
  max_float?: number
  min_rvol?: number
  sector?: string
}) => api.get<Gainer[]>('/api/gainers', { params }).then(r => r.data)

export const getHeatmap = () =>
  api.get('/api/gainers/heatmap').then(r => r.data)

export const getGainersExportUrl = (params?: Record<string, string | number>) => {
  const q = new URLSearchParams(
    Object.entries(params ?? {}).map(([k, v]) => [k, String(v)])
  ).toString()
  return `${BASE}/api/gainers/export${q ? '?' + q : ''}`
}

export const getSectors = () =>
  api.get<string[]>('/api/gainers/sectors').then(r => r.data)

// ── Charts ────────────────────────────────────────────────────────────────

export const getCharts = (params?: {
  ticker?: string
  setup_type?: string
  tag?: string
  date_from?: string
  date_to?: string
  min_cleanliness?: number
}) => api.get<ChartCapture[]>('/api/charts', { params }).then(r => r.data)

export const getChart = (id: number) =>
  api.get<ChartCapture>(`/api/charts/${id}`).then(r => r.data)

export const uploadChart = (formData: FormData) =>
  api.post<{ id: number; image_path: string }>('/api/charts', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export const updateChart = (
  id: number,
  data: Partial<Pick<ChartCapture, 'notes' | 'cleanliness_score' | 'setup_type' | 'timeframe'> & { tags: string[] }>
) => api.put(`/api/charts/${id}`, data).then(r => r.data)

export const deleteChart = (id: number) =>
  api.delete(`/api/charts/${id}`).then(r => r.data)

export const importGeminiAnalysis = (
  chartId: number,
  analysisText: string,
  annotatedImage?: File
) => {
  if (annotatedImage) {
    const fd = new FormData()
    fd.append('analysis_text', analysisText)
    fd.append('annotated_image', annotatedImage)
    return api.post(`/api/charts/${chartId}/gemini-import`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  }
  return api.post(`/api/charts/${chartId}/gemini-import`, { analysis_text: analysisText }).then(r => r.data)
}

// ── Analysis ──────────────────────────────────────────────────────────────

export const startContinuation = (date: string) =>
  api.post<{ job_id: string; status: string }>('/api/continuation', { date }).then(r => r.data)

export const startSentiment = (query: string) =>
  api.post<{ job_id: string; status: string }>('/api/sentiment', { query }).then(r => r.data)

export const startResearch = (ticker: string, date?: string) =>
  api.post<{ job_id: string; status: string }>('/api/research', { ticker, date }).then(r => r.data)

export const startRiskDetection = (ticker: string) =>
  api.post<{ job_id: string; status: string }>('/api/research/risk', { ticker }).then(r => r.data)

export const startCatalystAnalysis = (ticker: string, date?: string) =>
  api.post<{ job_id: string; status: string }>('/api/research/catalyst', { ticker, date }).then(r => r.data)

export const startDeepContext = (ticker: string) =>
  api.post<{ job_id: string; status: string }>('/api/research/context', { ticker }).then(r => r.data)

export const getJob = (jobId: string) =>
  api.get<LLMJob>(`/api/jobs/${jobId}`).then(r => r.data)


export const getJobStatus = getJob

export const listJobs = (type?: string, limit = 50) =>
  api.get<LLMJob[]>('/api/jobs', { params: { type, limit } }).then(r => r.data)

export const getArchetypes = () =>
  api.get<ArchetypeStat[]>('/api/archetypes').then(r => r.data)

// ── Health ────────────────────────────────────────────────────────────────

export const getHealth = () => api.get('/api/health').then(r => r.data)

// ── Helpers ───────────────────────────────────────────────────────────────

export const chartImageUrl = (imagePath: string) =>
  `${BASE}/storage/charts/${imagePath.split('/charts/').pop()}`
