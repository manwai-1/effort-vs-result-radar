import { COPY } from "@/lib/copy"
import { formatPlain, formatPrice, formatRvol } from "@/lib/format"
import { bilingualTag, resolveLabels } from "@/lib/labels"
import type { RadarPoint } from "@/lib/types"

export function tagLine(point: RadarPoint): string {
  const labels = resolveLabels(point)
  if (point.is_anomaly && labels.en && labels.zh) return bilingualTag(labels.en, labels.zh)
  return COPY.unmarked
}

export function pointName(point: RadarPoint): string {
  return `${point.ticker}, RVOL ${formatRvol(point.rvol)}, Displacement ${formatPlain(point.displacement)}, ${tagLine(point)}`
}

export function PointDetails({ point }: { point: RadarPoint }) {
  return (
    <div className="space-y-0.5 font-mono text-xs leading-[1.4] text-[#F4F1EA]">
      <div>{point.ticker}</div>
      <div>RVOL {formatRvol(point.rvol)}</div>
      <div>Displacement {formatPlain(point.displacement)}</div>
      <div>Anomaly Score {formatPlain(point.anomaly_score)}</div>
      <div>{tagLine(point)}</div>
      {point.last_price !== undefined ? (
        <div>Price {formatPrice(point.last_price, point.currency)}</div>
      ) : null}
    </div>
  )
}
