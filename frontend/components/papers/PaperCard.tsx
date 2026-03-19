"use client"

import { useEffect } from "react"
import Link from "next/link"
import { ExternalLink } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { fetchPaperStatus, deletePaper } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import type { Paper } from "@/types"

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

interface Props {
  paper: Paper
}

export function PaperCard({ paper }: Props) {
  const { updatePaper, removePaper, togglePaper, selectedPaperIds } = useAppStore()
  const isSelected = selectedPaperIds.includes(paper.id)

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
      // TODO: toast 提示
    }
  }

  return (
    <Card
      className={`cursor-pointer transition-all ${
        isSelected && paper.status === "ready" ? "ring-2 ring-primary" : ""
      }`}
      onClick={() => paper.status === "ready" && togglePaper(paper.id)}
    >
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
            <Link
              href={`/papers/${paper.id}`}
              onClick={(e) => e.stopPropagation()}
            >
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
                title="查看详情"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </Button>
            </Link>
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
