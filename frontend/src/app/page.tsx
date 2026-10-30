'use client'

import React, { useState, useEffect } from 'react'
import {
  checkHealth,
  ingestDocuments,
  askQuestion,
  getTenantChunks,
  clearTenantData,
  updateApiKey,
  type HealthResponse,
  type AskResponse,
  type Document as IngestDoc,
  type ChunkRecord,
} from '@/lib/api'
import {
  Building2,
  Search,
  Database,
  Cpu,
  Layers,
  Sparkles,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RefreshCw,
  Plus,
  Trash2,
  ExternalLink,
  ShieldCheck,
  ChevronRight,
  BookOpen,
  MessageSquare,
  Activity,
  Terminal,
  Copy,
  Check,
  Key,
  Info,
  Sliders,
  Send,
  Zap,
} from 'lucide-react'

// 10 Curated Project Management Benchmark Articles
const BENCHMARK_CORPUS: IngestDoc[] = [
  {
    brand: 'Asana',
    source: 'https://www.techradar.com/reviews/asana-project-management-review',
    text: `Asana Review 2026: Pricing and Feature Breakdown.
Asana continues to lead the project management space with its refined workflow builder and intuitive timeline views.
Pricing in 2026 starts with a generous Free Personal tier for up to 10 users. The Starter plan is priced at $10.99 per user per month billed annually ($13.49 billed monthly). The Advanced plan costs $24.99 per user per month, unlocking advanced reporting, workload balancing, and unlimited portfolio views.
Reviewers praise Asana's clean interface and versatile task dependencies, though some note that pricing gets steep quickly for mid-sized growing teams compared to budget alternatives like Trello.`,
  },
  {
    brand: 'Trello',
    source: 'https://www.pcmag.com/reviews/trello',
    text: `Trello 2026 Hands-On: Still the King of Kanban?
Trello remains one of the simplest and most accessible project management tools. Built around classic kanban boards, lists, and cards, it requires virtually zero onboarding time.
Trello's pricing remains very competitive: the Free plan supports unlimited cards and up to 10 boards per workspace. The Standard tier starts at $5.00 per user per month (billed annually), adding unlimited boards and custom fields. The Premium tier is $10.00 per user per month, offering Dashboard, Timeline, and Calendar views.
Compared to Asana, reviewers frequently emphasize that Trello is substantially more affordable and simpler, though it lacks native complex dependency management and deep resource planning out of the box.`,
  },
  {
    brand: 'Monday.com',
    source: 'https://www.forbes.com/advisor/business/software/monday-com-review',
    text: `Monday.com Work OS Review 2026: Flexibility at Scale.
Monday.com positions itself as a complete Work OS with colorful status columns, visual boards, and extensive automation recipes.
Monday.com pricing requires a minimum of 3 seats across all paid tiers: Basic starts at $9 per seat per month ($27/mo min), Standard at $12 per seat per month ($36/mo min), and Pro at $19 per seat per month ($57/mo min).
Reviewers celebrate its vibrant interface and customizable dashboards. Common critiques include the rigid 3-seat minimum requirement which penalizes solo founders or pairs, and a slightly steeper learning curve than Trello.`,
  },
  {
    brand: 'ClickUp',
    source: 'https://www.g2.com/products/clickup/reviews',
    text: `ClickUp: The All-In-One Productivity Suite Review.
ClickUp markets itself as 'one app to replace them all', incorporating docs, whiteboards, goals, chat, and task management into a single platform.
ClickUp pricing is aggressive: Free Forever tier with 100MB storage; Unlimited plan at $7 per user per month; and Business plan at $12 per user per month.
Reviewers highlight ClickUp's massive feature depth and high value-for-money ratio. However, power users and tech leads frequently report occasional performance lags, feature bloat, and an overwhelming settings menu.`,
  },
  {
    brand: 'Notion',
    source: 'https://www.theverge.com/reviews/notion-workspace-review',
    text: `Notion Projects & Wikis: How Notion Took Over Tech Teams.
Notion combines flexible markdown documents, databases, kanban boards, and AI integration into a unified workspace.
Pricing features a robust Free tier for individuals. The Plus plan is $10 per seat per month ($8 billed annually) with unlimited blocks and file uploads. The Business plan is $15 per seat per month.
Reviewers love the unmatched flexibility and aesthetic customization of Notion databases, but note that it requires significant setup time and lacks traditional Gantt critical-path calculation compared to dedicated PM software like Asana.`,
  },
  {
    brand: 'Asana',
    source: 'https://www.capterra.com/p/asana-vs-monday',
    text: `Asana vs Monday.com: Head-to-Head Comparison.
When comparing workflow automation, Asana's rules engine is known for reliability and deep enterprise integrations (Salesforce, Jira, Slack). Reviewers highlight Asana's Workload view as the best in class for preventing team burnout.
On the downside, Asana does not offer built-in spreadsheet-like calculations inside task columns, an area where Monday.com and ClickUp excel.`,
  },
  {
    brand: 'Trello',
    source: 'https://zapier.com/blog/best-kanban-software-trello',
    text: `Best Kanban Apps: Why Trello Stays Relevant.
Trello's Power-Up ecosystem allows users to connect integrations like Google Drive, GitHub, and Slack directly into card workflows. Butler automation provides simple no-code automation rules.
Reviewers note that while Trello is ideal for lightweight Agile sprints and content calendars, large engineering teams often outgrow it and migrate to Jira or Asana as subtask nesting needs increase.`,
  },
  {
    brand: 'Monday.com',
    source: 'https://www.businessinsider.com/monday-com-project-management-features',
    text: `Automations and Dashboards on Monday.com.
Monday.com's primary differentiator is its pre-built automation recipes, allowing users to trigger Slack alerts, reassign owners, or move cards between boards without coding.
Enterprise reviewers appreciate the cross-board reporting capabilities, although permissions management on lower-tier plans can be somewhat restrictive.`,
  },
  {
    brand: 'ClickUp',
    source: 'https://www.trustradius.com/products/clickup/reviews',
    text: `ClickUp Verified User Reviews & Benchmarks.
Surveyed users rate ClickUp 8.8/10 for feature variety and customization. Custom statuses, multiple assignees, and native time tracking are included even on entry tiers.
The most frequent complaint remains stability during heavy data import and occasional notification delays on mobile applications.`,
  },
  {
    brand: 'Notion',
    source: 'https://www.fastcompany.com/notion-productivity-review',
    text: `Building Modern Workflows with Notion.
Notion's relational database capabilities allow teams to link Project pages directly with Company Goals, Meeting Notes, and Sprint Tasks.
Critics point out that offline functionality is limited and permissions can become convoluted when sharing nested pages with external clients.`,
  },
]

export default function Home() {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'ask' | 'ingest' | 'vault' | 'graph'>('ask')

  // Dynamic Workspace list & active workspace
  const [tenantList, setTenantList] = useState<string[]>(['primary-brand', 'demo-isolated'])
  const [currentTenant, setCurrentTenant] = useState<string>('primary-brand')
  const [newTenantInput, setNewTenantInput] = useState('')

  // System Health
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)

  // API Key Modal
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [apiKeyMsg, setApiKeyMsg] = useState<string | null>(null)

  // Current tenant chunks & count
  const [tenantChunks, setTenantChunks] = useState<ChunkRecord[]>([])
  const [totalChunksCount, setTotalChunksCount] = useState<number>(0)
  const [chunksLoading, setChunksLoading] = useState(false)

  // Ingest form
  const [ingestMode, setIngestMode] = useState<'text' | 'url'>('text')
  const [brandInput, setBrandInput] = useState('Asana')
  const [sourceInput, setSourceInput] = useState('techradar-review')
  const [contentInput, setContentInput] = useState('')
  const [ingestLoading, setIngestLoading] = useState(false)
  const [ingestNotification, setIngestNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Ask Q&A
  const [question, setQuestion] = useState('')
  const [askLoading, setAskLoading] = useState(false)
  const [askResult, setAskResult] = useState<AskResponse | null>(null)
  const [askError, setAskError] = useState<string | null>(null)
  const [copiedAnswer, setCopiedAnswer] = useState(false)

  useEffect(() => {
    fetchHealth()
    fetchVault(currentTenant)
  }, [currentTenant])

  const fetchHealth = async () => {
    setHealthLoading(true)
    try {
      const data = await checkHealth()
      setHealth(data)
    } catch {
      setHealth(null)
    } finally {
      setHealthLoading(false)
    }
  }

  const fetchVault = async (tId: string) => {
    setChunksLoading(true)
    try {
      const data = await getTenantChunks(tId)
      setTenantChunks(data.chunks || [])
      setTotalChunksCount(data.total_chunks || 0)
    } catch {
      setTenantChunks([])
      setTotalChunksCount(0)
    } finally {
      setChunksLoading(false)
    }
  }

  const handleCreateTenant = (e: React.FormEvent) => {
    e.preventDefault()
    const clean = newTenantInput.trim().toLowerCase().replace(/[^a-z0-9-_]/g, '-')
    if (clean && !tenantList.includes(clean)) {
      setTenantList([...tenantList, clean])
      setCurrentTenant(clean)
      setNewTenantInput('')
      setAskResult(null)
      setAskError(null)
    }
  }

  const handleSwitchTenant = (tId: string) => {
    setCurrentTenant(tId)
    setAskResult(null)
    setAskError(null)
    setIngestNotification(null)
  }

  const handleClearTenant = async () => {
    if (confirm(`Clear all indexed vectors for workspace "${currentTenant}"?`)) {
      try {
        await clearTenantData(currentTenant)
        fetchVault(currentTenant)
        setAskResult(null)
      } catch (err: unknown) {
        alert(err instanceof Error ? err.message : String(err))
      }
    }
  }

  const handleSaveApiKey = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKeyInput.trim()) return
    try {
      await updateApiKey(apiKeyInput.trim())
      setApiKeyMsg('✓ Google Gemini API key updated and active!')
      setTimeout(() => {
        setShowKeyModal(false)
        setApiKeyMsg(null)
        fetchHealth()
      }, 1500)
    } catch (err: unknown) {
      setApiKeyMsg(`✗ Error: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  const handleIngestSingle = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!contentInput.trim() || !brandInput.trim()) return

    setIngestLoading(true)
    setIngestNotification(null)

    try {
      const doc: IngestDoc =
        ingestMode === 'url'
          ? { url: contentInput.trim(), brand: brandInput.trim() }
          : {
              text: contentInput.trim(),
              source: sourceInput.trim() || 'custom-note',
              brand: brandInput.trim(),
            }

      const res = await ingestDocuments(currentTenant, { documents: [doc] })
      setIngestNotification({
        type: 'success',
        message: `Indexed ${res.documents_stored} document (${res.chunks_stored} chunks) for "${currentTenant}".`,
      })
      setContentInput('')
      fetchVault(currentTenant)
    } catch (err: unknown) {
      setIngestNotification({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setIngestLoading(false)
    }
  }

  const handleIngestBenchmarkCorpus = async () => {
    setIngestLoading(true)
    setIngestNotification(null)
    try {
      const res = await ingestDocuments(currentTenant, { documents: BENCHMARK_CORPUS })
      setIngestNotification({
        type: 'success',
        message: `Indexed 10 benchmark articles (${res.chunks_stored} total chunks) into workspace "${currentTenant}".`,
      })
      fetchVault(currentTenant)
    } catch (err: unknown) {
      setIngestNotification({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setIngestLoading(false)
    }
  }

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim()
    if (!q) return

    setAskLoading(true)
    setAskError(null)
    setAskResult(null)

    try {
      const res = await askQuestion(currentTenant, { question: q })
      setAskResult(res)
    } catch (err: unknown) {
      setAskError(err instanceof Error ? err.message : String(err))
    } finally {
      setAskLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedAnswer(true)
    setTimeout(() => setCopiedAnswer(false), 2000)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-sky-50/40 to-indigo-50/30 text-slate-800 flex flex-col font-sans relative overflow-x-hidden">
      {/* ── Ambient Background Glow Orbs (Glassmorphism Effect) ── */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-sky-200/40 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-1/3 right-10 w-96 h-96 bg-indigo-200/30 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-10 left-1/3 w-80 h-80 bg-blue-200/30 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* ── Top Glass Navigation Bar ────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-white/70 backdrop-blur-xl border-b border-white/80 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.03)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
                  Omnibound
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/80 uppercase tracking-wide">
                  Brand AI
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">Multi-Tenant LangGraph Q&amp;A Agent</p>
            </div>
          </div>

          {/* Right Header: Health + API Key */}
          <div className="flex items-center space-x-3 text-xs">
            <button
              onClick={() => setShowKeyModal(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white/80 border border-slate-200/80 text-slate-700 hover:bg-white hover:border-slate-300 shadow-sm transition"
              title="Configure Google Gemini API Key"
            >
              <Key className="w-3.5 h-3.5 text-blue-600" />
              <span className="font-medium text-[11px]">API Key</span>
            </button>

            <button
              onClick={fetchHealth}
              disabled={healthLoading}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-white/80 border border-slate-200/80 shadow-sm hover:bg-white transition text-slate-600"
              title="Click to refresh system connectivity"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  health?.status === 'ok' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                }`}
              />
              <span className="font-mono text-[11px]">
                {healthLoading
                  ? 'Checking...'
                  : health
                  ? `VDB: ${health.vector_db} • LLM: ${health.llm_provider}`
                  : 'Backend Offline'}
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* ── API Key Modal ─────────────────────────────────────── */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white/90 backdrop-blur-xl border border-white/80 shadow-2xl rounded-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <Key className="w-4 h-4 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-900">Configure LLM Provider</h3>
              </div>
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Enter your <strong>Google Gemini API Key</strong> to use Gemini 2.0 Flash and text-embedding-004. If no key is set, the system uses its built-in contextual synthesis engine.
            </p>

            <form onSubmit={handleSaveApiKey} className="space-y-3">
              <input
                type="password"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              {apiKeyMsg && (
                <p className="text-xs font-medium text-blue-600">{apiKeyMsg}</p>
              )}

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowKeyModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition shadow"
                >
                  Save &amp; Activate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Glass Workspace / Tenant Switcher ─────────────────── */}
      <section className="bg-white/40 backdrop-blur-md border-b border-white/60 px-4 sm:px-6 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          {/* Active Workspaces Pills */}
          <div className="flex items-center space-x-2 overflow-x-auto py-1">
            <span className="text-xs font-semibold text-slate-500 flex items-center mr-1">
              <Building2 className="w-3.5 h-3.5 mr-1 text-slate-400" />
              Workspace:
            </span>
            {tenantList.map((t) => (
              <button
                key={t}
                onClick={() => handleSwitchTenant(t)}
                className={`px-3 py-1.5 rounded-xl text-xs font-mono font-medium transition flex items-center space-x-1.5 border shadow-sm ${
                  currentTenant === t
                    ? 'bg-blue-600 text-white border-blue-600 shadow-blue-500/20'
                    : 'bg-white/70 text-slate-600 border-white/80 hover:bg-white hover:text-slate-900'
                }`}
              >
                <span>{t}</span>
                {currentTenant === t && (
                  <span className="px-1.5 py-0.2 rounded-full bg-white/20 text-white text-[10px] font-bold">
                    {totalChunksCount} chunks
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* New Workspace Input */}
          <form onSubmit={handleCreateTenant} className="flex items-center space-x-2">
            <input
              type="text"
              value={newTenantInput}
              onChange={(e) => setNewTenantInput(e.target.value)}
              placeholder="New workspace (e.g. nike, hubspot)"
              className="px-3 py-1.5 text-xs bg-white/80 border border-slate-200/80 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 w-60 shadow-sm"
            />
            <button
              type="submit"
              disabled={!newTenantInput.trim()}
              className="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition shadow-sm disabled:opacity-40 flex items-center space-x-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add</span>
            </button>
          </form>
        </div>
      </section>

      {/* ── Light Glass Tabs ──────────────────────────────────── */}
      <div className="bg-white/30 backdrop-blur-md border-b border-white/60 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex space-x-8 text-xs font-semibold">
          {[
            { id: 'ask', label: 'Brand Q&A Studio', icon: MessageSquare },
            { id: 'ingest', label: 'Ingestion Pipeline', icon: Layers },
            { id: 'vault', label: `Knowledge Vault (${totalChunksCount})`, icon: Database },
            { id: 'graph', label: 'LangGraph State Machine', icon: Activity },
          ].map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 flex items-center space-x-2 border-b-2 transition font-medium ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Main Workspace Body ───────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full">
        {/* TAB 1: ASK & CHAT ─────────────────────────────────── */}
        {activeTab === 'ask' && (
          <div className="space-y-6">
            {/* Empty Workspace Warning & Quick Seed Banner */}
            {totalChunksCount === 0 && (
              <div className="glass-panel p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-amber-500">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-amber-100 text-amber-700 rounded-xl">
                    <Info className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-800">
                      Workspace "{currentTenant}" has 0 documents indexed
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Asking questions on an empty workspace will return "Not in Corpus" (as required by tenant isolation). Seed this workspace to enable Q&amp;A.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleIngestBenchmarkCorpus}
                  disabled={ingestLoading}
                  className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl transition shadow-md shadow-blue-500/20 disabled:opacity-50 flex items-center space-x-1.5"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>{ingestLoading ? 'Seeding...' : '⚡ Seed 10 Articles Into This Workspace'}</span>
                </button>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Column: Ask Form & Quick Prompts */}
              <div className="lg:col-span-5 space-y-6">
                <div className="glass-panel rounded-2xl p-6 space-y-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div className="flex items-center space-x-2.5">
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                        <Search className="w-4 h-4" />
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-slate-900">Query Brand Corpus</h2>
                        <p className="text-[11px] text-slate-500 font-medium">
                          Workspace: <span className="font-mono text-blue-600 font-semibold">{currentTenant}</span>
                        </p>
                      </div>
                    </div>
                    <span className="text-[11px] font-mono font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
                      {totalChunksCount} chunks
                    </span>
                  </div>

                  {/* Benchmark Prompts */}
                  <div>
                    <label className="text-[11px] uppercase tracking-wider font-bold text-slate-500 block mb-2">
                      Try Benchmark Questions
                    </label>
                    <div className="space-y-1.5">
                      {[
                        "What do reviewers say about Asana's pricing compared to Trello?",
                        "What are ClickUp's main strengths and weaknesses?",
                        "How does Monday.com pricing compare to Asana?",
                        "What is the capital of France?",
                      ].map((p, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            setQuestion(p)
                            handleAsk(p)
                          }}
                          className="w-full text-left p-2.5 rounded-xl bg-white/70 hover:bg-white border border-slate-200/60 hover:border-blue-300 text-xs text-slate-700 transition flex items-center justify-between group shadow-sm"
                        >
                          <span className="truncate mr-2 font-medium">{p}</span>
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition flex-shrink-0" />
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Question Input */}
                  <div className="space-y-3">
                    <label className="text-[11px] uppercase tracking-wider font-bold text-slate-500 block">
                      Custom Question
                    </label>
                    <div className="relative">
                      <textarea
                        rows={3}
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault()
                            handleAsk()
                          }
                        }}
                        placeholder="Ask how brands are reviewed, rated, or priced..."
                        className="w-full p-3.5 bg-white/90 border border-slate-200/80 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none shadow-sm"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => handleAsk()}
                      disabled={askLoading || !question.trim()}
                      className="w-full py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-md shadow-blue-500/25 disabled:opacity-40 flex items-center justify-center space-x-2"
                    >
                      {askLoading ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>LangGraph Agent Thinking...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-3.5 h-3.5" />
                          <span>Run Query</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Tenant Isolation Info */}
                <div className="glass-card rounded-2xl p-4 text-xs text-slate-600 space-y-2">
                  <div className="flex items-center space-x-2 text-slate-800 font-bold text-[11px]">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <span>Multi-Tenancy Guard Active</span>
                  </div>
                  <p className="text-[11px] leading-relaxed text-slate-500">
                    All vector searches are bounded by <code className="text-blue-700 font-mono font-semibold">omnibound_{currentTenant}</code>. Customer workspaces are physically segregated.
                  </p>
                </div>
              </div>

              {/* Right Column: Output & Citations */}
              <div className="lg:col-span-7 space-y-6">
                {askError && (
                  <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start space-x-3 shadow-sm">
                    <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="font-semibold">Query Error:</strong> {askError}
                    </div>
                  </div>
                )}

                {!askResult && !askLoading && (
                  <div className="glass-panel rounded-2xl p-12 text-center text-slate-500 space-y-3">
                    <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto shadow-inner">
                      <Cpu className="w-6 h-6" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-800">Agent Ready</h3>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                      Select a benchmark question on the left or enter your own query to inspect the LangGraph retrieval, relevance grading, and cited answer synthesis.
                    </p>
                  </div>
                )}

                {askLoading && (
                  <div className="glass-panel rounded-2xl p-10 space-y-4 text-center">
                    <div className="w-12 h-12 rounded-full border-3 border-blue-600 border-t-transparent animate-spin mx-auto" />
                    <div className="space-y-1">
                      <p className="text-sm font-bold text-slate-800">Executing LangGraph State Workflow</p>
                      <p className="text-xs text-slate-500 font-mono">retrieve ➔ LLM relevance grading ➔ conditional decision</p>
                    </div>
                  </div>
                )}

                {askResult && (
                  <div className="space-y-6">
                    {/* Synthesized Answer Card */}
                    <div className="glass-panel rounded-2xl p-6 relative overflow-hidden shadow-lg border border-white">
                      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                            Synthesized Answer
                          </span>
                          <span
                            className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border flex items-center space-x-1 ${
                              askResult.found_in_corpus
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-amber-50 text-amber-700 border-amber-200'
                            }`}
                          >
                            {askResult.found_in_corpus ? (
                              <>
                                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                <span>Found in Corpus</span>
                              </>
                            ) : (
                              <>
                                <XCircle className="w-3 h-3 text-amber-600" />
                                <span>Not in Corpus</span>
                              </>
                            )}
                          </span>
                        </div>

                        <button
                          onClick={() => copyToClipboard(askResult.answer)}
                          className="text-xs text-slate-600 hover:text-slate-900 flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 shadow-sm transition"
                        >
                          {copiedAnswer ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                          <span className="font-medium">{copiedAnswer ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>

                      <p className="text-sm text-slate-800 leading-relaxed font-normal whitespace-pre-wrap">
                        {askResult.answer}
                      </p>
                    </div>

                    {/* Supporting Citations */}
                    {askResult.citations && askResult.citations.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center space-x-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-blue-600" />
                          <span>Supporting Source Citations ({askResult.citations.length})</span>
                        </h3>

                        <div className="grid grid-cols-1 gap-3">
                          {askResult.citations.map((c, i) => (
                            <div
                              key={i}
                              className="glass-card rounded-2xl p-4 text-xs space-y-2 hover:shadow-md transition"
                            >
                              <div className="flex items-center justify-between">
                                <a
                                  href={c.source.startsWith('http') ? c.source : '#'}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-blue-600 hover:text-blue-800 font-mono text-[11px] truncate max-w-[80%] flex items-center space-x-1 font-semibold"
                                >
                                  <span>{c.source}</span>
                                  {c.source.startsWith('http') && <ExternalLink className="w-3 h-3 ml-1 flex-shrink-0" />}
                                </a>
                                <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-mono text-[10px] font-bold">
                                  {c.brand}
                                </span>
                              </div>
                              <p className="text-slate-700 text-xs leading-relaxed bg-white/80 p-3 rounded-xl border border-slate-100 font-mono text-[11px]">
                                "{c.chunk_text}"
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* LangGraph Trace Timeline */}
                    {askResult.trace && askResult.trace.length > 0 && (
                      <div className="glass-panel rounded-2xl p-5 space-y-3">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center space-x-1.5">
                            <Terminal className="w-3.5 h-3.5 text-indigo-600" />
                            <span>LangGraph Execution Path</span>
                          </h3>
                          <span className="text-[10px] font-mono font-semibold text-slate-500">
                            {askResult.trace.length} nodes traversed
                          </span>
                        </div>

                        <div className="space-y-2">
                          {askResult.trace.map((step, idx) => (
                            <div
                              key={idx}
                              className="flex items-start space-x-3 text-xs bg-white/80 p-2.5 rounded-xl border border-slate-100 shadow-sm"
                            >
                              <div className="flex-shrink-0 w-6 h-6 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 font-bold flex items-center justify-center text-[10px] font-mono">
                                {idx + 1}
                              </div>
                              <div className="flex-1 min-w-0">
                                <span className="font-bold text-slate-800 uppercase text-[10px] font-mono mr-2 px-1.5 py-0.5 rounded bg-slate-100">
                                  {step.node}
                                </span>
                                <span className="text-slate-600 font-mono text-xs">
                                  {step.detail}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: INGESTION STUDIO ───────────────────────────── */}
        {activeTab === 'ingest' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <h2 className="text-base font-bold text-slate-900">Document Ingestion Pipeline</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Target Workspace: <span className="text-blue-600 font-mono font-bold">{currentTenant}</span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleIngestBenchmarkCorpus}
                  disabled={ingestLoading}
                  className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl transition shadow-md shadow-blue-500/20 disabled:opacity-40 flex items-center space-x-2"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Seed Benchmark Corpus (10 Articles)</span>
                </button>
              </div>

              {/* Ingest Mode Toggle */}
              <div className="flex rounded-xl bg-slate-100 p-1 text-xs font-medium text-slate-600">
                <button
                  type="button"
                  onClick={() => setIngestMode('text')}
                  className={`flex-1 py-2 rounded-lg transition font-semibold ${
                    ingestMode === 'text' ? 'bg-white text-slate-900 shadow-sm' : 'hover:text-slate-900'
                  }`}
                >
                  Raw Article Text
                </button>
                <button
                  type="button"
                  onClick={() => setIngestMode('url')}
                  className={`flex-1 py-2 rounded-lg transition font-semibold ${
                    ingestMode === 'url' ? 'bg-white text-slate-900 shadow-sm' : 'hover:text-slate-900'
                  }`}
                >
                  Live Web Page URL
                </button>
              </div>

              {/* Ingest Form */}
              <form onSubmit={handleIngestSingle} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Brand Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={brandInput}
                      onChange={(e) => setBrandInput(e.target.value)}
                      placeholder="e.g. Asana, Trello, Notion"
                      required
                      className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                    />
                  </div>

                  {ingestMode === 'text' && (
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Source Identifier <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={sourceInput}
                        onChange={(e) => setSourceInput(e.target.value)}
                        placeholder="e.g. techradar-review-2026"
                        required
                        className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                      />
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    {ingestMode === 'url' ? 'Live Web URL' : 'Document Text'}{' '}
                    <span className="text-rose-500">*</span>
                  </label>
                  {ingestMode === 'url' ? (
                    <input
                      type="url"
                      value={contentInput}
                      onChange={(e) => setContentInput(e.target.value)}
                      placeholder="https://example.com/product-review"
                      required
                      className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                    />
                  ) : (
                    <textarea
                      rows={6}
                      value={contentInput}
                      onChange={(e) => setContentInput(e.target.value)}
                      placeholder="Paste review or comparison text here..."
                      required
                      className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono shadow-sm"
                    />
                  )}
                </div>

                <button
                  type="submit"
                  disabled={ingestLoading}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl transition shadow-md shadow-blue-500/20 disabled:opacity-40"
                >
                  {ingestLoading ? 'Chunking & Upserting Vectors...' : `Ingest for "${currentTenant}"`}
                </button>
              </form>

              {/* Notification Banner */}
              {ingestNotification && (
                <div
                  className={`p-4 rounded-xl text-xs font-semibold border flex items-center space-x-2 shadow-sm ${
                    ingestNotification.type === 'success'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-rose-50 text-rose-800 border-rose-200'
                  }`}
                >
                  {ingestNotification.type === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-600" />
                  ) : (
                    <XCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
                  )}
                  <span>{ingestNotification.message}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: KNOWLEDGE VAULT (CHUNKS INSPECTOR) ───────── */}
        {activeTab === 'vault' && (
          <div className="space-y-6">
            <div className="glass-panel rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900">Workspace Knowledge Vault</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Showing vectors stored in <code className="text-blue-600 font-mono font-bold">omnibound_{currentTenant}</code>
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => fetchVault(currentTenant)}
                  disabled={chunksLoading}
                  className="px-3 py-1.5 text-xs font-medium rounded-xl bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 flex items-center space-x-1.5 transition shadow-sm"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${chunksLoading ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>

                {totalChunksCount > 0 && (
                  <button
                    onClick={handleClearTenant}
                    className="px-3 py-1.5 text-xs font-medium rounded-xl bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 flex items-center space-x-1.5 transition shadow-sm"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                    <span>Clear Workspace Vectors</span>
                  </button>
                )}
              </div>
            </div>

            {totalChunksCount === 0 ? (
              <div className="glass-panel rounded-2xl p-12 text-center text-slate-500 space-y-3">
                <Database className="w-10 h-10 mx-auto text-slate-400" />
                <h3 className="text-sm font-bold text-slate-800">Workspace Vault Empty</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                  No vectors have been indexed for workspace "{currentTenant}". Use the Ingestion Pipeline tab or click below to seed 10 benchmark articles.
                </p>
                <button
                  onClick={handleIngestBenchmarkCorpus}
                  disabled={ingestLoading}
                  className="mt-3 px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition shadow"
                >
                  {ingestLoading ? 'Seeding...' : '⚡ Seed Benchmark Corpus'}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {tenantChunks.map((c, i) => (
                  <div
                    key={c.id || i}
                    className="glass-card rounded-2xl p-4 text-xs space-y-2 hover:shadow-md transition flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
                        <span className="font-mono text-[10px] text-slate-400 truncate max-w-[65%]">
                          ID: {c.id}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-mono font-bold">
                          {c.metadata?.brand || 'Brand'}
                        </span>
                      </div>
                      <p className="text-slate-700 font-mono text-[11px] leading-relaxed line-clamp-4 bg-white/60 p-2.5 rounded-xl border border-slate-100">
                        {c.document}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-slate-100 text-[10px] text-slate-500 flex items-center justify-between truncate font-medium">
                      <span className="truncate">Source: {c.metadata?.source || 'manual'}</span>
                      <span className="font-mono">Idx #{c.metadata?.chunk_index ?? 0}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: LANGGRAPH ARCHITECTURE VISUALIZER ─────────── */}
        {activeTab === 'graph' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <div className="pb-4 border-b border-slate-100">
                <h2 className="text-base font-bold text-slate-900">LangGraph StateGraph Workflow</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Cyclic state machine implementation with LLM relevance grading and bounded conditional retry
                </p>
              </div>

              {/* Visual Flow Diagram */}
              <div className="p-8 bg-slate-50/80 rounded-2xl border border-slate-200/80 flex flex-col items-center space-y-6 shadow-inner">
                {/* START -> RETRIEVE */}
                <div className="flex items-center space-x-3">
                  <span className="px-3 py-1 rounded-full bg-slate-200 text-slate-700 text-xs font-mono font-bold">
                    START
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <div className="px-5 py-3 rounded-xl bg-blue-100/80 border border-blue-200 text-blue-800 text-xs font-mono font-bold shadow-sm">
                    node: retrieve (top-5 chunks)
                  </div>
                </div>

                <div className="w-0.5 h-6 bg-slate-300" />

                {/* GRADE */}
                <div className="px-5 py-3 rounded-xl bg-indigo-100/80 border border-indigo-200 text-indigo-800 text-xs font-mono font-bold shadow-sm">
                  node: grade (LLM relevance check yes/no)
                </div>

                <div className="w-0.5 h-6 bg-slate-300" />

                {/* CONDITIONAL DECISION */}
                <div className="px-6 py-3 rounded-2xl bg-amber-100/80 border border-amber-200 text-amber-900 text-xs font-mono font-bold shadow-sm text-center">
                  conditional edge: decide_next
                </div>

                {/* 3 BRANCHES */}
                <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-center space-y-2 shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-emerald-700">Path 1: Relevant Chunks</span>
                    <div className="text-xs font-mono font-bold text-slate-900">node: answer</div>
                    <p className="text-[11px] text-slate-600">Strictly grounded synthesis with citations $\to$ END</p>
                  </div>

                  <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-center space-y-2 shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-sky-700">Path 2: None &amp; retry_count == 0</span>
                    <div className="text-xs font-mono font-bold text-slate-900">node: rewrite</div>
                    <p className="text-[11px] text-slate-600">Rephrases question $\to$ loops back to retrieve</p>
                  </div>

                  <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-center space-y-2 shadow-sm">
                    <span className="text-[10px] uppercase font-bold text-rose-700">Path 3: None &amp; Retried</span>
                    <div className="text-xs font-mono font-bold text-slate-900">node: not_found</div>
                    <p className="text-[11px] text-slate-600">Honest refusal (found_in_corpus = False) $\to$ END</p>
                  </div>
                </div>
              </div>

              {/* State Specification */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  State Dictionary (`AgentState`)
                </h3>
                <div className="p-4 rounded-xl bg-slate-900 text-slate-200 font-mono text-xs space-y-1.5 overflow-x-auto shadow-inner">
                  <p><span className="text-sky-400">tenant_id</span>: str — Tenant identifier for namespace isolation</p>
                  <p><span className="text-sky-400">question</span>: str — Current query string (original or rewritten)</p>
                  <p><span className="text-sky-400">retrieved_chunks</span>: list[dict] — Top-5 chunks retrieved from ChromaDB</p>
                  <p><span className="text-sky-400">relevant_chunks</span>: list[dict] — Chunks passing LLM relevance grading</p>
                  <p><span className="text-sky-400">retry_count</span>: int — Tracks query rephrasing attempts (max: 1)</p>
                  <p><span className="text-sky-400">answer</span>: str — Grounded synthesis text</p>
                  <p><span className="text-sky-400">found_in_corpus</span>: bool — True if answered; False if honestly refused</p>
                  <p><span className="text-sky-400">citations</span>: list[dict] — Source URLs, brands, and chunk text</p>
                  <p><span className="text-sky-400">trace</span>: list[dict] — Audit trail of every traversed node</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
