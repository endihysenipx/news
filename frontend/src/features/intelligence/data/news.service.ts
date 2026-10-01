import { demoBrief, demoNews } from "./news.mock"
import type { DailyBrief, NewsEntry, RepostGroup } from "../types"

export interface IntelligenceFeed { items: NewsEntry[]; isDemo: boolean; brief: DailyBrief | null; emailConfigured: boolean; emailRecipient: string; aiConfigured: boolean }
export type ReadState = "all" | "unread" | "read"
export interface IntelligenceFeedService { getFeed(apiFetch: (path: string) => Promise<Response>, readState?: ReadState, dueSoon?: boolean, savedOnly?: boolean, repostGroup?: RepostGroup): Promise<IntelligenceFeed> }

export const intelligenceFeedService: IntelligenceFeedService = {
  async getFeed(apiFetch, readState = "all", dueSoon = false, savedOnly = false, repostGroup) {
    const response = await apiFetch(`/intelligence/items?read_state=${readState}${dueSoon ? "&due_soon=true" : ""}${savedOnly ? "&saved_only=true" : ""}${repostGroup ? `&repost_group=${repostGroup}` : ""}`)
    if (!response.ok) throw new Error("Could not load intelligence updates.")
    const payload = await response.json() as { items: NewsEntry[]; hasLiveSources: boolean; emailConfigured: boolean; emailRecipient: string; aiConfigured: boolean }
    return payload.hasLiveSources
      ? { items: payload.items, isDemo: false, brief: null, emailConfigured: payload.emailConfigured, emailRecipient: payload.emailRecipient, aiConfigured: payload.aiConfigured }
      : { items: repostGroup ? [] : demoNews, isDemo: true, brief: demoBrief, emailConfigured: false, emailRecipient: "", aiConfigured: false }
  },
}
