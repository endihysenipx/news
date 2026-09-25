"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { LogOut, Newspaper, Radio } from "lucide-react"
import { useAuth } from "@/lib/auth"

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, loading, logout } = useAuth()
  React.useEffect(() => { if (!loading && !user) router.replace("/login") }, [loading, user, router])
  if (loading || !user) return <div className="flex min-h-screen items-center justify-center text-sm text-[#8b978c]">Loading workspace…</div>

  return <div className="min-h-screen bg-[#fafbf9]"><header className="sticky top-0 z-20 border-b border-[#e8ece7] bg-white/95 backdrop-blur"><div className="mx-auto flex h-16 max-w-[1450px] items-center justify-between gap-4 px-4 sm:px-7 lg:px-10"><Link href="/intelligence" className="flex items-center gap-2.5 text-sm font-semibold tracking-tight text-[#263b2b]"><span className="flex size-8 items-center justify-center rounded-lg bg-[#294334] text-white"><Newspaper className="size-4" /></span> News Intelligence</Link><nav aria-label="Workspace" className="flex items-center gap-1 sm:gap-4"><Link href="/intelligence/news" className="rounded-lg px-2 py-1.5 text-sm text-[#5f7062] hover:bg-[#f3f6f2] hover:text-[#263b2b]">Feed</Link><Link href="/intelligence/sources" className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm text-[#5f7062] hover:bg-[#f3f6f2] hover:text-[#263b2b]"><Radio className="size-3.5" /> Sources</Link><button type="button" onClick={() => void logout().then(() => router.replace("/login"))} aria-label="Sign out" className="rounded-lg p-2 text-[#7e8d80] hover:bg-[#f3f6f2] hover:text-[#263b2b]"><LogOut className="size-4" /></button></nav></div></header><main className="p-4">{children}</main></div>
}
