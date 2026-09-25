"use client"

import * as React from "react"
import { ArrowRight, ArrowUpRight, BrainCircuit, LoaderCircle, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { StrategicBrief } from "../types"

export function StrategicBriefPanel({ brief, generating, onGenerate }: {
  brief: StrategicBrief | null
  generating: boolean
  onGenerate: () => void
}) {
  const [open, setOpen] = React.useState(false)
  const featured = brief?.signals.slice(0, 3) ?? []
  const dateLabel = brief ? new Date(brief.generatedAt).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : null

  return <>
    <section aria-labelledby="strategic-brief-heading" className="rounded-2xl border border-[#e1e9e1] bg-white p-5 shadow-[0_8px_32px_rgba(28,52,35,0.035)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#557560]"><span className="flex size-7 items-center justify-center rounded-lg bg-[#edf4ed]"><BrainCircuit className="size-4" /></span> AI briefing <span className="font-normal tracking-normal text-[#9aa89d]">/ What matters now</span></div>
        {dateLabel ? <span className="text-xs text-[#89968b]">Updated {dateLabel}</span> : null}
      </div>

      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0 max-w-4xl">
          <h2 id="strategic-brief-heading" className="text-lg font-semibold leading-snug tracking-[-0.025em] text-[#233a2b]">{brief ? "Key signals for your business" : "Your strategic brief"}</h2>
          <p className="mt-1 line-clamp-2 text-sm leading-6 text-[#64736a]">{brief ? brief.overview : "A quick read of the most useful updates, why they matter, and what to check next."}</p>
        </div>
        {!brief ? <Button size="sm" onClick={onGenerate} disabled={generating} className="bg-[#284b35] text-white hover:bg-[#1f3c2a]">{generating ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}{generating ? "Analyzing updates…" : "Generate brief"}</Button> : null}
      </div>

      {featured.length ? <>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {featured.map((signal, index) => <article key={signal.itemId} className="flex min-w-0 flex-col rounded-xl border border-[#e5ebe4] bg-[#f8faf7] p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.13em] text-[#78937d]">0{index + 1} / Signal</span>
            <h3 className="mt-2 line-clamp-2 text-sm font-semibold leading-5 text-[#2a3e30]">{signal.title}</h3>
            <p className="mt-2 line-clamp-2 text-[13px] leading-5 text-[#66746a]">{signal.insight}</p>
            <a href={signal.url} target="_blank" rel="noopener noreferrer" className="mt-auto inline-flex w-fit items-center gap-1 pt-3 text-xs font-semibold text-[#4e7257] hover:underline">Original source <ArrowUpRight className="size-3.5" /></a>
          </article>)}
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[#edf1ec] pt-3">
          <p className="text-xs text-[#8b988e]">AI summary of saved analyses. Verify details at the source.</p>
          <Button variant="ghost" size="sm" className="-mr-2 text-[#3d6848] hover:bg-[#f0f5ef]" onClick={() => setOpen(true)}>View full brief <ArrowRight className="size-4" /></Button>
        </div>
      </> : null}
    </section>

    {brief ? <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#5c8064]"><BrainCircuit className="size-4" /> Strategic brief</div>
          <DialogTitle className="pt-2 text-xl leading-snug">{brief.headline}</DialogTitle>
          <DialogDescription>Updated {dateLabel} · Based on saved news analyses</DialogDescription>
        </DialogHeader>
        <p className="text-sm leading-6 text-[#526257]">{brief.overview}</p>
        <div className="space-y-3">{brief.signals.map((signal, index) => <section key={signal.itemId} className="rounded-xl border border-[#e5ebe4] bg-[#f8faf7] p-4">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#78937d]">0{index + 1} / Signal</span>
          <h3 className="mt-2 text-sm font-semibold leading-5 text-[#2a3e30]">{signal.title}</h3>
          <p className="mt-2 text-sm leading-6 text-[#58695d]">{signal.insight}</p>
          <p className="mt-3 border-t border-[#e5ebe4] pt-3 text-sm leading-6 text-[#58695d]"><strong className="text-[#2a3e30]">Next step:</strong> {signal.nextStep}</p>
          <a href={signal.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[#4e7257] hover:underline">Open original source <ArrowUpRight className="size-3.5" /></a>
        </section>)}</div>
        {brief.watchouts.length ? <section className="border-t border-[#e5ebe4] pt-4"><h3 className="text-sm font-semibold text-[#2a3e30]">Keep in mind</h3><ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-6 text-[#64736a]">{brief.watchouts.map((watchout, index) => <li key={index}>{watchout}</li>)}</ul></section> : null}
      </DialogContent>
    </Dialog> : null}
  </>
}
