"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, FileText, Layers } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { fetchPaper, fetchPaperChunks } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Paper, PaperChunk } from "@/types"

type Tab = "chunks" | "full"

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [paper, setPaper] = useState<Paper | null>(null)
  const [chunks, setChunks] = useState<PaperChunk[]>([])
  const [tab, setTab] = useState<Tab>("chunks")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [p, c] = await Promise.all([fetchPaper(id), fetchPaperChunks(id)])
        setPaper(p)
        setChunks(c.chunks)
      } catch (e) {
        setError(e instanceof Error ? e.message : "加载失败")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center text-sm text-muted-foreground">
        加载中…
      </div>
    )
  }
  if (error || !paper) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center text-sm text-destructive">
        {error ?? "论文不存在"}
      </div>
    )
  }

  const fullText = chunks.map((c) => c.text).join("\n\n")

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 space-y-4">
      {/* 顶部导航 */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        返回文献库
      </button>

      {/* 论文信息 */}
      <div className="space-y-1">
        <div className="flex items-start gap-2">
          <h1 className="text-xl font-semibold leading-tight">{paper.title}</h1>
          <Badge
            variant={paper.status === "ready" ? "default" : paper.status === "failed" ? "destructive" : "secondary"}
            className="shrink-0 mt-0.5"
          >
            {paper.status === "ready" ? "就绪" : paper.status === "failed" ? "失败" : "处理中"}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          {paper.filename} · {paper.chunk_count} 个切块 · {new Date(paper.created_at).toLocaleString("zh-CN")}
        </p>
        {paper.error && <p className="text-sm text-destructive">{paper.error}</p>}
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-0 border-b">
        {(
          [
            { key: "chunks" as Tab, icon: Layers, label: `切块列表 (${chunks.length})` },
            { key: "full" as Tab, icon: FileText, label: "文档原文" },
          ] as const
        ).map(({ key, icon: Icon, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm border-b-2 transition-colors ${
              tab === key
                ? "border-foreground font-semibold text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      {tab === "chunks" ? (
        <div className="space-y-3">
          {chunks.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">暂无切块数据</p>
          ) : (
            chunks.map((chunk) => (
              <div
                key={chunk.index}
                className="rounded-lg border bg-card p-4 space-y-1.5 hover:border-muted-foreground/40 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                    #{chunk.index + 1}
                  </span>
                  <span className="text-xs text-muted-foreground">{chunk.text.length} 字符</span>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{chunk.text}</p>
              </div>
            ))
          )}
        </div>
      ) : (
        <ScrollArea className="h-[calc(100vh-18rem)]">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{fullText || "_暂无内容_"}</ReactMarkdown>
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
