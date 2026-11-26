import { ArrowDownToLine, ArrowUpFromLine, FoldHorizontal } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Label } from "@/components/ui/label"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { COPY } from "@/lib/copy"
import { TAG_LABELS } from "@/lib/labels"
import type { MarketFilter, TagKey } from "@/lib/types"
import { TAG_ORDER } from "@/lib/types"

const ICONS: Record<TagKey, LucideIcon> = {
  buyer_absorption: ArrowDownToLine,
  seller_distribution: ArrowUpFromLine,
  stalemate_compression: FoldHorizontal,
}

const ICON_COLOR: Record<TagKey, string> = {
  buyer_absorption: "text-[#E8B849]",
  seller_distribution: "text-[#F4F1EA]",
  stalemate_compression: "text-[#9AA3B2]",
}

export function FiltersBar({
  market,
  tags,
  onMarket,
  onTags,
}: {
  market: MarketFilter
  tags: TagKey[]
  onMarket: (market: MarketFilter) => void
  onTags: (tags: TagKey[]) => void
}) {
  return (
    <div className="flex flex-col gap-6 md:flex-row md:items-start">
      <div className="flex w-full flex-col gap-2 md:w-max md:shrink-0">
        <Label
          id="market-filter-label"
          className="font-sans text-xs font-medium text-[#9AA3B2]"
        >
          <span lang="zh-Hant">{COPY.market}</span>
        </Label>
        <ToggleGroup
          value={[market]}
          onValueChange={(next) => {
            const added = next.find((item) => item !== market)
            const value = added ?? next[0]
            if (value === "all" || value === "US" || value === "HK") onMarket(value)
          }}
          aria-labelledby="market-filter-label"
          className="grid w-full grid-cols-3 gap-2 md:flex md:w-max"
        >
          {(
            [
              ["all", COPY.marketAll],
              ["US", COPY.marketUs],
              ["HK", COPY.marketHk],
            ] as const
          ).map(([value, label]) => (
            <ToggleGroupItem
              key={value}
              value={value}
              className="min-h-11 w-full justify-center text-[#9AA3B2] md:w-auto md:min-w-16 data-pressed:border-[#E8B849] data-pressed:bg-[#E8B849] data-pressed:text-[#07090C]"
            >
              {label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <Label
          id="tag-filter-label"
          className="font-sans text-xs font-medium text-[#9AA3B2]"
        >
          <span lang="zh-Hant">{COPY.tags}</span>
        </Label>
        <ToggleGroup
          multiple
          value={tags}
          onValueChange={(next) => {
            onTags(TAG_ORDER.filter((tag) => next.includes(tag)))
          }}
          aria-labelledby="tag-filter-label"
          className="flex w-full flex-col items-stretch gap-2 md:flex-row md:flex-wrap"
        >
          {TAG_ORDER.map((tag) => {
            const Icon = ICONS[tag]
            return (
              <ToggleGroupItem
                key={tag}
                value={tag}
                className="h-auto min-h-11 w-full justify-start text-left text-[#F4F1EA] opacity-70 data-pressed:border-[#E8B849] data-pressed:opacity-100 md:w-auto"
              >
                <Icon className={`size-3.5 ${ICON_COLOR[tag]}`} aria-hidden />
                <span lang="zh-Hant" className="whitespace-normal text-left">
                  {TAG_LABELS[tag].full}
                </span>
              </ToggleGroupItem>
            )
          })}
        </ToggleGroup>
      </div>
    </div>
  )
}
