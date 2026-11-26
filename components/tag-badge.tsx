import { ArrowDownToLine, ArrowUpFromLine, FoldHorizontal } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { TagKey } from "@/lib/types"

const ICONS: Record<TagKey, LucideIcon> = {
  buyer_absorption: ArrowDownToLine,
  seller_distribution: ArrowUpFromLine,
  stalemate_compression: FoldHorizontal,
}

const BORDERS: Record<TagKey, string> = {
  buyer_absorption: "border-[#E8B849]",
  seller_distribution: "border-[#F4F1EA]",
  stalemate_compression: "border-[#2A3140]",
}

const ICON_COLOR: Record<TagKey, string> = {
  buyer_absorption: "text-[#E8B849]",
  seller_distribution: "text-[#F4F1EA]",
  stalemate_compression: "text-[#9AA3B2]",
}

export function TagBadge({
  tag,
  en,
  zh,
}: {
  tag: TagKey
  en: string
  zh: string
}) {
  const Icon = ICONS[tag]
  return (
    <Badge variant="outline" className={`${BORDERS[tag]} max-w-full`}>
      <Icon className={`size-3.5 ${ICON_COLOR[tag]}`} aria-hidden />
      <span className="flex min-w-0 flex-col items-start text-left">
        <span className="whitespace-normal font-sans text-sm font-medium leading-[1.2] text-[#F4F1EA]">
          {en}
        </span>
        <span
          lang="zh-Hant"
          className="whitespace-normal font-sans text-xs font-medium leading-[1.3] text-[#F4F1EA]"
        >
          {zh}
        </span>
      </span>
    </Badge>
  )
}
