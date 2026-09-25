"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"
import { AlertCircle, CalendarDays, RefreshCw, Search, SlidersHorizontal, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/auth"
import type { User } from "@/lib/types"
import { cn } from "@/lib/utils"
import { AIBrief } from "./ai-brief"
import { NewsCard } from "./news-card"
import { StrategicBriefPanel } from "./strategic-brief"
import { filters } from "./news-filters"
import { intelligenceFeedService } from "../data/news.service"
import type { DailyBrief, IntelligenceView, NewsEntry, NewsFilter, StrategicBrief } from "../types"

const DEMO_READ_PREFIX = "news-intelligence-demo-read:"
const DEMO_SAVED_PREFIX = "news-intelligence-demo-saved:"
const opportunityCategories = new Set(["GRANT", "TENDER", "BUSINESS", "PARTNERSHIP"])

function matchFilter(item: NewsEntry, filter: NewsFilter) {
  const { category, relevanceScore, tags } = item.analysis
  switch (filter) {
    case "For You": return category === "GRANT" || category === "TENDER" ? (item.focusScore ?? 0) >= 100 : relevanceScore >= 70
    case "All": return true
    case "Grants": return category === "GRANT"
    case "Tenders": return category === "TENDER"
    case "Business": return opportunityCategories.has(category)
    case "AI & Tech": return category === "TECHNOLOGY" || tags.includes("AI")
    case "Kosovo": return tags.includes("Kosovo")
    case "EU": return tags.includes("EU")
    case "Events": return category === "EVENT"
  }
}

function FeedSkeleton() {
  return <div aria-label="Loading intelligence updates" role="status" className="space-y-3">{[0, 1, 2].map((index) => <div key={index} className="animate-pulse rounded-xl border border-[#e8eae7] bg-white p-6"><div className="h-3 w-24 rounded bg-[#e9eee9]"/><div className="mt-5 h-5 w-2/3 rounded bg-[#e9eee9]"/><div className="mt-3 h-3 w-full rounded bg-[#f0f2f0]"/><div className="mt-2 h-3 w-4/5 rounded bg-[#f0f2f0]"/><div className="mt-7 h-3 w-1/3 rounded bg-[#f0f2f0]"/></div>)}</div>
}

function FeedEmptyState({ view, readMode, narrowed, priorityOnly, onReset }: { view: IntelligenceView; readMode: "unread" | "read"; narrowed: boolean; priorityOnly: boolean; onReset: () => void }) {
  const title = priorityOnly ? `No ${readMode} high priority updates.` : narrowed ? "No matching updates found." : view === "saved" ? "Nothing saved yet." : readMode === "read" ? "Nothing read yet." : "No unread updates."
  const description = priorityOnly ? readMode === "read" ? "High priority updates you mark as read will appear here." : "New high priority updates will appear here." : narrowed ? "Try adjusting your filters or search." : view === "saved" ? "Bookmark an update to keep it here." : readMode === "read" ? "Updates you open or mark as read will appear here." : "New updates will appear here after the next source check."
  return <div className="rounded-xl border border-dashed border-[#dce5dc] bg-white px-6 py-12 text-center"><SlidersHorizontal className="mx-auto size-6 text-[#a1b1a3]" /><h3 className="mt-3 font-semibold">{title}</h3><p className="mt-1 text-sm text-[#839087]">{description}</p>{narrowed ? <Button variant="ghost" size="sm" className="mt-4 text-[#4d7457]" onClick={onReset}>Clear filters</Button> : null}</div>
}

export function IntelligencePage({ view }: { view: IntelligenceView }) {
  const { user, apiFetch } = useAuth()
  return <IntelligenceWorkspace view={view} user={user} apiFetch={apiFetch} />
}

export function IntelligenceWorkspace({ view, user, apiFetch }: { view: IntelligenceView; user: Pick<User, "id" | "role"> | null; apiFetch: (path: string, init?: RequestInit) => Promise<Response> }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [items, setItems] = React.useState<NewsEntry[]>([])
  const [brief, setBrief] = React.useState<DailyBrief | null>(null)
  const [strategicBrief, setStrategicBrief] = React.useState<StrategicBrief | null>(null)
  const [generatingBrief, setGeneratingBrief] = React.useState(false)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState(false)
  const [isDemo, setIsDemo] = React.useState(false)
  const [emailConfigured, setEmailConfigured] = React.useState(false)
  const [aiConfigured, setAiConfigured] = React.useState(false)
  const category = searchParams.get("category")
  const highPriorityOnly = searchParams.get("priority") === "high"
  const filter: NewsFilter = filters.find((value) => value === category) || (view === "overview" ? "For You" : "All")
  const [query, setQuery] = React.useState("")
  const [savedIds, setSavedIds] = React.useState<string[]>([])
  const [demoReadIds, setDemoReadIds] = React.useState<string[]>([])
  const [readMode, setReadMode] = React.useState<"unread" | "read">("unread")
  const [emailingId, setEmailingId] = React.useState<string | null>(null)

  const loadFeed = React.useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const feed = await intelligenceFeedService.getFeed(apiFetch, view === "saved" ? "all" : readMode)
      setItems(feed.items)
      if (feed.isDemo) {
        try { setSavedIds(JSON.parse(localStorage.getItem(`${DEMO_SAVED_PREFIX}${user?.id || "guest"}`) || "[]")) }
        catch { setSavedIds([]) }
      } else setSavedIds(feed.items.filter((item) => Boolean(item.savedAt)).map((item) => item.id))
      setBrief(feed.brief)
      setIsDemo(feed.isDemo)
      setEmailConfigured(feed.emailConfigured)
      setAiConfigured(feed.aiConfigured)
    } catch { setError(true) }
    finally { setLoading(false) }
  }, [apiFetch, readMode, view, user])
  React.useEffect(() => { void loadFeed() }, [loadFeed])

  React.useEffect(() => {
    if (view !== "overview" || !aiConfigured || isDemo) return
    let active = true
    void apiFetch("/intelligence/brief")
      .then(async (response) => response.ok ? await response.json() as StrategicBrief | null : null)
      .then((result) => { if (active) setStrategicBrief(result) })
      .catch(() => {})
    return () => { active = false }
  }, [apiFetch, view, aiConfigured, isDemo])

  const generateBrief = async () => {
    if (generatingBrief) return
    setGeneratingBrief(true)
    try {
      const response = await apiFetch("/intelligence/brief", { method: "POST" })
      const payload = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "Could not generate the briefing.")
      setStrategicBrief(payload as StrategicBrief)
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : "Could not generate the briefing.")
    } finally {
      setGeneratingBrief(false)
    }
  }

  React.useEffect(() => {
    if (!user?.id) return
    try { setDemoReadIds(JSON.parse(localStorage.getItem(`${DEMO_READ_PREFIX}${user.id}`) || "[]")) } catch { setDemoReadIds([]) }
  }, [user?.id])

  const toggleSaved = (id: string) => {
    const wasSaved = savedIds.includes(id)
    setSavedIds((current) => {
      const next = current.includes(id) ? current.filter((value) => value !== id) : [...current, id]
      if (isDemo) localStorage.setItem(`${DEMO_SAVED_PREFIX}${user?.id || "guest"}`, JSON.stringify(next))
      return next
    })
    if (isDemo) return
    void (async () => {
      try {
        const response = await apiFetch(`/intelligence/items/${id}/saved`, { method: wasSaved ? "DELETE" : "PUT" })
        if (!response.ok) throw new Error("Could not update saved items")
      } catch {
        setSavedIds((current) => wasSaved ? [...new Set([...current, id])] : current.filter((value) => value !== id))
        toast.error("Could not update saved items. Please try again.")
      }
    })()
  }

  const setRead = (id: string, read: boolean) => {
    if (!user?.id) return
    if (isDemo) {
      setDemoReadIds((current) => {
        const next = read ? [...new Set([...current, id])] : current.filter((value) => value !== id)
        localStorage.setItem(`${DEMO_READ_PREFIX}${user.id}`, JSON.stringify(next))
        return next
      })
      return
    }
    const previous = items.find((item) => item.id === id)?.readAt || null
    setItems((current) => current.map((item) => item.id === id ? { ...item, readAt: read ? new Date().toISOString() : null } : item))
    void (async () => {
      try {
        const response = await apiFetch(`/intelligence/items/${id}/read`, { method: read ? "PUT" : "DELETE" })
        if (!response.ok) throw new Error("Could not update reading status.")
      } catch {
        setItems((current) => current.map((item) => item.id === id ? { ...item, readAt: previous } : item))
        toast.error("Could not update reading status. Please try again.")
      }
    })()
  }

  const sendEmail = async (id: string) => {
    if (isDemo || emailingId) return
    setEmailingId(id)
    try {
      const response = await apiFetch(`/intelligence/items/${id}/email`, { method: "POST" })
      const payload = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "Could not send this update.")
      setItems((current) => current.map((item) => item.id === id ? { ...item, emailedAt: payload.sentAt } : item))
      toast.success(payload.alreadySent ? "This update was already emailed." : `Sent to ${payload.recipient}`)
    } catch (cause) {
      toast.error(cause instanceof Error ? cause.message : "Could not send this update.")
    } finally {
      setEmailingId(null)
    }
  }

  const visibleItems = React.useMemo(() => {
    const needle = query.trim().toLowerCase()
    const matching = items.filter((item) => {
      if (view === "saved" && !savedIds.includes(item.id)) return false
      if (view !== "saved") {
        const isRead = isDemo ? demoReadIds.includes(item.id) : Boolean(item.readAt)
        if (readMode === "read" ? !isRead : isRead) return false
      }
      if (view === "opportunities" && !opportunityCategories.has(item.analysis.category)) return false
      if (highPriorityOnly && item.priority !== "HIGH") return false
      if (!matchFilter(item, filter)) return false
      if (!needle) return true
      return [item.title, item.analysis.summary, item.sourceName, ...item.analysis.tags].some((value) => value.toLowerCase().includes(needle))
    })
    return view === "overview" || view === "opportunities"
      ? matching.sort((a, b) => (b.focusScore ?? 0) - (a.focusScore ?? 0))
      : matching
  }, [items, view, savedIds, demoReadIds, isDemo, readMode, highPriorityOnly, filter, query])

  const opportunities = items.filter((item) => opportunityCategories.has(item.analysis.category)).length
  const today = new Date()
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()
  const upcoming = items.filter((item) => item.analysis.deadline && new Date(`${item.analysis.deadline}T12:00:00`).getTime() >= todayStart).sort((a, b) => (a.analysis.deadline || "").localeCompare(b.analysis.deadline || "")).slice(0, 3)
  const pageHeading = highPriorityOnly ? "High priority" : view === "overview" ? "Overview" : view === "news" ? "News" : view === "saved" ? "Saved" : "Opportunities"

  return <div className="min-h-screen px-4 pb-16 pt-7 text-[#24342a] sm:px-7 lg:px-10 lg:pt-10">
    <div className="mx-auto max-w-[1370px]">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div><div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#83958a]"><span className="size-1.5 rounded-full bg-[#7ca889]" /> News portal <span className="font-normal normal-case tracking-normal text-[#a0aaa2]">/ {isDemo ? "Sample data" : "Live sources"}</span></div><h1 className="mt-2 text-[32px] font-semibold tracking-[-0.045em] sm:text-[38px]">{pageHeading}</h1><p className="mt-1 text-sm text-[#758179]">Updates and opportunities, all in one place.</p></div>
        {!isDemo ? <Button variant="outline" size="sm" disabled={loading} className="border-[#e2e8e1] bg-white text-[#536359]" onClick={() => void loadFeed()}><RefreshCw className="size-4" /> Refresh feed</Button> : null}
      </div>

      {view === "overview" && brief && !loading ? <div className="mt-8"><AIBrief brief={brief} items={items} /></div> : null}
      {view === "overview" && !loading && !isDemo && aiConfigured && items.length ? <div className="mt-8"><StrategicBriefPanel brief={strategicBrief} generating={generatingBrief} onGenerate={() => void generateBrief()} /></div> : null}

      <div className="mt-8 grid gap-9 xl:grid-cols-[minmax(0,1fr)_280px] xl:gap-10">
        <section id="intelligence-feed" className="min-w-0">
          <div className="flex flex-wrap items-end justify-between gap-3"><div><div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#83958a]"><span className="size-1.5 rounded-full bg-[#8ab397]" /> {highPriorityOnly ? "Priority feed" : filter === "All" ? "Curated feed" : filter}</div><h2 className="mt-1 text-xl font-semibold tracking-tight">{highPriorityOnly ? "High priority updates" : view === "saved" ? "Your saved updates" : readMode === "read" ? "Read updates" : view === "opportunities" ? "Opportunity watch" : "Latest signals"}</h2></div><span className="text-xs text-[#8c978e]">{loading ? "Loading…" : `${visibleItems.length} ${visibleItems.length === 1 ? "update" : "updates"}`}</span></div>
          {view !== "saved" ? <div role="group" aria-label="Reading status" className="mt-4 inline-flex rounded-lg bg-[#edf1ec] p-0.5 text-xs font-medium">{(["unread", "read"] as const).map((mode) => <button key={mode} type="button" aria-pressed={readMode === mode} onClick={() => setReadMode(mode)} className={cn("rounded-md px-3.5 py-1.5 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#5e806c]", readMode === mode ? "bg-white text-[#2c4533] shadow-sm" : "text-[#76857a] hover:text-[#2c4533]")}>{mode === "unread" ? "Unread" : "Read"}</button>)}</div> : null}
          <div className="relative mt-5"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[#9ca9a0]"/><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search topics, sources, or keywords" aria-label="Search intelligence updates" className="h-10 border-[#e4eae3] bg-white pl-9 shadow-none focus-visible:ring-[#acc7b1]/40" /></div>
          <div className="mt-5 space-y-3">{loading ? <FeedSkeleton /> : error ? <div role="alert" className="rounded-xl border border-[#e8eae7] bg-white px-6 py-10 text-center"><AlertCircle className="mx-auto size-6 text-[#89998b]" /><h3 className="mt-3 font-semibold">Updates could not be loaded.</h3><p className="mt-1 text-sm text-[#7f8a80]">Please refresh the page and try again.</p></div> : visibleItems.length ? visibleItems.map((item) => <NewsCard key={item.id} item={item} saved={savedIds.includes(item.id)} read={isDemo ? demoReadIds.includes(item.id) : Boolean(item.readAt)} canEmail={!isDemo && emailConfigured} canAnalyze={!isDemo && aiConfigured} apiFetch={apiFetch} emailSending={emailingId === item.id} emailBusy={Boolean(emailingId)} onEmail={(id) => void sendEmail(id)} onToggleSaved={toggleSaved} onSetRead={setRead} />) : <FeedEmptyState view={view} readMode={readMode} priorityOnly={highPriorityOnly} narrowed={Boolean(query.trim()) || highPriorityOnly || filter !== "All" && !(view === "overview" && filter === "For You")} onReset={() => { router.push(view === "overview" ? "/intelligence/news" : "/intelligence/" + view); setQuery("") }} />}</div>
        </section>
        <aside className="space-y-6 xl:pt-1" aria-label="Intelligence highlights">
          <div className="rounded-xl border border-[#e8ece7] bg-white p-5"><div className="flex items-center gap-2 text-[#5e8067]"><Sparkles className="size-4" /><span className="text-[11px] font-semibold uppercase tracking-[0.12em]">At a glance</span></div><div className="mt-5 grid grid-cols-2 gap-4"><Link href="/intelligence/news?priority=high" className="rounded-lg -m-2 p-2 transition-colors hover:bg-[#f2f6ef] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#54775d]" aria-label="View high priority updates"><div className="text-2xl font-semibold tracking-tight">{items.filter((item) => item.priority === "HIGH").length}</div><div className="mt-1 text-xs text-[#5e8067]">High priority →</div></Link><div><div className="text-2xl font-semibold tracking-tight">{opportunities}</div><div className="mt-1 text-xs text-[#89958a]">Opportunities</div></div></div><p className="mt-5 border-t border-[#eef1ed] pt-4 text-xs leading-5 text-[#91a096]">Priority favors current grants and tenders for a Kosovo AI company. Check eligibility at the source.</p></div>
          {upcoming.length ? <div className="px-1"><div className="flex items-center justify-between"><h3 className="flex items-center gap-2 text-sm font-semibold"><CalendarDays className="size-4 text-[#7f9b85]" /> Dates to watch</h3>{isDemo ? <span className="text-[11px] text-[#a0aaa2]">Sample</span> : null}</div><div className="mt-4 space-y-0">{upcoming.map((item) => <div key={item.id} className="flex items-start gap-3 border-b border-[#e8ece7] py-3"><span className="min-w-11 text-xs font-semibold text-[#5d7964]">{new Date(`${item.analysis.deadline}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span><div className="min-w-0"><div className="text-xs font-medium leading-5 text-[#36473b]">{item.title}</div><div className="mt-0.5 text-[11px] text-[#9aa69c]">{item.sourceName}</div></div></div>)}</div></div> : null}
        </aside>
      </div>
    </div>
  </div>
}
