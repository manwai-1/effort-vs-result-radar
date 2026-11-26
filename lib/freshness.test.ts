import assert from "node:assert/strict"
import test from "node:test"
import { STALE_MS, isStaleGeneratedAt, lastScanCopy, staleNotice } from "./freshness"

test("empty fixtures do not display the epoch or the stale notice", () => {
  assert.equal(
    lastScanCopy({
      status: "ready",
      dataStatus: "empty_fixture",
      generatedAt: "1970-01-01T00:00:00+00:00",
    }),
    "最近掃描：時間未有提供",
  )
  assert.equal(
    staleNotice({
      status: "ready",
      dataStatus: "empty_fixture",
      generatedAt: "1970-01-01T00:00:00+00:00",
      now: Date.parse("2026-11-27T00:00:00Z"),
    }),
    null,
  )
})

test("a real generated_at is shown, and stale starts after 72 hours", () => {
  const generatedAt = "2026-11-24T00:00:00Z"
  const now = Date.parse(generatedAt)
  assert.equal(isStaleGeneratedAt(generatedAt, now + STALE_MS), false)
  assert.equal(isStaleGeneratedAt(generatedAt, now + STALE_MS + 1), true)
  assert.equal(
    lastScanCopy({ status: "ready", generatedAt }),
    "最近掃描：2026-11-24 08:00 香港時間",
  )
  assert.equal(
    staleNotice({ status: "ready", generatedAt, now: now + STALE_MS + 1 }),
    "掃描時間已超過 72 小時，資料可能已過時。",
  )
  assert.equal(lastScanCopy({ status: "loading" }), "最近掃描：載入中")
  assert.equal(lastScanCopy({ status: "ready" }), "最近掃描：時間未有提供")
})
