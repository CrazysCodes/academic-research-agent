import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import Link from "next/link"
import { AppInitializer } from "@/components/layout/AppInitializer"
import { NavLinks } from "@/components/layout/NavLinks"
import "./globals.css"

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] })
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] })

export const metadata: Metadata = {
  title: "学术研究 Agent",
  description: "文献上传、检索问答、多文档对比分析",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
          <nav className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-4">
            <Link href="/" className="text-sm font-semibold shrink-0">
              学术研究 Agent
            </Link>
            <NavLinks />
          </nav>
        </header>
        <AppInitializer />
        <main>{children}</main>
      </body>
    </html>
  )
}
