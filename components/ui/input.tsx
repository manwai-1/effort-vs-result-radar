import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"
import { cn } from "cn"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "min-h-11 w-full min-w-0 rounded-md border border-[#2A3140] bg-transparent px-2.5 py-1 text-sm text-[#F4F1EA] outline-none placeholder:text-[#9AA3B2] focus-visible:ring-2 focus-visible:ring-[#E8B849] focus-visible:ring-offset-2 focus-visible:ring-offset-[#12161C] disabled:pointer-events-none disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Input }
