import type { Market, TagKey } from "@/lib/types"

export interface FilterPoint {
  market: Market
  is_anomaly: boolean
  bargaining_power: TagKey | null
}

export type LeaderboardKind = "rows" | "no-anomalies" | "filtered-out" | "tags-off"
export type HistoryKind = "rows" | "empty-ledger" | "filtered-out" | "tags-off"

export function leaderboardKind(
  points: FilterPoint[],
  market: "all" | Market,
  tags: TagKey[],
): LeaderboardKind {
  if (tags.length === 0) return "tags-off"
  const visible = points.some(
    (point) =>
      point.is_anomaly &&
      (market === "all" || point.market === market) &&
      point.bargaining_power !== null &&
      tags.includes(point.bargaining_power),
  )
  if (visible) return "rows"
  if (points.some((point) => point.is_anomaly)) return "filtered-out"
  return "no-anomalies"
}

export function historyKind(
  recordCount: number,
  visibleCount: number,
  tags: TagKey[],
): HistoryKind {
  if (tags.length === 0) return "tags-off"
  if (recordCount === 0) return "empty-ledger"
  if (visibleCount === 0) return "filtered-out"
  return "rows"
}

export function showNoAnomalyCaption(points: FilterPoint[], market: "all" | Market): boolean {
  return !points.some(
    (point) => point.is_anomaly && (market === "all" || point.market === market),
  )
}

export function anomalyInLeaderboard(
  point: FilterPoint,
  market: "all" | Market,
  tags: TagKey[],
): boolean {
  return (
    tags.length > 0 &&
    point.is_anomaly &&
    (market === "all" || point.market === market) &&
    point.bargaining_power !== null &&
    tags.includes(point.bargaining_power)
  )
}
