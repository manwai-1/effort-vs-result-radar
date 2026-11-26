import { TAG_LABELS } from "@/lib/labels"
import { roundHalfAwayFromZero } from "@/lib/format"
import type { HistoryRecord, HorizonSummary, TagKey, TagSummary } from "@/lib/types"
import { TAG_ORDER } from "@/lib/types"

function horizonBlock(tag: TagKey, returns: number[]): HorizonSummary {
  const applicable = tag !== "stalemate_compression"
  const block: HorizonSummary = {
    sample_count: returns.length,
    average_return_pct: null,
    hit_rate_pct: null,
    hit_rate_applicable: applicable,
    hit_rate_label: applicable ? null : "不適用",
  }
  if (returns.length === 0) return block
  const average = returns.reduce((sum, value) => sum + value, 0) / returns.length
  block.average_return_pct = roundHalfAwayFromZero(average, 4)
  if (!applicable) return block
  const hits = returns.filter((value) =>
    tag === "buyer_absorption" ? value > 0 : value < 0,
  ).length
  block.hit_rate_pct = roundHalfAwayFromZero((hits / returns.length) * 100, 4)
  return block
}

export function summarize(records: HistoryRecord[]): TagSummary[] {
  return TAG_ORDER.map((tag) => {
    const rows = records.filter((row) => row.bargaining_power === tag)
    return {
      bargaining_power: tag,
      bargaining_power_label_en: TAG_LABELS[tag].en,
      bargaining_power_label_zh: TAG_LABELS[tag].zh,
      sample_count: rows.length,
      t_plus_3: horizonBlock(
        tag,
        rows.flatMap((row) =>
          row.t_plus_3_return_pct === null ? [] : [row.t_plus_3_return_pct],
        ),
      ),
      t_plus_5: horizonBlock(
        tag,
        rows.flatMap((row) =>
          row.t_plus_5_return_pct === null ? [] : [row.t_plus_5_return_pct],
        ),
      ),
      t_plus_10: horizonBlock(
        tag,
        rows.flatMap((row) =>
          row.t_plus_10_return_pct === null ? [] : [row.t_plus_10_return_pct],
        ),
      ),
    }
  })
}

export function isCompleteSummary(value: TagSummary[] | undefined): value is TagSummary[] {
  if (!value || value.length !== 3) return false
  return TAG_ORDER.every((tag) => value.some((row) => row.bargaining_power === tag))
}

export function cardsForFilters(input: {
  records: HistoryRecord[]
  summary: TagSummary[] | undefined
  market: "all" | "US" | "HK"
  tags: TagKey[]
}): TagSummary[] {
  const visible = input.records.filter(
    (row) =>
      (input.market === "all" || row.market === input.market) &&
      input.tags.includes(row.bargaining_power),
  )
  const computed = summarize(visible)
  const unfiltered = input.market === "all" && input.tags.length === TAG_ORDER.length
  const source = unfiltered && isCompleteSummary(input.summary) ? input.summary : computed
  return TAG_ORDER.filter((tag) => input.tags.includes(tag)).map((tag) => {
    return (
      source.find((row) => row.bargaining_power === tag) ??
      computed.find((row) => row.bargaining_power === tag) ??
      computed[0]
    )
  })
}
