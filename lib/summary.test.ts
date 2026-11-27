import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"
import { parseHistory, parseRadar } from "./parse"
import { cardsForFilters, summarize } from "./summary"
import type { HistoryRecord, TagKey } from "./types"

const OFFSET_TIMESTAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$/

function row(
  tag: TagKey,
  returns: [number | null, number | null, number | null],
): HistoryRecord {
  return {
    date: "2026-11-20",
    ticker: tag,
    market: "US",
    signal_price: 10,
    currency: "USD",
    rvol: 2.4,
    displacement: 0.2,
    anomaly_score: 12,
    bargaining_power: tag,
    bargaining_power_label_en: tag,
    bargaining_power_label_zh: tag,
    t_plus_3_return_pct: returns[0],
    t_plus_5_return_pct: returns[1],
    t_plus_10_return_pct: returns[2],
  }
}

test("summary rules exclude nulls, ignore a flat zero, and mark stalemate inapplicable", () => {
  const summary = summarize([
    row("buyer_absorption", [1, 0, null]),
    row("buyer_absorption", [null, null, null]),
    row("seller_distribution", [-2, null, null]),
    row("stalemate_compression", [1, -1, 0]),
  ])
  const absorption = summary[0]
  assert.equal(absorption.sample_count, 2)
  assert.equal(absorption.t_plus_3.sample_count, 1)
  assert.equal(absorption.t_plus_3.average_return_pct, 1)
  assert.equal(absorption.t_plus_3.hit_rate_pct, 100)
  assert.equal(absorption.t_plus_5.sample_count, 1)
  assert.equal(absorption.t_plus_5.average_return_pct, 0)
  assert.equal(absorption.t_plus_5.hit_rate_pct, 0)
  assert.equal(absorption.t_plus_10.average_return_pct, null)
  assert.equal(absorption.t_plus_10.hit_rate_pct, null)

  const distribution = summary[1]
  assert.equal(distribution.t_plus_3.hit_rate_pct, 100)

  const stalemate = summary[2]
  assert.equal(stalemate.t_plus_3.hit_rate_applicable, false)
  assert.equal(stalemate.t_plus_3.hit_rate_label, "不適用")
  assert.equal(stalemate.t_plus_3.hit_rate_pct, null)
  assert.equal(stalemate.t_plus_3.average_return_pct, 1)
  assert.equal(stalemate.t_plus_10.average_return_pct, 0)
})

test("an empty horizon average is null rather than zero", () => {
  const [absorption] = summarize([row("buyer_absorption", [null, null, null])])
  assert.equal(absorption.sample_count, 1)
  assert.equal(absorption.t_plus_3.average_return_pct, null)
  assert.equal(absorption.t_plus_3.sample_count, 0)
})

test("unfiltered cards use summary_by_tag and a narrowed market recomputes", () => {
  const history = parseHistory(JSON.parse(readFileSync("tests/fixtures/empty_history.json", "utf8")))
  assert.ok(history)
  const cards = cardsForFilters({
    records: history.records,
    summary: history.summary_by_tag,
    market: "all",
    tags: ["buyer_absorption", "seller_distribution", "stalemate_compression"],
  })
  assert.equal(cards[0].sample_count, 0)
  assert.equal(cards[0].t_plus_3.average_return_pct, null)
  assert.equal(cards[2].t_plus_3.hit_rate_label, "不適用")

  const narrowed = cardsForFilters({
    records: [row("buyer_absorption", [2, null, null]), { ...row("buyer_absorption", [4, null, null]), market: "HK", ticker: "0700.HK" }],
    summary: history.summary_by_tag,
    market: "HK",
    tags: ["buyer_absorption", "seller_distribution", "stalemate_compression"],
  })
  assert.equal(narrowed.find((card) => card.bargaining_power === "buyer_absorption")?.sample_count, 1)
  assert.equal(narrowed.find((card) => card.bargaining_power === "buyer_absorption")?.t_plus_3.average_return_pct, 4)
})

test("an empty radar fixture parses as an empty fixture", () => {
  const radar = parseRadar(JSON.parse(readFileSync("tests/fixtures/empty_radar.json", "utf8")))
  assert.equal(radar?.data_status, "empty_fixture")
  assert.equal(radar?.points.length, 0)
  assert.equal(
    parseRadar({
      data_status: "empty_fixture",
      points: [
        {
          ticker: "FIX",
          market: "US",
          rvol: 1,
          displacement: 1,
          anomaly_score: 1,
          is_anomaly: false,
          trend_20d: "sideways",
          bargaining_power: null,
          bargaining_power_label_en: null,
          bargaining_power_label_zh: null,
        },
      ],
    }),
    null,
  )
})

test("committed public data parses as a live scan", () => {
  const radarRaw = JSON.parse(readFileSync("public/data/radar.json", "utf8"))
  const historyRaw = JSON.parse(readFileSync("public/data/history_results.json", "utf8"))
  const radar = parseRadar(radarRaw)
  const history = parseHistory(historyRaw)
  assert.ok(radar)
  assert.ok(history)
  assert.equal(Object.hasOwn(radarRaw, "data_status"), false)
  assert.equal(Object.hasOwn(historyRaw, "data_status"), false)
  assert.equal(radar.data_status, undefined)
  assert.equal(history.data_status, undefined)
  assert.match(radar.generated_at ?? "", OFFSET_TIMESTAMP)
  assert.match(history.updated_at ?? "", OFFSET_TIMESTAMP)
})
