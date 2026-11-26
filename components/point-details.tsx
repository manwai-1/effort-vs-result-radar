import { COPY } from "@/lib/copy"
import { formatPlain, formatPrice, formatRvol } from "@/lib/format"
import { bilingualTag, resolveLabels } from "@/lib/labels"
import type { RadarPoint } from "@/lib/types"

export function tagLine(point: RadarPoint): string | null {
  const labels = resolveLabels(point)
  if (labels.en && labels.zh) return bilingualTag(labels.en, labels.zh)
  if (!point.is_anomaly) return COPY.unmarked
  return null
}

export function pointName(point: RadarPoint): string {
  const base = `${point.ticker}, RVOL ${formatRvol(point.rvol)}, Displacement ${formatPlain(point.displacement)}`
  const tag = tagLine(point)
  return tag ? `${base}, ${tag}` : base
}

export function PointDetails({ point }: { point: RadarPoint }) {
  const tag = tagLine(point)
  return (
    <div className="space-y-0.5 font-mono text-xs leading-[1.4] text-[#F4F1EA]">
      <div>{point.ticker}</div>
      <div>RVOL {formatRvol(point.rvol)}</div>
      <div>Displacement {formatPlain(point.displacement)}</div>
      <div>Anomaly Score {formatPlain(point.anomaly_score)}</div>
      {tag ? <div>{tag}</div> : null}
      {point.last_price !== undefined ? (
        <div>Price {formatPrice(point.last_price, point.currency)}</div>
      ) : null}
    </div>
  )
}
