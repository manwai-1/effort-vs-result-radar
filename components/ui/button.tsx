import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-transparent text-sm font-medium whitespace-normal outline-none select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#E8B849] focus-visible:ring-offset-2 focus-visible:ring-offset-[#07090C] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-[#E8B849] text-[#07090C] hover:opacity-90",
        outline:
          "border-[#2A3140] bg-transparent text-[#F4F1EA] hover:border-[#E8B849]",
        secondary: "border-[#2A3140] bg-[#12161C] text-[#F4F1EA]",
        ghost: "bg-transparent text-[#F4F1EA] hover:border-[#2A3140]",
        destructive: "border-[#2A3140] bg-transparent text-[#F4F1EA]",
        link: "text-[#E8B849] underline-offset-4 hover:underline",
      },
      size: {
        default: "min-h-11 min-w-11 px-3 py-2",
        xs: "min-h-11 min-w-11 px-2 text-xs",
        sm: "min-h-11 min-w-11 px-2.5",
        lg: "min-h-11 min-w-11 px-4",
        icon: "size-11",
        "icon-xs": "size-11",
        "icon-sm": "size-11",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Button, buttonVariants }
