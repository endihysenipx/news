import { MessageCircle, Repeat2, ThumbsUp } from "lucide-react"
import type { LinkedInActivity as Activity } from "../types"

export function LinkedInActivity({ activity }: { activity: Activity }) {
  return <div className="mt-4 space-y-3 border-t border-[#eef0ed] pt-3 text-xs text-[#68776b]">
    {activity.kind === "REPOST" ? <p className="flex items-center gap-1.5 font-medium text-[#4f7161]"><Repeat2 className="size-3.5" /> Reposted{activity.authorName ? ` by ${activity.authorName}` : ""}</p> : null}
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      {activity.reactionCount !== null ? <span className="flex items-center gap-1.5"><ThumbsUp className="size-3.5" />{activity.reactionCount.toLocaleString()} likes / reactions</span> : null}
      {activity.commentCount !== null ? <span className="flex items-center gap-1.5"><MessageCircle className="size-3.5" />{activity.commentCount.toLocaleString()} comments</span> : null}
      {activity.repostCount !== null ? <span className="flex items-center gap-1.5"><Repeat2 className="size-3.5" />{activity.repostCount.toLocaleString()} reposts / shares</span> : null}
      {activity.checkedAt ? <span className="text-[#91a096]">Checked {new Date(activity.checkedAt).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span> : null}
    </div>
    {activity.originalPostText || activity.originalPostUrl ? <details className="rounded-lg bg-[#f6f8f5] p-3"><summary className="cursor-pointer font-medium text-[#4f7161]">Shared post{activity.originalAuthor ? ` by ${activity.originalAuthor}` : ""}</summary>{activity.originalPostText ? <p className="mt-2 whitespace-pre-wrap text-[13px] leading-5">{activity.originalPostText}</p> : null}{activity.originalPostUrl ? <a href={activity.originalPostUrl} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block font-medium text-[#405d4b] hover:underline">Open shared post ↗</a> : null}</details> : null}
    {activity.comments.length ? <details className="rounded-lg bg-[#f6f8f5] p-3"><summary className="cursor-pointer font-medium text-[#4f7161]">Available comments ({activity.comments.length})</summary><p className="mt-2 text-[#91a096]">Public comment preview. LinkedIn may show more comments.</p><div className="mt-3 space-y-3">{activity.comments.map((comment, index) => <div key={`${comment.url || comment.author || "comment"}-${index}`} className="border-l-2 border-[#dce5dc] pl-3"><div className="font-medium text-[#405d4b]">{comment.author || "LinkedIn member"}</div><p className="mt-1 whitespace-pre-wrap text-[13px] leading-5">{comment.text}</p>{comment.url ? <a href={comment.url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-block hover:underline">View on LinkedIn ↗</a> : null}</div>)}</div></details> : null}
  </div>
}
