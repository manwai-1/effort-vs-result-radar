import assert from "node:assert/strict"
import test from "node:test"
import {
  formatCount,
  formatFixed,
  formatHongKong,
  formatReturn,
  formatRvol,
  roundHalfAwayFromZero,
} from "./format"

test("half away from zero rounds the displayed decimals", () => {
  assert.equal(roundHalfAwayFromZero(1.005, 2), 1.01)
  assert.equal(roundHalfAwayFromZero(-1.005, 2), -1.01)
  assert.equal(roundHalfAwayFromZero(1.004, 2), 1)
  assert.equal(formatFixed(1.2, 2), "1.20")
  assert.equal(formatFixed(-0.8, 2), "-0.80")
})

test("returns use a signed percent and a unicode minus", () => {
  assert.deepEqual(formatReturn(1.25), { text: "+1.25%", pending: false })
  assert.deepEqual(formatReturn(0), { text: "+0.00%", pending: false })
  assert.equal(formatReturn(-0.8).text, "\u22120.80%")
  assert.deepEqual(formatReturn(null), { text: "待補", pending: true })
})

test("rvol uses a multiplication sign and counts group only above 999", () => {
  assert.equal(formatRvol(2.4), "2.40\u00d7")
  assert.equal(formatCount(999), "999")
  assert.equal(formatCount(1000), "1,000")
  assert.equal(formatCount(0), "0")
})

test("timestamps render in Asia/Hong_Kong", () => {
  assert.equal(formatHongKong("2026-11-27T16:00:00Z"), "2026-11-28 00:00")
  assert.equal(formatHongKong("not-a-date"), null)
})
