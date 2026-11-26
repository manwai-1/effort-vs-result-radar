import assert from "node:assert/strict"
import test from "node:test"
import { chartDomain } from "./domain"
import { historyKind, leaderboardKind, showNoAnomalyCaption } from "./view-state"
import type { FilterPoint } from "./view-state"

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

test("the scatter domain keeps the stated floors and expands for outliers", () => {
  assert.deepEqual(chartDomain([]), { xMin: 0, xMax: 4, yMin: 0, yMax: 2 })
  assert.deepEqual(chartDomain([{ rvol: 6.5, displacement: 3 }]), {
    xMin: 0,
    xMax: 6.825,
    yMin: 0,
    yMax: 3.15,
  })
})
