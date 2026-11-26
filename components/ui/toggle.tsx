"use client"

import { Toggle as TogglePrimitive } from "@base-ui/react/toggle"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

const toggleVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md border border-[#2A3140] bg-transparent text-sm font-medium whitespace-normal text-[#F4F1EA] outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E8B849] focus-visible:ring-offset-2 focus-visible:ring-offset-[#07090C] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        default: "bg-transparent",
        outline: "border-[#2A3140] bg-transparent",
      },
      size: {
        default: "min-h-11 min-w-11 px-3 py-2",
        sm: "min-h-11 min-w-11 px-2.5",
        lg: "min-h-11 min-w-11 px-3",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

function Toggle({
  className,
  variant = "default",
  size = "default",
  ...props
}: TogglePrimitive.Props & VariantProps<typeof toggleVariants>) {
  return (
    <TogglePrimitive
      data-slot="toggle"
      className={cn(toggleVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Toggle, toggleVariants }
