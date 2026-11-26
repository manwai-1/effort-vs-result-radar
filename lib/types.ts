export const TAG_ORDER = [
  "buyer_absorption",
  "seller_distribution",
  "stalemate_compression",
] as const

export type TagKey = (typeof TAG_ORDER)[number]
export type Market = "US" | "HK"
export type MarketFilter = "all" | Market
export type Trend = "down" | "up" | "sideways"

export interface RadarPoint {
  ticker: string
  market: Market
  rvol: number
  displacement: number
  anomaly_score: number
  is_anomaly: boolean
  trend_20d: Trend
  bargaining_power: TagKey | null
  bargaining_power_label_en: string | null
  bargaining_power_label_zh: string | null
  last_price?: number
  currency?: string
}

export interface RadarFile {
  data_status?: string
  generated_at?: string
  universe?: {
    us_count?: number
    hk_count?: number
  }
  points: RadarPoint[]
}

export interface HorizonSummary {
  sample_count: number
  average_return_pct: number | null
  hit_rate_pct: number | null
  hit_rate_applicable: boolean
  hit_rate_label: string | null
}

export interface TagSummary {
  bargaining_power: TagKey
  bargaining_power_label_en: string
  bargaining_power_label_zh: string
  sample_count: number
  t_plus_3: HorizonSummary
  t_plus_5: HorizonSummary
  t_plus_10: HorizonSummary
}

export interface HistoryRecord {
  date: string
  ticker: string
  market: Market
  signal_price: number
  currency?: string
  rvol: number
  displacement: number
  anomaly_score: number
  bargaining_power: TagKey
  bargaining_power_label_en: string
  bargaining_power_label_zh: string
  t_plus_3_return_pct: number | null
  t_plus_5_return_pct: number | null
  t_plus_10_return_pct: number | null
}

export interface HistoryFile {
  data_status?: string
  updated_at?: string
  records: HistoryRecord[]
  summary_by_tag?: TagSummary[]
}

export type LoadState<T> =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; data: T }

export type SortDirection = "asc" | "desc"

export type LeaderboardSortKey =
  | "ticker"
  | "rvol"
  | "displacement"
  | "anomaly_score"
  | "bargaining_power"

export type HistorySortKey =
  | LeaderboardSortKey
  | "date"
  | "signal_price"
  | "t_plus_3_return_pct"
  | "t_plus_5_return_pct"
  | "t_plus_10_return_pct"

export interface SortState<Key extends string> {
  key: Key
  direction: SortDirection
}
