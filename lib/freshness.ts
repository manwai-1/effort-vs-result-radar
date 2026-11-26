import { formatHongKong } from "@/lib/format"

export const STALE_MS = 72 * 60 * 60 * 1000

export function isStaleGeneratedAt(iso: string, now: number): boolean {
  const timestamp = Date.parse(iso)
  if (Number.isNaN(timestamp)) return false
  return now - timestamp > STALE_MS
}

export function lastScanCopy(input: {
  status: "loading" | "error" | "ready"
  dataStatus?: string
  generatedAt?: string
}): string {
  if (input.status === "loading") return "最近掃描：載入中"
  if (input.status !== "ready" || input.dataStatus === "empty_fixture" || !input.generatedAt) {
    return "最近掃描：時間未有提供"
  }
  const formatted = formatHongKong(input.generatedAt)
  if (!formatted) return "最近掃描：時間未有提供"
  return `最近掃描：${formatted} 香港時間`
}

export function staleNotice(input: {
  status: "loading" | "error" | "ready"
  dataStatus?: string
  generatedAt?: string
  now: number
}): string | null {
  if (input.status !== "ready") return null
  if (input.dataStatus === "empty_fixture") return null
  if (!input.generatedAt) return null
  if (!isStaleGeneratedAt(input.generatedAt, input.now)) return null
  return "掃描時間已超過 72 小時，資料可能已過時。"
}

export function ledgerUpdatedCopy(input: {
  dataStatus?: string
  updatedAt?: string
}): string | null {
  if (input.dataStatus === "empty_fixture" || !input.updatedAt) return null
  const formatted = formatHongKong(input.updatedAt)
  if (!formatted) return null
  return `Ledger updated ${formatted} 香港時間`
}
