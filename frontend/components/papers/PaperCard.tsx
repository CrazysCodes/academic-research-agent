"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Check, ChevronDown, ExternalLink } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { fetchPaperStatus, deletePaper, generateCitation } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import type { CitationFormat, Paper } from "@/types"

const STATUS_LABEL: Record<Paper["status"], string> = {
  processing: "解析中",
  ready: "就绪",
  failed: "失败",
}

const STATUS_VARIANT: Record<Paper["status"], "default" | "secondary" | "destructive"> = {
  processing: "secondary",
  ready: "default",
  failed: "destructive",
}

const CITATION_FORMATS: { value: CitationFormat; label: string }[] = [
  { value: "apa", label: "APA" },
  { value: "mla", label: "MLA" },
  { value: "ieee", label: "IEEE" },
  { value: "bibtex", label: "BibTeX" },
]

interface Props {
  paper: Paper
}

export function PaperCard({ paper }: Props) {
  const { updatePaper, removePaper } = useAppStore()
  const [copied, setCopied] = useState(false)
  const [citationLoading, setCitationLoading] = useState(false)

  // 轮询：processing 状态每 2 秒查一次
  useEffect(() => {
    if (paper.status !== "processing") return
    const timer = setInterval(async () => {
      try {
        const status = await fetchPaperStatus(paper.id)
        if (status.status !== "processing") {
          updatePaper({ ...paper, status: status.status, chunk_count: status.chunk_count, error: status.error ?? undefined })
        }
      } catch {
        // 静默失败，继续轮询
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [paper, updatePaper])

  const handleDelete = async () => {
    try {
      await deletePaper(paper.id)
      removePaper(paper.id)
    } catch {
      // 静默失败
    }
  }

  const handleCopyCitation = async (format: CitationFormat) => {
    setCitationLoading(true)
    try {
      const { citation } = await generateCitation(paper.id, format)
      await navigator.clipboard.writeText(citation)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // 静默失败
    } finally {
      setCitationLoading(false)
    }
  }

  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{paper.title}</p>
          <p className="text-xs text-muted-foreground">
            {paper.status === "ready"
              ? `${paper.chunk_count} 个文本块`
              : paper.status === "failed"
              ? paper.error ?? "解析失败"
              : "正在解析…"}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant={STATUS_VARIANT[paper.status]}>
            {STATUS_LABEL[paper.status]}
          </Badge>
          {paper.status === "ready" && (
            <>
              {/* 复制引用下拉 */}
              <DropdownMenu>
                <DropdownMenuTrigger
                  className="inline-flex h-7 items-center gap-0.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                  disabled={citationLoading}
                  title="复制引用"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <>
                      引用
                      <ChevronDown className="h-3 w-3" />
                    </>
                  )}
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {CITATION_FORMATS.map(({ value, label }) => (
                    <DropdownMenuItem
                      key={value}
                      onClick={() => handleCopyCitation(value)}
                    >
                      {label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {/* 详情链接 */}
              <Link href={`/papers/${paper.id}`} onClick={(e) => e.stopPropagation()}>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
                  title="查看详情"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.stopPropagation(); handleDelete() }}
          >
            ✕
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
