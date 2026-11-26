import { BookOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { COPY } from "@/lib/copy"
import { focusCard } from "@/lib/styles"

export function MethodologyDialog() {
  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button
            type="button"
            variant="ghost"
            className={`min-h-11 min-w-11 flex-1 gap-2 md:flex-none ${focusCard}`}
          />
        }
      >
        <BookOpen className="size-4" aria-hidden />
        {COPY.methodology}
      </DialogTrigger>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle className="font-sans text-xl font-semibold tracking-tight text-[#F4F1EA]">
            {COPY.methodology}
          </DialogTitle>
        </DialogHeader>
        <div className="max-w-prose space-y-3">
          {COPY.formulas.map((line) => (
            <p
              key={line}
              className="font-mono text-base font-normal leading-7 text-[#F4F1EA]"
            >
              {line}
            </p>
          ))}
        </div>
        <DialogDescription className="max-w-prose font-sans text-base font-normal leading-7 text-[#F4F1EA]">
          {COPY.scanSentence}
        </DialogDescription>
        <DialogClose
          render={
            <Button type="button" variant="ghost" className={`min-h-11 ${focusCard}`} />
          }
        >
          {COPY.close}
        </DialogClose>
      </DialogContent>
    </Dialog>
  )
}
