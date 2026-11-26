"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { History, Radar } from "lucide-react"
import { AppHeader } from "@/components/app-header"
import { FileAlert } from "@/components/file-alert"
import { FiltersBar } from "@/components/filters-bar"
import { Leaderboard, leaderboardCount } from "@/components/leaderboard"
import { ScatterPlot } from "@/components/scatter-plot"
import { SiteFooter } from "@/components/site-footer"
import { TrackRecord } from "@/components/track-record"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { COPY } from "@/lib/copy"
import { lastScanCopy, ledgerUpdatedCopy, staleNotice } from "@/lib/freshness"
import { parseHistory, parseRadar } from "@/lib/parse"
import { sortLeaderboard } from "@/lib/sort"
import { anomalyInLeaderboard, showNoAnomalyCaption } from "@/lib/view-state"
import type {
  HistoryFile,
  HistorySortKey,
  LeaderboardSortKey,
  LoadState,
  MarketFilter,
  RadarFile,
  SortState,
  TagKey,
} from "@/lib/types"
import { TAG_ORDER } from "@/lib/types"

async function fetchJson(path: string): Promise<unknown> {
  const response = await fetch(path, { cache: "no-store" })
  if (!response.ok) throw new Error(String(response.status))
  return response.json() as Promise<unknown>
}

export function RadarApp() {
  const [radar, setRadar] = useState<LoadState<RadarFile>>({ status: "loading" })
  const [history, setHistory] = useState<LoadState<HistoryFile>>({ status: "loading" })
  const [busy, setBusy] = useState(true)
  const [view, setView] = useState("live")
  const [market, setMarket] = useState<MarketFilter>("all")
  const [tags, setTags] = useState<TagKey[]>([...TAG_ORDER])
  const [leaderboardSort, setLeaderboardSort] = useState<SortState<LeaderboardSortKey>>({
    key: "anomaly_score",
    direction: "desc",
  })
  const [historySort, setHistorySort] = useState<SortState<HistorySortKey>>({
    key: "date",
    direction: "desc",
  })
  const [page, setPage] = useState(1)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [activeTicker, setActiveTicker] = useState<string | null>(null)
  const [pointer, setPointer] = useState<"chart" | "row" | null>(null)
  const [loadedAt, setLoadedAt] = useState<number | null>(null)
  const requestId = useRef(0)
  const tagKey = tags.join("|")
  const pageKey = `${market}|${tagKey}|${leaderboardSort.key}|${leaderboardSort.direction}`
  const [pageKeySeen, setPageKeySeen] = useState(pageKey)
  if (pageKeySeen !== pageKey) {
    setPageKeySeen(pageKey)
    setPage(1)
  }

  const load = useCallback(async () => {
    const id = ++requestId.current
    setBusy(true)
    const [radarResult, historyResult] = await Promise.all([
      fetchJson("/data/radar.json")
        .then((payload) => parseRadar(payload))
        .catch(() => null),
      fetchJson("/data/history_results.json")
        .then((payload) => parseHistory(payload))
        .catch(() => null),
    ])
    if (id !== requestId.current) return
    setLoadedAt(Date.now())
    setRadar(radarResult ? { status: "ready", data: radarResult } : { status: "error" })
    setHistory(historyResult ? { status: "ready", data: historyResult } : { status: "error" })
    setBusy(false)
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const points = useMemo(
    () => (radar.status === "ready" ? radar.data.points : []),
    [radar],
  )
  const plotted = useMemo(
    () => points.filter((point) => market === "all" || point.market === market),
    [points, market],
  )
  const anomalies = useMemo(
    () => plotted.filter((point) => anomalyInLeaderboard(point, market, tags)),
    [plotted, market, tags],
  )
  if (
    selectedTicker &&
    radar.status === "ready" &&
    !anomalies.some((point) => point.ticker === selectedTicker)
  ) {
    setSelectedTicker(null)
  }

  const scanLine = lastScanCopy({
    status: radar.status,
    dataStatus: radar.status === "ready" ? radar.data.data_status : undefined,
    generatedAt: radar.status === "ready" ? radar.data.generated_at : undefined,
  })
  const stale =
    loadedAt === null
      ? null
      : staleNotice({
          status: radar.status,
          dataStatus: radar.status === "ready" ? radar.data.data_status : undefined,
          generatedAt: radar.status === "ready" ? radar.data.generated_at : undefined,
          now: loadedAt,
        })
  const updated =
    history.status === "ready"
      ? ledgerUpdatedCopy({
          dataStatus: history.data.data_status,
          updatedAt: history.data.updated_at,
        })
      : null

  const leaderboardEmpty =
    anomalies.length > 0
      ? null
      : tags.length === 0
        ? COPY.tagsOff
        : points.some((point) => point.is_anomaly)
          ? COPY.filterEmpty
          : COPY.noAnomalies

  function selectAnomaly(ticker: string) {
    setSelectedTicker(ticker)
    const sorted = sortLeaderboard(anomalies, leaderboardSort.key, leaderboardSort.direction)
    const index = sorted.findIndex((point) => point.ticker === ticker)
    if (index >= 0 && sorted.length > 100) setPage(Math.floor(index / 50) + 1)
  }

  return (
    <div className="min-h-screen bg-[#07090C] text-[#F4F1EA]">
      <AppHeader lastScan={scanLine} stale={stale} busy={busy} onRefresh={() => void load()} />
      <main className="py-20">
        <div className="mx-auto w-full max-w-[1280px] space-y-6 px-4 md:px-8">
          <FiltersBar market={market} tags={tags} onMarket={setMarket} onTags={setTags} />
          <Tabs
            value={view}
            onValueChange={(value) => {
              if (value === "live" || value === "record") setView(value)
            }}
          >
            <TabsList activateOnFocus className="w-full md:w-fit">
              <TabsTrigger value="live">
                <Radar className="size-4" aria-hidden />
                {COPY.liveRadar}
              </TabsTrigger>
              <TabsTrigger value="record">
                <History className="size-4" aria-hidden />
                {COPY.trackRecord}
              </TabsTrigger>
            </TabsList>
            <TabsContent value="live">
              {radar.status === "loading" ? <LiveSkeleton /> : null}
              {radar.status === "error" ? (
                <FileAlert message={COPY.radarError} busy={busy} onRefresh={() => void load()} />
              ) : null}
              {radar.status === "ready" ? (
                <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-[minmax(0,1.4fr)_minmax(360px,1fr)]">
                  <div className="min-w-0">
                    <ScatterPlot
                      points={plotted}
                      tags={tags}
                      activeTicker={activeTicker}
                      selectedTicker={selectedTicker}
                      showTooltip={pointer === "chart" && activeTicker !== null}
                      showCaption={showNoAnomalyCaption(points, market)}
                      onActivate={(ticker) => {
                        setActiveTicker(ticker)
                        setPointer("chart")
                      }}
                      onClear={() => {
                        setActiveTicker(null)
                        setPointer(null)
                      }}
                      onSelect={selectAnomaly}
                    />
                  </div>
                  <div className="min-w-0">
                    <Leaderboard
                      rows={anomalies}
                      countLabel={
                        anomalies.length > 0
                          ? leaderboardCount(anomalies.length)
                          : leaderboardEmpty === COPY.noAnomalies
                            ? leaderboardCount(0)
                            : null
                      }
                      empty={leaderboardEmpty}
                      sort={leaderboardSort}
                      page={page}
                      activeTicker={activeTicker}
                      selectedTicker={selectedTicker}
                      onSort={setLeaderboardSort}
                      onPage={setPage}
                      onHover={(ticker) => {
                        setActiveTicker(ticker)
                        setPointer("row")
                      }}
                      onHoverEnd={() => {
                        setActiveTicker(null)
                        setPointer(null)
                      }}
                      onSelect={selectAnomaly}
                    />
                  </div>
                </div>
              ) : null}
            </TabsContent>
            <TabsContent value="record">
              {history.status === "loading" ? <HistorySkeleton /> : null}
              {history.status === "error" ? (
                <FileAlert message={COPY.historyError} busy={busy} onRefresh={() => void load()} />
              ) : null}
              {history.status === "ready" ? (
                <TrackRecord
                  history={history.data}
                  market={market}
                  tags={tags}
                  sort={historySort}
                  updated={updated}
                  onSort={setHistorySort}
                />
              ) : null}
            </TabsContent>
          </Tabs>
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}

function LiveSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1.4fr)_minmax(360px,1fr)]">
      <Skeleton className="h-[280px] w-full md:h-[480px]" />
      <div className="space-y-2">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} className="h-11 w-full" />
        ))}
      </div>
    </div>
  )
}

function HistorySkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-6">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} className="h-11 w-full" />
        ))}
      </div>
    </div>
  )
}
