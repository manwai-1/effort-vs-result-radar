const MINUS = "\u2212"

export function roundHalfAwayFromZero(value: number, places: number): number {
  if (!Number.isFinite(value)) return value
  const negative = value < 0
  const text = Math.abs(value).toString()
  const normalized = /e/i.test(text) ? Math.abs(value).toFixed(places + 8) : text
  const [intRaw, fracRaw = ""] = normalized.split(".")
  const digits = (fracRaw + "0".repeat(places + 1)).slice(0, places + 1)
  let keep = places > 0 ? digits.slice(0, places) : ""
  const next = Number(digits[places] ?? "0")
  let whole = Number(intRaw)
  if (next >= 5) {
    if (places === 0) {
      whole += 1
    } else {
      const incremented = String(Number(keep || "0") + 1)
      if (incremented.length > keep.length) {
        whole += 1
        keep = "0".repeat(places)
      } else {
        keep = incremented.padStart(places, "0")
      }
    }
  }
  const body = places > 0 ? `${whole}.${keep}` : String(whole)
  const result = Number(body)
  if (result === 0) return 0
  return negative ? -result : result
}

export function formatFixed(value: number, decimals: number): string {
  const rounded = roundHalfAwayFromZero(value, decimals)
  const negative = rounded < 0
  const [whole, frac = ""] = Math.abs(rounded).toFixed(decimals).split(".")
  const body = decimals > 0 ? `${whole}.${frac}` : whole
  return negative ? `-${body}` : body
}

export function formatCount(value: number): string {
  const rounded = Math.round(value)
  if (Math.abs(rounded) > 999) return rounded.toLocaleString("en-US")
  return String(rounded)
}

export function formatRvol(value: number): string {
  return `${formatFixed(value, 2)}\u00d7`
}

export function formatPlain(value: number): string {
  return formatFixed(value, 2)
}

export function formatTick(value: number): string {
  return formatFixed(value, 2)
    .replace(/\.00$/, "")
    .replace(/(\.\d)0$/, "$1")
}

export function formatReturn(value: number | null): { text: string; pending: boolean } {
  if (value === null) return { text: "待補", pending: true }
  const fixed = formatFixed(value, 2)
  if (fixed.startsWith("-")) return { text: `${MINUS}${fixed.slice(1)}%`, pending: false }
  return { text: `+${fixed}%`, pending: false }
}

export function formatAverage(value: number | null): string {
  if (value === null) return "尚無"
  return formatReturn(value).text
}

export function formatHitRate(
  applicable: boolean,
  label: string | null,
  pct: number | null,
): string {
  if (!applicable || label === "不適用") return "不適用"
  if (pct === null) return "尚無"
  return `${formatFixed(pct, 2)}%`
}

export function formatPrice(value: number, currency?: string | null): string {
  const amount = formatFixed(value, 2)
  return currency ? `${amount} ${currency}` : amount
}

export function formatHongKong(iso: string): string | null {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Hong_Kong",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date)
  const pick = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ""
  const year = pick("year")
  const month = pick("month")
  const day = pick("day")
  const hour = pick("hour")
  const minute = pick("minute")
  if (!year || !month || !day || hour === "" || minute === "") return null
  return `${year}-${month}-${day} ${hour}:${minute}`
}
