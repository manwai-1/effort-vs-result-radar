import assert from "node:assert/strict"
import test from "node:test"
import { tagLine } from "../components/point-details"
import { chartDomain } from "./domain"
import { anomalyInLeaderboard, historyKind, leaderboardKind, showNoAnomalyCaption } from "./view-state"
import type { FilterPoint } from "./view-state"
import type { RadarPoint } from "./types"

const points: FilterPoint[] = [
  { market: "US", is_anomaly: true, bargaining_power: "buyer_absorption" },
  { market: "HK", is_anomaly: false, bargaining_power: null },
]

test("filters distinguish a real empty scan from a filter that hid anomalies", () => {
  assert.equal(leaderboardKind(points, "all", ["buyer_absorption", "seller_distribution", "stalemate_compression"]), "rows")
  assert.equal(leaderboardKind(points, "HK", ["buyer_absorption", "seller_distribution", "stalemate_compression"]), "filtered-out")
  assert.equal(leaderboardKind(points, "all", []), "tags-off")
  assert.equal(leaderboardKind([], "all", ["buyer_absorption", "seller_distribution", "stalemate_compression"]), "no-anomalies")
  assert.equal(showNoAnomalyCaption(points, "HK"), true)
  assert.equal(showNoAnomalyCaption(points, "US"), false)
  assert.equal(historyKind(0, 0, ["buyer_absorption"]), "empty-ledger")
  assert.equal(historyKind(2, 0, ["buyer_absorption"]), "filtered-out")
  assert.equal(historyKind(2, 0, []), "tags-off")
})

const allTags = ["buyer_absorption", "seller_distribution", "stalemate_compression"] as const

test("tag filters drop tagged leaderboard rows and keep null-tag anomalies", () => {
  const seller: FilterPoint = {
    market: "US",
    is_anomaly: true,
    bargaining_power: "seller_distribution",
  }
  const nullTag: FilterPoint = { market: "US", is_anomaly: true, bargaining_power: null }
  const plain: FilterPoint = { market: "US", is_anomaly: false, bargaining_power: null }
  assert.equal(anomalyInLeaderboard(nullTag, "all", [...allTags]), true)
  assert.equal(anomalyInLeaderboard(nullTag, "all", []), true)
  assert.equal(anomalyInLeaderboard(seller, "all", [...allTags]), true)
  assert.equal(
    anomalyInLeaderboard(seller, "all", ["buyer_absorption", "stalemate_compression"]),
    false,
  )
  assert.equal(anomalyInLeaderboard(plain, "all", [...allTags]), false)
  assert.equal(leaderboardKind([seller, nullTag], "all", []), "rows")
  assert.equal(leaderboardKind([seller], "all", []), "tags-off")
})

test("未標記 is only for a non-anomaly", () => {
  const base = {
    market: "US" as const,
    rvol: 2.2,
    displacement: 0.3,
    anomaly_score: 7,
    trend_20d: "sideways" as const,
    last_price: 10,
    currency: "USD",
  }
  const nullTag: RadarPoint = {
    ...base,
    ticker: "NULLTAG",
    is_anomaly: true,
    bargaining_power: null,
    bargaining_power_label_en: null,
    bargaining_power_label_zh: null,
  }
  const missingLabel: RadarPoint = {
    ...base,
    ticker: "0005.HK",
    is_anomaly: true,
    bargaining_power: "seller_distribution",
    bargaining_power_label_en: null,
    bargaining_power_label_zh: null,
  }
  const quiet: RadarPoint = {
    ...base,
    ticker: "QUIET",
    is_anomaly: false,
    bargaining_power: null,
    bargaining_power_label_en: null,
    bargaining_power_label_zh: null,
  }
  assert.equal(tagLine(nullTag), null)
  assert.equal(tagLine(missingLabel), "Seller Distribution (賣方暗中出貨)")
  assert.equal(tagLine(quiet), "未標記")
})

test("the scatter domain keeps the stated floors and expands for outliers", () => {
  assert.deepEqual(chartDomain([]), { xMin: 0, xMax: 4, yMin: 0, yMax: 2 })
  assert.deepEqual(chartDomain([{ rvol: 6.5, displacement: 3 }]), {
    xMin: 0,
    xMax: 6.825,
    yMin: 0,
    yMax: 3.15,
  })
})
