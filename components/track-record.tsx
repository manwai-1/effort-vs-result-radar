"use client"

import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { TagBadge } from "@/components/tag-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
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
import { COPY, HISTORY_COLUMNS } from "@/lib/copy"
import {
  formatAverage,
  formatCount,
  formatHitRate,
  formatPlain,
  formatPrice,
  formatReturn,
  formatRvol,
} from "@/lib/format"
import { resolveHistoryLabels } from "@/lib/labels"
import { cardsForFilters } from "@/lib/summary"
import { focusCard } from "@/lib/styles"
import { defaultSortDirection, sortHistory } from "@/lib/sort"
import type { HistoryFile, HistoryRecord, HistorySortKey, MarketFilter, SortState, TagKey } from "@/lib/types"

function SortIcon({ active, direction }: { active: boolean; direction: "asc" | "desc" }) {
  if (!active) return <ArrowUpDown className="size-3.5 text-[#9AA3B2]" aria-hidden />
  if (direction === "desc") return <ArrowDown className="size-3.5 text-[#9AA3B2]" aria-hidden />
  return <ArrowUp className="size-3.5 text-[#9AA3B2]" aria-hidden />
}

function ReturnValue({ value }: { value: number | null }) {
  const formatted = formatReturn(value)
  return (
    <span
      className={`font-mono text-sm font-medium tabular-nums ${
        formatted.pending ? "text-[#9AA3B2]" : "text-[#F4F1EA]"
      }`}
    >
      {formatted.text}
    </span>
  )
}

function cellValue(row: HistoryRecord, key: HistorySortKey) {
  if (key === "date") return row.date
  if (key === "ticker") return row.ticker
  if (key === "signal_price") return formatPrice(row.signal_price, row.currency)
  if (key === "rvol") return formatRvol(row.rvol)
  if (key === "displacement") return formatPlain(row.displacement)
  if (key === "anomaly_score") return formatPlain(row.anomaly_score)
  if (key === "t_plus_3_return_pct" || key === "t_plus_5_return_pct" || key === "t_plus_10_return_pct") {
    return <ReturnValue value={row[key]} />
  }
  const labels = resolveHistoryLabels(row)
  return <TagBadge tag={row.bargaining_power} en={labels.en} zh={labels.zh} />
}

export function TrackRecord({
  history,
  market,
  tags,
  sort,
  updated,
  onSort,
}: {
  history: HistoryFile
  market: MarketFilter
  tags: TagKey[]
  sort: SortState<HistorySortKey>
  updated: string | null
  onSort: (sort: SortState<HistorySortKey>) => void
}) {
  const visible = history.records.filter(
    (row) =>
      (market === "all" || row.market === market) && tags.includes(row.bargaining_power),
  )
  const cards = tags.length === 0 ? [] : cardsForFilters({
    records: history.records,
    summary: history.summary_by_tag,
    market,
    tags,
  })
  const sorted = sortHistory(visible, sort.key, sort.direction)
  const empty =
    tags.length === 0
      ? COPY.tagsOff
      : history.records.length === 0
        ? COPY.emptyLedger
        : visible.length === 0
          ? COPY.filterEmpty
          : null

  function toggle(key: HistorySortKey) {
    if (sort.key === key) {
      onSort({ key, direction: sort.direction === "asc" ? "desc" : "asc" })
      return
    }
    onSort({ key, direction: defaultSortDirection(key) })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="font-sans text-xl font-semibold tracking-tight text-[#F4F1EA]">
          {COPY.trackRecord}
        </h2>
        <p className="max-w-prose font-sans text-base font-normal leading-7 text-[#F4F1EA]">
          {COPY.intro}
        </p>
        {updated ? (
          <p className="font-mono text-xs font-normal leading-[1.4] text-[#9AA3B2] tabular-nums">
            {updated}
          </p>
        ) : null}
      </div>
      {cards.length > 0 ? (
        <div
          className={`grid grid-cols-1 gap-4 md:gap-6 ${
            cards.length >= 3 ? "md:grid-cols-3" : cards.length === 2 ? "md:grid-cols-2" : ""
          }`}
        >
          {cards.map((card) => (
            <Card key={card.bargaining_power} className="p-4">
              <TagBadge
                tag={card.bargaining_power}
                en={card.bargaining_power_label_en}
                zh={card.bargaining_power_label_zh}
              />
              <div className="mt-3 space-y-1 font-mono text-sm leading-6 text-[#F4F1EA] tabular-nums">
                <p>{COPY.sample(formatCount(card.sample_count))}</p>
                <p>{COPY.average("T+3", formatAverage(card.t_plus_3.average_return_pct))}</p>
                <p>{COPY.average("T+5", formatAverage(card.t_plus_5.average_return_pct))}</p>
                <p>{COPY.average("T+10", formatAverage(card.t_plus_10.average_return_pct))}</p>
                <p>
                  {COPY.hitRate(
                    formatHitRate(
                      card.t_plus_3.hit_rate_applicable,
                      card.t_plus_3.hit_rate_label,
                      card.t_plus_3.hit_rate_pct,
                    ),
                    formatHitRate(
                      card.t_plus_5.hit_rate_applicable,
                      card.t_plus_5.hit_rate_label,
                      card.t_plus_5.hit_rate_pct,
                    ),
                    formatHitRate(
                      card.t_plus_10.hit_rate_applicable,
                      card.t_plus_10.hit_rate_label,
                      card.t_plus_10.hit_rate_pct,
                    ),
                  )}
                </p>
              </div>
              <p lang="zh-Hant" className="mt-3 font-sans text-xs font-medium leading-[1.3] text-[#9AA3B2]">
                {COPY.footnote(
                  formatCount(card.t_plus_3.sample_count),
                  formatCount(card.t_plus_5.sample_count),
                  formatCount(card.t_plus_10.sample_count),
                )}
              </p>
            </Card>
          ))}
        </div>
      ) : null}
      {empty ? (
        <p className="max-w-prose font-sans text-base font-normal leading-7 text-[#F4F1EA]">
          {empty}
        </p>
      ) : (
        <Card>
          <CardHeader className="md:hidden">
            <div className="flex items-center gap-2">
              <Select
                value={sort.key}
                onValueChange={(value) => {
                  if (!HISTORY_COLUMNS.some((column) => column.key === value)) return
                  const key = value as HistorySortKey
                  if (key === sort.key) return
                  onSort({ key, direction: defaultSortDirection(key) })
                }}
              >
                <SelectTrigger className={focusCard} aria-label={COPY.trackRecord}>
                  <SelectValue>
                    {(value) => HISTORY_COLUMNS.find((column) => column.key === value)?.label ?? ""}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {HISTORY_COLUMNS.map((column) => (
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
                  {HISTORY_COLUMNS.find((column) => column.key === sort.key)?.label}
                </span>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-0 md:p-0">
            <div className="flex flex-col gap-3 md:hidden">
              {sorted.map((row) => (
                <div
                  key={`${row.date}-${row.ticker}`}
                  className="flex flex-col gap-2 rounded-lg border border-[#2A3140] p-3"
                >
                  {HISTORY_COLUMNS.map((column) => (
                    <div key={column.key} className="flex items-start justify-between gap-3">
                      <span className="font-sans text-xs font-medium uppercase tracking-wide text-[#9AA3B2]">
                        {column.label}
                      </span>
                      <span className="min-w-0 text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {cellValue(row, column.key)}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="hidden md:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    {HISTORY_COLUMNS.map((column) => {
                      const active = sort.key === column.key
                      return (
                        <TableHead
                          key={column.key}
                          aria-sort={
                            active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"
                          }
                          className="p-0"
                        >
                          <Button
                            type="button"
                            variant="ghost"
                            className={`min-h-11 w-full rounded-none px-2 ${focusCard} ${
                              column.numeric ? "justify-end" : "justify-start"
                            }`}
                            onClick={() => toggle(column.key)}
                          >
                            <span className="font-sans text-xs font-medium uppercase tracking-wide text-[#9AA3B2]">
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
                  {sorted.map((row) => (
                    <TableRow key={`${row.date}-${row.ticker}`}>
                      <TableHead scope="row" className="font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {row.date}
                      </TableHead>
                      <TableHead scope="row" className="font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {row.ticker}
                      </TableHead>
                      <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {formatPrice(row.signal_price, row.currency)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {formatRvol(row.rvol)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {formatPlain(row.displacement)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-medium text-[#F4F1EA] tabular-nums">
                        {formatPlain(row.anomaly_score)}
                      </TableCell>
                      <TableCell>
                        <TagBadge
                          tag={row.bargaining_power}
                          en={resolveHistoryLabels(row).en}
                          zh={resolveHistoryLabels(row).zh}
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <ReturnValue value={row.t_plus_3_return_pct} />
                      </TableCell>
                      <TableCell className="text-right">
                        <ReturnValue value={row.t_plus_5_return_pct} />
                      </TableCell>
                      <TableCell className="text-right">
                        <ReturnValue value={row.t_plus_10_return_pct} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
