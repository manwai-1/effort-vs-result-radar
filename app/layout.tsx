import type { Metadata } from "next"
import { IBM_Plex_Mono, IBM_Plex_Sans, Noto_Sans_TC } from "next/font/google"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./globals.css"

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-plex-sans",
  display: "swap",
})

const notoSansTc = Noto_Sans_TC({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-noto-sans-tc",
  display: "swap",
  preload: false,
})

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-ibm-plex-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Effort vs Result Radar",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${notoSansTc.variable} ${plexMono.variable} h-full`}
    >
      <body className="min-h-full bg-[#07090C] text-[#F4F1EA] antialiased">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  )
}
