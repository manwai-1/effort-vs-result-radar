import { resolveHistoryLabels, resolveLabels } from "@/lib/labels"
import type {
  HistoryRecord,
  HistorySortKey,
  LeaderboardSortKey,
  RadarPoint,
  SortDirection,
} from "@/lib/types"

function directionOf(value: number, direction: SortDirection): number {
  return direction === "asc" ? value : -value
}

function compareText(a: string, b: string, direction: SortDirection): number {
  if (a === b) return 0
  return directionOf(a < b ? -1 : 1, direction)
}

function compareNumber(a: number, b: number, direction: SortDirection): number {
  if (a === b) return 0
  return directionOf(a < b ? -1 : 1, direction)
}

function compareNullable(a: number | null, b: number | null, direction: SortDirection): number {
  if (a === null && b === null) return 0
  if (a === null) return 1
  if (b === null) return -1
  return compareNumber(a, b, direction)
}

function tagText(point: RadarPoint): string {
  const labels = resolveLabels(point)
  return labels.en ?? point.bargaining_power ?? ""
}

export function sortLeaderboard(
  rows: RadarPoint[],
  key: LeaderboardSortKey,
  direction: SortDirection,
): RadarPoint[] {
  return rows
    .map((row, index) => ({ row, index }))
    .sort((left, right) => {
      let diff = 0
      if (key === "ticker") diff = compareText(left.row.ticker, right.row.ticker, direction)
      else if (key === "rvol") diff = compareNumber(left.row.rvol, right.row.rvol, direction)
      else if (key === "displacement") {
        diff = compareNumber(left.row.displacement, right.row.displacement, direction)
      } else if (key === "anomaly_score") {
        diff = compareNumber(left.row.anomaly_score, right.row.anomaly_score, direction)
      } else diff = compareText(tagText(left.row), tagText(right.row), direction)
      if (diff !== 0) return diff
      const ticker = compareText(left.row.ticker, right.row.ticker, "asc")
      if (ticker !== 0) return ticker
      return left.index - right.index
    })
    .map((item) => item.row)
}

function historyTag(row: HistoryRecord): string {
  return resolveHistoryLabels(row).en
}

export function sortHistory(
  rows: HistoryRecord[],
  key: HistorySortKey,
  direction: SortDirection,
): HistoryRecord[] {
  return rows
    .map((row, index) => ({ row, index }))
    .sort((left, right) => {
      let diff = 0
      if (key === "date") diff = compareText(left.row.date, right.row.date, direction)
      else if (key === "ticker") diff = compareText(left.row.ticker, right.row.ticker, direction)
      else if (key === "signal_price") {
        diff = compareNumber(left.row.signal_price, right.row.signal_price, direction)
      } else if (key === "rvol") diff = compareNumber(left.row.rvol, right.row.rvol, direction)
      else if (key === "displacement") {
        diff = compareNumber(left.row.displacement, right.row.displacement, direction)
      } else if (key === "anomaly_score") {
        diff = compareNumber(left.row.anomaly_score, right.row.anomaly_score, direction)
      } else if (key === "bargaining_power") {
        diff = compareText(historyTag(left.row), historyTag(right.row), direction)
      } else diff = compareNullable(left.row[key], right.row[key], direction)
      if (diff !== 0) return diff
      const date = compareText(left.row.date, right.row.date, "desc")
      if (date !== 0) return date
      const ticker = compareText(left.row.ticker, right.row.ticker, "asc")
      if (ticker !== 0) return ticker
      return left.index - right.index
    })
    .map((item) => item.row)
}

export function defaultSortDirection(key: LeaderboardSortKey | HistorySortKey): SortDirection {
  if (key === "ticker" || key === "bargaining_power") return "asc"
  return "desc"
}
