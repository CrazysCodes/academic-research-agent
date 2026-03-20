"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

const NAV_LINKS = [
  { href: "/chat", label: "问答" },
  { href: "/analyze", label: "分析" },
  { href: "/papers", label: "文献库" },
]

const SETTINGS_LINK = { href: "/settings", label: "设置" }

export function NavLinks() {
  const pathname = usePathname()

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/")

  return (
    <>
      {NAV_LINKS.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            "text-sm transition-colors hover:text-foreground",
            isActive(href) ? "font-semibold text-foreground" : "text-muted-foreground",
          )}
        >
          {label}
        </Link>
      ))}
      <Link
        href={SETTINGS_LINK.href}
        className={cn(
          "ml-auto text-sm transition-colors hover:text-foreground",
          isActive(SETTINGS_LINK.href) ? "font-semibold text-foreground" : "text-muted-foreground",
        )}
      >
        {SETTINGS_LINK.label}
      </Link>
    </>
  )
}
