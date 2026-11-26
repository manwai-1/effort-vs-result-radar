import type { HistoryRecord, RadarPoint, TagKey } from "@/lib/types"
import { TAG_ORDER } from "@/lib/types"

export const TAG_LABELS: Record<
  TagKey,
  { en: string; zh: string; full: string }
> = {
  buyer_absorption: {
    en: "Buyer Absorption",
    zh: "買方暗中承接",
    full: "Buyer Absorption (買方暗中承接)",
  },
  seller_distribution: {
    en: "Seller Distribution",
    zh: "賣方暗中出貨",
    full: "Seller Distribution (賣方暗中出貨)",
  },
  stalemate_compression: {
    en: "Stalemate / Compression",
    zh: "多空角力壓縮",
    full: "Stalemate / Compression (多空角力壓縮)",
  },
}

export function isTagKey(value: unknown): value is TagKey {
  return TAG_ORDER.some((tag) => tag === value)
}

export function resolveLabels(
  row: Pick<
    RadarPoint,
    | "is_anomaly"
    | "bargaining_power"
    | "bargaining_power_label_en"
    | "bargaining_power_label_zh"
  >,
): { en: string | null; zh: string | null } {
  const table = row.bargaining_power ? TAG_LABELS[row.bargaining_power] : undefined
  const fallback = row.is_anomaly ? table : undefined
  const en = row.bargaining_power_label_en?.trim() || fallback?.en || null
  const zh = row.bargaining_power_label_zh?.trim() || fallback?.zh || null
  return { en, zh }
}

export function resolveHistoryLabels(
  row: Pick<
    HistoryRecord,
    "bargaining_power" | "bargaining_power_label_en" | "bargaining_power_label_zh"
  >,
): { en: string; zh: string } {
  const table = TAG_LABELS[row.bargaining_power]
  return {
    en: row.bargaining_power_label_en?.trim() || table.en,
    zh: row.bargaining_power_label_zh?.trim() || table.zh,
  }
}

export function bilingualTag(en: string, zh: string): string {
  return `${en} (${zh})`
}
