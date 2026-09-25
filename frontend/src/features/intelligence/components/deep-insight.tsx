"use client"

import * as React from "react"
import { ArrowUpRight, BrainCircuit, LoaderCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { DeepInsight, NewsEntry } from "../types"

export function DeepInsightAction({ item, apiFetch }: {
  item: NewsEntry
  apiFetch: (path: string, init?: RequestInit) => Promise<Response>
}) {
  const [open, setOpen] = React.useState(false)
  const [insight, setInsight] = React.useState<DeepInsight | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const analyze = async () => {
    if (loading) return
    setLoading(true)
    setError("")
    try {
      const response = await apiFetch(`/intelligence/items/${item.id}/deep-analysis`, { method: "POST" })
      const payload = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "Could not analyze this update.")
      setInsight(payload as DeepInsight)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not analyze this update.")
    } finally {
      setLoading(false)
    }
  }

  return <>
    <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs text-[#3e6b4c] hover:bg-[#edf4ed]" onClick={() => { setOpen(true); if (!insight) void analyze() }}><BrainCircuit className="size-3.5" /> Deep analysis</Button>
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#578066]"><BrainCircuit className="size-4" /> AI deep analysis</div>
          <DialogTitle className="pt-2 text-xl leading-snug">{item.title}</DialogTitle>
          <DialogDescription>Source: {item.sourceName} · AI analysis of saved source text. Verify details at the original source.</DialogDescription>
        </DialogHeader>
        {loading ? <div role="status" className="flex items-center gap-2 py-8 text-sm text-[#65756b]"><LoaderCircle className="size-4 animate-spin" /> Analyzing this update…</div> : error ? <div role="alert" className="rounded-lg bg-[#fff5f0] p-4 text-sm text-[#985c45]">{error}<Button variant="outline" size="sm" className="mt-3 block" onClick={() => void analyze()}>Try again</Button></div> : insight ? <div className="space-y-5 pb-2 text-sm">
          <div className="flex items-center gap-2 text-xs text-[#6f7f73]"><span className="rounded-full bg-[#edf4ed] px-2.5 py-1 font-semibold capitalize text-[#476b50]">{insight.confidence} confidence</span><span>Generated {new Date(insight.generatedAt).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span></div>
          <section><h3 className="font-semibold text-[#263e2f]">Key points</h3><ul className="mt-2 list-disc space-y-1.5 pl-5 leading-6 text-[#53645a]">{insight.keyPoints.map((point, index) => <li key={index}>{point}</li>)}</ul></section>
          <section className="rounded-xl bg-[#f2f6f1] p-4"><h3 className="font-semibold text-[#263e2f]">Business impact</h3><p className="mt-2 leading-6 text-[#53645a]">{insight.businessImpact}</p></section>
          <section><h3 className="font-semibold text-[#263e2f]">Suggested next steps</h3><ol className="mt-2 list-decimal space-y-1.5 pl-5 leading-6 text-[#53645a]">{insight.recommendedActions.map((action, index) => <li key={index}>{action}</li>)}</ol></section>
          {insight.openQuestions.length ? <section><h3 className="font-semibold text-[#263e2f]">Questions to verify</h3><ul className="mt-2 list-disc space-y-1.5 pl-5 leading-6 text-[#53645a]">{insight.openQuestions.map((question, index) => <li key={index}>{question}</li>)}</ul></section> : null}
          {insight.evidenceLimitations ? <p className="border-t pt-4 text-xs leading-5 text-[#7d897f]">Evidence limit: {insight.evidenceLimitations}</p> : null}
          {item.url ? <a href={item.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-[#426c4d] hover:underline">Open original source <ArrowUpRight className="size-4" /></a> : null}
        </div> : null}
      </DialogContent>
    </Dialog>
  </>
}
