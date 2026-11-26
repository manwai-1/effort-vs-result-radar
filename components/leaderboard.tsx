"use client"

import { useEffect } from "react"
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { PointDetails } from "@/components/point-details"
import { TagBadge } from "@/components/tag-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { COPY, LEADERBOARD_COLUMNS } from "@/lib/copy"
import { formatCount, formatPlain, formatRvol } from "@/lib/format"
import { resolveLabels } from "@/lib/labels"
import { focusCard } from "@/lib/styles"
import { defaultSortDirection, sortLeaderboard } from "@/lib/sort"
import type { LeaderboardSortKey, RadarPoint, SortState } from "@/lib/types"

const PAGE_SIZE = 50

function rowDomId(ticker: string, desktop: boolean): string {
  return `${desktop ? "d" : "m"}-anomaly-${ticker.replace(/[^A-Za-z0-9_-]/g, "_")}`
}

function SortIcon({
  active,
  direction,
}: {
  active: boolean
  direction: "asc" | "desc"
}) {
  if (!active) return <ArrowUpDown className="size-3.5 text-[#9AA3B2]" aria-hidden />
  if (direction === "desc") return <ArrowDown className="size-3.5 text-[#9AA3B2]" aria-hidden />
  return <ArrowUp className="size-3.5 text-[#9AA3B2]" aria-hidden />
}

export function Leaderboard({
  rows,
  countLabel,
  empty,
  sort,
  page,
  activeTicker,
  selectedTicker,
  onSort,
  onPage,
  onHover,
  onHoverEnd,
  onSelect,
}: {
  rows: RadarPoint[]
  countLabel: string | null
  empty: string | null
  sort: SortState<LeaderboardSortKey>
  page: number
  activeTicker: string | null
  selectedTicker: string | null
  onSort: (sort: SortState<LeaderboardSortKey>) => void
  onPage: (page: number) => void
  onHover: (ticker: string) => void
  onHoverEnd: () => void
  onSelect: (ticker: string) => void
}) {
  const sorted = sortLeaderboard(rows, sort.key, sort.direction)
  const paged = sorted.length > 100
  const pageCount = paged ? Math.ceil(sorted.length / PAGE_SIZE) : 1
  const safePage = Math.min(Math.max(page, 1), pageCount)
  const visible = paged
    ? sorted.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)
    : sorted

  useEffect(() => {
    if (!selectedTicker) return
    const desktop = window.matchMedia("(min-width: 768px)").matches
    document.getElementById(rowDomId(selectedTicker, desktop))?.scrollIntoView({
      block: "nearest",
    })
  }, [selectedTicker, safePage, sort.key, sort.direction])

  function toggle(key: LeaderboardSortKey) {
    if (sort.key === key) {
      onSort({ key, direction: sort.direction === "asc" ? "desc" : "asc" })
      return
    }
    onSort({ key, direction: defaultSortDirection(key) })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{COPY.leaderboard}</CardTitle>
        {countLabel ? (
          <p className="font-mono text-xs font-normal leading-[1.4] text-[#9AA3B2] tabular-nums">
            {countLabel}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {empty ? (
          <p className="max-w-prose font-sans text-base font-normal leading-7 text-[#F4F1EA]">
            {empty}
          </p>
        ) : (
          <>
            <div className="mb-4 flex items-center gap-2 md:hidden">
              <Select
                value={sort.key}
                onValueChange={(value) => {
                  if (!LEADERBOARD_COLUMNS.some((column) => column.key === value)) return
                  const key = value as LeaderboardSortKey
                  if (key === sort.key) return
                  onSort({ key, direction: defaultSortDirection(key) })
                }}
              >
                <SelectTrigger className={focusCard} aria-label={COPY.leaderboard}>
                  <SelectValue>
                    {(value) =>
                      LEADERBOARD_COLUMNS.find((column) => column.key === value)?.label ?? ""
                    }
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {LEADERBOARD_COLUMNS.map((column) => (
                    <SelectItem key={column.key} value={column.key}>
                      {column.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="ghost"
                className={`min-h-11 shrink-0 ${focusCard}`}
                onClick={() => toggle(sort.key)}
              >
                <SortIcon active direction={sort.direction} />
                <span className="font-sans text-xs font-medium uppercase tracking-wide text-[#9AA3B2]">
                  {LEADERBOARD_COLUMNS.find((column) => column.key === sort.key)?.label}
                </span>
              </Button>
            </div>
            <div className="flex flex-col gap-3 md:hidden">
              {visible.map((row) => (
                <RecordBlock
                  key={row.ticker}
                  row={row}
                  selected={selectedTicker === row.ticker}
                  active={activeTicker === row.ticker}
                  onHover={onHover}
                  onHoverEnd={onHoverEnd}
                  onSelect={onSelect}
                />
              ))}
            </div>
            <div className="hidden md:block">
              <Table className="table-fixed">
                <colgroup>
                  <col className="w-[14%]" />
                  <col className="w-[13%]" />
                  <col className="w-[24%]" />
                  <col className="w-[18%]" />
                  <col className="w-[31%]" />
                </colgroup>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    {LEADERBOARD_COLUMNS.map((column) => {
                      const active = sort.key === column.key
                      return (
                        <TableHead
                          key={column.key}
                          aria-sort={
                            active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"
                          }
                          className="overflow-hidden p-0 align-bottom"
                        >
                          <Button
                            type="button"
                            variant="ghost"
                            className={`h-auto min-h-11 w-full flex-col gap-1 whitespace-normal rounded-none px-1 py-2 ${focusCard} ${
                              column.numeric ? "items-end" : "items-start"
                            }`}
                            onClick={() => toggle(column.key)}
                          >
                            <span className="w-full min-w-0 whitespace-normal text-left font-sans text-xs font-medium uppercase leading-tight tracking-wide text-[#9AA3B2]">
                              {column.label}
                            </span>
                            <SortIcon active={active} direction={sort.direction} />
                          </Button>
                        </TableHead>
                      )
                    })}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((row) => (
                    <DesktopRow
                      key={row.ticker}
                      row={row}
                      selected={selectedTicker === row.ticker}
                      active={activeTicker === row.ticker}
                      onHover={onHover}
                      onHoverEnd={onHoverEnd}
                      onSelect={onSelect}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
            {paged ? (
              <div className="mt-4 flex items-center justify-between gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  className={`min-h-11 ${focusCard}`}
                  disabled={safePage <= 1}
                  onClick={() => onPage(safePage - 1)}
                >
                  {COPY.previous}
                </Button>
                <span className="font-mono text-xs text-[#9AA3B2] tabular-nums">
                  {COPY.page(safePage)}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  className={`min-h-11 ${focusCard}`}
                  disabled={safePage >= pageCount}
                  onClick={() => onPage(safePage + 1)}
                >
                  {COPY.next}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function rowClass(active: boolean, selected: boolean): string {
  if (selected) return "shadow-[inset_0_0_0_2px_#E8B849]"
  if (active) return "shadow-[inset_0_0_0_1px_#E8B849]"
  return ""
}

function RecordBlock({
  row,
  selected,
  active,
  onHover,
  onHoverEnd,
  onSelect,
}: {
  row: RadarPoint
  selected: boolean
  active: boolean
  onHover: (ticker: string) => void
  onHoverEnd: () => void
  onSelect: (ticker: string) => void
}) {
  const labels = resolveLabels(row)
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <div
            id={rowDomId(row.ticker, false)}
            role="row"
            tabIndex={0}
            aria-selected={selected}
            className={`flex min-h-11 cursor-pointer flex-col gap-2 rounded-lg border border-[#2A3140] p-3 outline-none ${focusCard} ${rowClass(active, selected)}`}
            onClick={() => onSelect(row.ticker)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                onSelect(row.ticker)
              }
            }}
            onMouseEnter={() => onHover(row.ticker)}
            onMouseLeave={onHoverEnd}
            onFocus={() => onHover(row.ticker)}
            onBlur={onHoverEnd}
          />
        }
      >
        <Field label="Ticker" value={row.ticker} mono />
        <Field label="RVOL" value={formatRvol(row.rvol)} mono />
        <Field label="Displacement" value={formatPlain(row.displacement)} mono />
        <Field label="Anomaly Score" value={formatPlain(row.anomaly_score)} mono />
        <div className="flex flex-col gap-2">
          <span className="font-sans text-xs font-medium uppercase tracking-wide text-[#9AA3B2]">
            Bargaining Power
          </span>
          {labels.en && labels.zh && row.bargaining_power ? (
            <TagBadge tag={row.bargaining_power} en={labels.en} zh={labels.zh} />
          ) : null}
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <PointDetails point={row} />
      </TooltipContent>
    </Tooltip>
  )
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="font-sans text-xs font-medium uppercase tracking-wide text-[#9AA3B2]">
        {label}
      </span>
      <span
        className={
          mono
            ? "min-w-0 text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums"
            : "min-w-0 text-right text-[#F4F1EA]"
        }
      >
        {value}
      </span>
    </div>
  )
}

function DesktopRow({
  row,
  selected,
  active,
  onHover,
  onHoverEnd,
  onSelect,
}: {
  row: RadarPoint
  selected: boolean
  active: boolean
  onHover: (ticker: string) => void
  onHoverEnd: () => void
  onSelect: (ticker: string) => void
}) {
  const labels = resolveLabels(row)
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <TableRow
            id={rowDomId(row.ticker, true)}
            tabIndex={0}
            aria-selected={selected}
            className={`cursor-pointer outline-none ${focusCard} ${rowClass(active, selected)}`}
            onClick={() => onSelect(row.ticker)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                onSelect(row.ticker)
              }
            }}
            onMouseEnter={() => onHover(row.ticker)}
            onMouseLeave={onHoverEnd}
            onFocus={() => onHover(row.ticker)}
            onBlur={onHoverEnd}
          />
        }
      >
        <TableHead
          scope="row"
          className="font-mono text-sm font-medium text-[#F4F1EA] tabular-nums"
        >
          {row.ticker}
        </TableHead>
        <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
          {formatRvol(row.rvol)}
        </TableCell>
        <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
          {formatPlain(row.displacement)}
        </TableCell>
        <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
          {formatPlain(row.anomaly_score)}
        </TableCell>
        <TableCell className="whitespace-normal">
          {labels.en && labels.zh && row.bargaining_power ? (
            <TagBadge tag={row.bargaining_power} en={labels.en} zh={labels.zh} />
          ) : null}
        </TableCell>
      </TooltipTrigger>
      <TooltipContent>
        <PointDetails point={row} />
      </TooltipContent>
    </Tooltip>
  )
}

export function leaderboardCount(count: number): string {
  return COPY.anomalyCount(formatCount(count))
}
