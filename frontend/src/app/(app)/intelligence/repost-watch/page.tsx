import { redirect } from "next/navigation"

export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams
  const query = new URLSearchParams({ tab: "repost-watch" })
  for (const [key, value] of Object.entries(params)) {
    if (key === "tab" || value === undefined) continue
    for (const entry of Array.isArray(value) ? value : [value]) query.append(key, entry)
  }
  redirect(`/intelligence/primex-linkedin?${query}`)
}
