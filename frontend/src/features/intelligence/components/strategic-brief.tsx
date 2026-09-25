import { ArrowUpRight, BrainCircuit, LoaderCircle, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { StrategicBrief } from "../types"

export function StrategicBriefPanel({ brief, generating, onGenerate }: {
  brief: StrategicBrief | null
  generating: boolean
  onGenerate: () => void
}) {
  return <section aria-labelledby="strategic-brief-heading" className="overflow-hidden rounded-2xl bg-[#213d2f] p-6 text-white shadow-sm sm:p-8">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.15em] text-[#b7d4bd]"><BrainCircuit className="size-4" /> AI intelligence</div>
        <h2 id="strategic-brief-heading" className="mt-2 text-2xl font-semibold tracking-tight">{brief ? brief.headline : "Your strategic brief"}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#d2e0d4]">{brief ? brief.overview : "Turn the latest updates into a focused view of what matters and what to do next."}</p>
      </div>
      {brief ? <span className="rounded-full border border-white/15 px-3 py-1 text-xs text-[#c8dacb]">Updated {new Date(brief.generatedAt).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</span> : <Button size="sm" onClick={onGenerate} disabled={generating} className="bg-white text-[#24412f] hover:bg-[#e6f0e6]">{generating ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}{generating ? "Analyzing updates…" : "Generate brief"}</Button>}
    </div>
    {brief ? <>
      <div className="mt-7 grid gap-3 lg:grid-cols-3">
        {brief.signals.map((signal, index) => <div key={signal.itemId} className="rounded-xl border border-white/10 bg-white/[0.07] p-4">
          <span className="text-xs font-semibold text-[#a8c8ae]">0{index + 1} / SIGNAL</span>
          <a href={signal.url} target="_blank" rel="noopener noreferrer" className="mt-3 flex items-start gap-1 text-sm font-semibold leading-5 hover:underline">{signal.title}<ArrowUpRight className="mt-0.5 size-3.5 shrink-0" /></a>
          <p className="mt-3 text-[13px] leading-5 text-[#deeadf]">{signal.insight}</p>
          <p className="mt-4 border-t border-white/10 pt-3 text-xs leading-5 text-[#b9d4be]"><strong className="text-white">Next step:</strong> {signal.nextStep}</p>
        </div>)}
      </div>
      {brief.watchouts.length ? <div className="mt-5 border-t border-white/15 pt-4"><span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#a8c8ae]">Keep in mind</span><p className="mt-1 text-xs leading-5 text-[#d1e0d3]">{brief.watchouts.join(" · ")}</p></div> : null}
      <p className="mt-5 text-[11px] text-[#a9c5af]">Based on saved news analyses. Check the original source before acting.</p>
    </> : <div className="mt-6 flex flex-wrap gap-2 text-xs text-[#d0e2d3]"><span className="rounded-full border border-white/15 px-3 py-1.5">What changed</span><span className="rounded-full border border-white/15 px-3 py-1.5">Why it matters</span><span className="rounded-full border border-white/15 px-3 py-1.5">Suggested next steps</span></div>}
  </section>
}
