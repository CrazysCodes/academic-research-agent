import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import Link from "next/link"
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
            <Link href="/" className="text-sm font-semibold">
              学术研究 Agent
            </Link>
            <Link
              href="/papers"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              文献库
            </Link>
            <Link
              href="/chat"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              问答
            </Link>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  )
}
