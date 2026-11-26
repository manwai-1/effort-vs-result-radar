import { RefreshCw } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { COPY } from "@/lib/copy"
import { focusCard } from "@/lib/styles"

export function FileAlert({
  message,
  busy,
  onRefresh,
}: {
  message: string
  busy: boolean
  onRefresh: () => void
}) {
  return (
    <Alert className="border-[#2A3140] bg-[#12161C] text-[#F4F1EA]">
      <AlertDescription className="font-sans text-base font-normal leading-7 text-[#F4F1EA]">
        {message}
      </AlertDescription>
      <Button
        type="button"
        className={`mt-3 min-h-11 ${focusCard}`}
        onClick={onRefresh}
        disabled={busy}
        aria-busy={busy}
      >
        <RefreshCw className={busy ? "size-4 motion-safe:animate-spin" : "size-4"} aria-hidden />
        {COPY.refresh}
      </Button>
    </Alert>
  )
}
