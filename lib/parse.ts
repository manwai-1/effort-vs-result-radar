import { isTagKey } from "@/lib/labels"
import type {
  HistoryFile,
  HistoryRecord,
  HorizonSummary,
  RadarFile,
  RadarPoint,
  TagSummary,
} from "@/lib/types"
import { TAG_ORDER } from "@/lib/types"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value)
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() !== "" ? value : undefined
}

function labelField(value: unknown): string | null | undefined {
  if (value === null) return null
  if (typeof value === "string") return value
  return undefined
}

function returnField(value: unknown): number | null | undefined {
  if (value === null) return null
  if (isFiniteNumber(value)) return value
  return undefined
}

function parsePoint(value: unknown): RadarPoint | null {
  if (!isRecord(value)) return null
  if (typeof value.ticker !== "string" || value.ticker.length === 0) return null
  if (value.market !== "US" && value.market !== "HK") return null
  if (!isFiniteNumber(value.rvol) || !isFiniteNumber(value.displacement)) return null
  if (!isFiniteNumber(value.anomaly_score) || typeof value.is_anomaly !== "boolean") return null
  if (value.trend_20d !== "down" && value.trend_20d !== "up" && value.trend_20d !== "sideways") {
    return null
  }
  if (!(value.bargaining_power === null || isTagKey(value.bargaining_power))) return null
  const en = labelField(value.bargaining_power_label_en)
  const zh = labelField(value.bargaining_power_label_zh)
  if (en === undefined || zh === undefined) return null
  const point: RadarPoint = {
    ticker: value.ticker,
    market: value.market,
    rvol: value.rvol,
    displacement: value.displacement,
    anomaly_score: value.anomaly_score,
    is_anomaly: value.is_anomaly,
    trend_20d: value.trend_20d,
    bargaining_power: value.bargaining_power,
    bargaining_power_label_en: en,
    bargaining_power_label_zh: zh,
  }
  if (value.last_price !== undefined) {
    if (!isFiniteNumber(value.last_price)) return null
    point.last_price = value.last_price
  }
  const currency = optionalString(value.currency)
  if (currency) point.currency = currency
  return point
}

function parseHorizon(value: unknown): HorizonSummary | null {
  if (!isRecord(value)) return null
  if (!isFiniteNumber(value.sample_count)) return null
  const average = returnField(value.average_return_pct)
  const hitRate = returnField(value.hit_rate_pct)
  if (average === undefined || hitRate === undefined) return null
  if (typeof value.hit_rate_applicable !== "boolean") return null
  const label = labelField(value.hit_rate_label)
  if (label === undefined) return null
  return {
    sample_count: value.sample_count,
    average_return_pct: average,
    hit_rate_pct: hitRate,
    hit_rate_applicable: value.hit_rate_applicable,
    hit_rate_label: label,
  }
}

function parseSummary(value: unknown): TagSummary[] | undefined {
  if (value === undefined) return undefined
  if (!Array.isArray(value)) return undefined
  const rows: TagSummary[] = []
  for (const item of value) {
    if (!isRecord(item) || !isTagKey(item.bargaining_power)) return undefined
    if (typeof item.bargaining_power_label_en !== "string") return undefined
    if (typeof item.bargaining_power_label_zh !== "string") return undefined
    if (!isFiniteNumber(item.sample_count)) return undefined
    const t3 = parseHorizon(item.t_plus_3)
    const t5 = parseHorizon(item.t_plus_5)
    const t10 = parseHorizon(item.t_plus_10)
    if (!t3 || !t5 || !t10) return undefined
    rows.push({
      bargaining_power: item.bargaining_power,
      bargaining_power_label_en: item.bargaining_power_label_en,
      bargaining_power_label_zh: item.bargaining_power_label_zh,
      sample_count: item.sample_count,
      t_plus_3: t3,
      t_plus_5: t5,
      t_plus_10: t10,
    })
  }
  const keys = new Set(rows.map((row) => row.bargaining_power))
  if (TAG_ORDER.some((tag) => !keys.has(tag)) || rows.length !== 3) return undefined
  return rows
}

function parseRecord(value: unknown): HistoryRecord | null {
  if (!isRecord(value)) return null
  if (typeof value.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value.date)) return null
  if (typeof value.ticker !== "string" || value.ticker.length === 0) return null
  if (value.market !== "US" && value.market !== "HK") return null
  if (!isFiniteNumber(value.signal_price)) return null
  if (!isFiniteNumber(value.rvol) || !isFiniteNumber(value.displacement)) return null
  if (!isFiniteNumber(value.anomaly_score) || !isTagKey(value.bargaining_power)) return null
  if (typeof value.bargaining_power_label_en !== "string") return null
  if (typeof value.bargaining_power_label_zh !== "string") return null
  const t3 = returnField(value.t_plus_3_return_pct)
  const t5 = returnField(value.t_plus_5_return_pct)
  const t10 = returnField(value.t_plus_10_return_pct)
  if (t3 === undefined || t5 === undefined || t10 === undefined) return null
  const record: HistoryRecord = {
    date: value.date,
    ticker: value.ticker,
    market: value.market,
    signal_price: value.signal_price,
    rvol: value.rvol,
    displacement: value.displacement,
    anomaly_score: value.anomaly_score,
    bargaining_power: value.bargaining_power,
    bargaining_power_label_en: value.bargaining_power_label_en,
    bargaining_power_label_zh: value.bargaining_power_label_zh,
    t_plus_3_return_pct: t3,
    t_plus_5_return_pct: t5,
    t_plus_10_return_pct: t10,
  }
  const currency = optionalString(value.currency)
  if (currency) record.currency = currency
  return record
}

export function parseRadar(value: unknown): RadarFile | null {
  if (!isRecord(value) || !Array.isArray(value.points)) return null
  const points: RadarPoint[] = []
  for (const item of value.points) {
    const point = parsePoint(item)
    if (!point) return null
    points.push(point)
  }
  const dataStatus = optionalString(value.data_status)
  if (dataStatus === "empty_fixture" && points.length > 0) return null
  const file: RadarFile = { points }
  if (dataStatus) file.data_status = dataStatus
  if (typeof value.generated_at === "string") file.generated_at = value.generated_at
  if (isRecord(value.universe)) {
    file.universe = {
      us_count: isFiniteNumber(value.universe.us_count) ? value.universe.us_count : undefined,
      hk_count: isFiniteNumber(value.universe.hk_count) ? value.universe.hk_count : undefined,
    }
  }
  return file
}

export function parseHistory(value: unknown): HistoryFile | null {
  if (!isRecord(value) || !Array.isArray(value.records)) return null
  const records: HistoryRecord[] = []
  for (const item of value.records) {
    const record = parseRecord(item)
    if (!record) return null
    records.push(record)
  }
  const dataStatus = optionalString(value.data_status)
  if (dataStatus === "empty_fixture" && records.length > 0) return null
  const file: HistoryFile = { records }
  if (dataStatus) file.data_status = dataStatus
  if (typeof value.updated_at === "string") file.updated_at = value.updated_at
  if (value.summary_by_tag !== undefined) {
    const summary = parseSummary(value.summary_by_tag)
    if (summary) file.summary_by_tag = summary
  }
  return file
}
