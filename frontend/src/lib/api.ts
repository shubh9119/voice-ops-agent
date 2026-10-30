const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Document {
  url?: string
  text?: string
  source?: string
  brand: string
}

export interface IngestRequest {
  documents: Document[]
}

export interface IngestResponse {
  documents_stored: number
  chunks_stored: number
}

export interface AskRequest {
  question: string
}

export interface Citation {
  source: string
  brand: string
  chunk_text: string
}

export interface TraceEntry {
  node: string
  detail: string
}

export interface AskResponse {
  answer: string
  found_in_corpus: boolean
  citations: Citation[]
  trace: TraceEntry[]
}

export interface HealthResponse {
  status: string
  version: string
  vector_db: string
  llm_provider: string
}

export interface ChunkRecord {
  id: string
  document: string
  metadata: {
    tenant_id: string
    doc_id: string
    chunk_index: number
    source: string
    brand: string
  }
}

export interface TenantChunksResponse {
  tenant_id: string
  total_chunks: number
  chunks: ChunkRecord[]
}

export interface TenantStatsResponse {
  tenant_id: string
  total_chunks: number
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

export async function updateApiKey(apiKey: string): Promise<{ status: string; detail: string }> {
  const res = await fetch(`${API_BASE}/settings/api-key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  })
  if (!res.ok) throw new Error('Failed to update API key')
  return res.json()
}

export async function ingestDocuments(tenantId: string, body: IngestRequest): Promise<IngestResponse> {
  const res = await fetch(`${API_BASE}/tenants/${tenantId}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Ingest failed')
  }
  return res.json()
}

export async function askQuestion(tenantId: string, body: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/tenants/${tenantId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Ask failed')
  }
  return res.json()
}

export async function getTenantStats(tenantId: string): Promise<TenantStatsResponse> {
  const res = await fetch(`${API_BASE}/tenants/${tenantId}/stats`)
  if (!res.ok) throw new Error('Failed to fetch tenant stats')
  return res.json()
}

export async function getTenantChunks(tenantId: string): Promise<TenantChunksResponse> {
  const res = await fetch(`${API_BASE}/tenants/${tenantId}/chunks`)
  if (!res.ok) throw new Error('Failed to fetch tenant chunks')
  return res.json()
}

export async function clearTenantData(tenantId: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/tenants/${tenantId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to clear tenant data')
  return res.json()
}
