"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import {
  CartesianGrid,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
} from "recharts"
import { PointDetails, pointName } from "@/components/point-details"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { COPY } from "@/lib/copy"
import { chartDomain } from "@/lib/domain"
import { formatTick } from "@/lib/format"
import { anomalyInLeaderboard } from "@/lib/view-state"
import { focusCard } from "@/lib/styles"
import type { RadarPoint, TagKey } from "@/lib/types"

const MARGIN = { top: 28, right: 16, bottom: 48, left: 64 }
const AXIS_FONT =
  "var(--font-ibm-plex-mono), var(--font-noto-sans-tc), ui-monospace, monospace"

function pointDomId(ticker: string): string {
  return `radar-point-${ticker.replace(/[^A-Za-z0-9_-]/g, "_")}`
}


export function ScatterPlot({
  points,
  tags,
  activeTicker,
  selectedTicker,
  showTooltip,
  showCaption,
  onActivate,
  onClear,
  onSelect,
}: {
  points: RadarPoint[]
  tags: TagKey[]
  activeTicker: string | null
  selectedTicker: string | null
  showTooltip: boolean
  showCaption: boolean
  onActivate: (ticker: string) => void
  onClear: () => void
  onSelect: (ticker: string) => void
}) {
  const frame = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const domain = useMemo(() => chartDomain(points), [points])
  const ordered = useMemo(() => {
    const anomalies = points.filter((point) => point.is_anomaly)
    const rest = points.filter((point) => !point.is_anomaly)
    return [...anomalies, ...rest]
  }, [points])

  useEffect(() => {
    const element = frame.current
    if (!element) return
    const update = () => {
      setSize({ width: element.clientWidth, height: element.clientHeight })
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const active = points.find((point) => point.ticker === activeTicker) ?? null
  const plotWidth = Math.max(0, size.width - MARGIN.left - MARGIN.right)
  const plotHeight = Math.max(0, size.height - MARGIN.top - MARGIN.bottom)
  const xSpan = domain.xMax - domain.xMin || 1
  const ySpan = domain.yMax - domain.yMin || 1
  const xPx = (value: number) => MARGIN.left + ((value - domain.xMin) / xSpan) * plotWidth
  const yPx = (value: number) =>
    MARGIN.top + (1 - (value - domain.yMin) / ySpan) * plotHeight

  function move(step: number) {
    if (ordered.length === 0) return
    const current = ordered.findIndex((point) => point.ticker === activeTicker)
    const index =
      current < 0
        ? step > 0
          ? 0
          : ordered.length - 1
        : (current + step + ordered.length) % ordered.length
    onActivate(ordered[index].ticker)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{COPY.liveRadar}</CardTitle>
        <CardDescription className="font-sans text-sm leading-6 text-[#9AA3B2]">
          {COPY.zoneRule}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div
          ref={frame}
          role="application"
          tabIndex={0}
          aria-label={COPY.chartName}
          aria-activedescendant={active ? pointDomId(active.ticker) : undefined}
          className={`relative h-[280px] w-full outline-none md:h-[480px] ${focusCard}`}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowDown") {
              event.preventDefault()
              move(1)
            } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
              event.preventDefault()
              move(-1)
            } else if (event.key === "Escape") {
              event.preventDefault()
              onClear()
            } else if (event.key === "Enter" && active && anomalyInLeaderboard(active, "all", tags)) {
              event.preventDefault()
              onSelect(active.ticker)
            }
          }}
        >
          <p className="sr-only" aria-live="polite">
            {active ? pointName(active) : ""}
          </p>
          {size.width > 0 && size.height > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart accessibilityLayer={false} tabIndex={-1} margin={MARGIN}>
                <CartesianGrid stroke="#2A3140" strokeWidth={1} />
                <XAxis
                  type="number"
                  dataKey="rvol"
                  domain={[domain.xMin, domain.xMax]}
                  tickFormatter={formatTick}
                  tick={{ fill: "#9AA3B2", fontSize: 12, fontFamily: AXIS_FONT }}
                  tickLine={{ stroke: "#2A3140" }}
                  axisLine={{ stroke: "#2A3140" }}
                  height={40}
                  label={{
                    value: COPY.axisX,
                    position: "insideBottom",
                    offset: 0,
                    fill: "#9AA3B2",
                    fontSize: 12,
                    fontFamily: AXIS_FONT,
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="displacement"
                  domain={[domain.yMin, domain.yMax]}
                  tickFormatter={formatTick}
                  tick={{ fill: "#9AA3B2", fontSize: 12, fontFamily: AXIS_FONT }}
                  tickLine={{ stroke: "#2A3140" }}
                  axisLine={{ stroke: "#2A3140" }}
                  width={56}
                  label={{
                    value: COPY.axisY,
                    angle: -90,
                    position: "insideLeft",
                    offset: 8,
                    fill: "#9AA3B2",
                    fontSize: 12,
                    fontFamily: AXIS_FONT,
                    style: { textAnchor: "middle" },
                  }}
                />
                <ReferenceArea
                  x1={2}
                  x2={domain.xMax}
                  y1={Math.max(domain.yMin, 0)}
                  y2={Math.min(0.5, domain.yMax)}
                  fill="#E8B849"
                  fillOpacity={0.12}
                  stroke="#E8B849"
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  ifOverflow="visible"
                  style={{ pointerEvents: "none" }}
                  label={{
                    value: COPY.zoneLabel,
                    position: "insideTopLeft",
                    fill: "#E8B849",
                    fontSize: 12,
                    fontFamily: AXIS_FONT,
                  }}
                />
                <ReferenceLine
                  x={2}
                  stroke="#E8B849"
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  ifOverflow="visible"
                />
                <ReferenceLine
                  y={0.5}
                  stroke="#E8B849"
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  ifOverflow="visible"
                />
                <Scatter
                  data={[
                    ...points,
                    { rvol: domain.xMin, displacement: domain.yMin, anchor: true },
                    { rvol: domain.xMax, displacement: domain.yMax, anchor: true },
                  ]}
                  isAnimationActive={false}
                  shape={(raw) => {
                    const props = raw as {
                      cx?: number
                      cy?: number
                      payload?: RadarPoint & { anchor?: boolean }
                    }
                    const point = props.payload
                    if (!point?.ticker || point.anchor || props.cx == null || props.cy == null) return <g />
                    const hot = point.is_anomaly
                    const radius = hot ? 4 : 2
                    const marked =
                      point.ticker === activeTicker || point.ticker === selectedTicker
                    return (
                      <g>
                        <circle
                          id={pointDomId(point.ticker)}
                          role="img"
                          aria-label={pointName(point)}
                          cx={props.cx}
                          cy={props.cy}
                          r={point.is_anomaly ? 22 : 12}
                          fill="transparent"
                          style={{ cursor: "pointer" }}
                          onMouseEnter={() => onActivate(point.ticker)}
                          onMouseLeave={onClear}
                          onClick={() => {
                            onActivate(point.ticker)
                            if (anomalyInLeaderboard(point, "all", tags)) onSelect(point.ticker)
                          }}
                        />
                        {marked ? (
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={radius + 5}
                            fill="none"
                            stroke="#E8B849"
                            strokeWidth={2}
                            style={{ pointerEvents: "none" }}
                          />
                        ) : null}
                        <circle
                          cx={props.cx}
                          cy={props.cy}
                          r={radius}
                          fill={hot ? "#E8B849" : "#9AA3B2"}
                          stroke={hot ? "#12161C" : "none"}
                          strokeWidth={hot ? 1 : 0}
                          style={{ pointerEvents: "none" }}
                        />
                      </g>
                    )
                  }}
                />
              </ScatterChart>
            </ResponsiveContainer>
          ) : null}
          {showTooltip && active ? (
            <div
              aria-hidden
              className="pointer-events-none absolute z-10 max-w-[220px] rounded-lg border border-[#2A3140] bg-[#12161C] px-3 py-2"
              style={{
                left: Math.min(Math.max(8, xPx(active.rvol) + 12), Math.max(8, size.width - 228)),
                top: Math.max(8, yPx(active.displacement) - 96),
              }}
            >
              <PointDetails point={active} />
            </div>
          ) : null}
        </div>
        {showCaption ? (
          <p className="max-w-prose px-4 py-4 font-sans text-base font-normal leading-7 text-[#F4F1EA]">
            {COPY.noAnomalies}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
