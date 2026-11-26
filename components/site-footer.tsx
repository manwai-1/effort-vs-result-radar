import { COPY } from "@/lib/copy"
import { Separator } from "@/components/ui/separator"

export function SiteFooter() {
  return (
    <>
      <div className="mx-auto w-full max-w-[1280px] px-4 md:px-8">
        <Separator />
      </div>
      <footer className="py-20">
        <div className="mx-auto w-full max-w-[1280px] px-4 md:px-8">
          <div className="max-w-prose space-y-4">
            {COPY.footer.map((sentence) => (
              <p
                key={sentence}
                lang="zh-Hant"
                className="font-sans text-base font-normal leading-7 text-[#9AA3B2]"
              >
                {sentence}
              </p>
            ))}
          </div>
        </div>
      </footer>
    </>
  )
}
