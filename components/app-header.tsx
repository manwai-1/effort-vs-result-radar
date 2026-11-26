import { Clock, RefreshCw } from "lucide-react"
import { MethodologyDialog } from "@/components/methodology-dialog"
import { RadarMark } from "@/components/radar-mark"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { COPY } from "@/lib/copy"
import { focusCard } from "@/lib/styles"

export function AppHeader({
  lastScan,
  stale,
  busy,
  onRefresh,
}: {
  lastScan: string
  stale: string | null
  busy: boolean
  onRefresh: () => void
}) {
  return (
    <header className="py-20">
      <div className="mx-auto w-full max-w-[1280px] px-4 md:px-8">
        <div className="rounded-lg border border-[#2A3140] bg-[#12161C] px-4 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <RadarMark />
              <h1 className="min-w-0 font-sans text-2xl font-semibold tracking-tight text-[#F4F1EA] md:text-3xl">
                {COPY.title}
              </h1>
            </div>
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-2">
              <p className="flex items-center gap-2 font-mono text-xs font-normal leading-[1.4] text-[#9AA3B2]">
                <Clock className="size-3.5 shrink-0" aria-hidden />
                <span>{lastScan}</span>
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  className={`min-h-11 min-w-11 flex-1 gap-2 md:flex-none ${focusCard}`}
                  onClick={onRefresh}
                  disabled={busy}
                  aria-busy={busy}
                >
                  <RefreshCw
                    className={busy ? "size-4 motion-safe:animate-spin" : "size-4"}
                    aria-hidden
                  />
                  {COPY.refresh}
                </Button>
                <MethodologyDialog />
              </div>
            </div>
          </div>
          {stale ? (
            <Alert className="mt-4 border-[#2A3140] bg-[#12161C] text-[#F4F1EA]">
              <AlertDescription className="font-sans text-base font-normal leading-7 text-[#F4F1EA]">
                {stale}
              </AlertDescription>
            </Alert>
          ) : null}
        </div>
      </div>
    </header>
  )
}
