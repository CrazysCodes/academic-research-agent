"use client"

import { useEffect, useState } from "react"
import { Plus, Trash2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { AgentProgress } from "@/components/analyze/AgentProgress"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { deleteAnalysis, getAnalysis, listAnalyses, streamAnalyze } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import type { AgentNodeName, Analysis, NodeOutputData, NodeStep } from "@/types"

export default function AnalyzePage() {
  const { papers, selectedPaperIds, togglePaper } = useAppStore()
  const [query, setQuery] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [nodeSteps, setNodeSteps] = useState<NodeStep[]>([])
  const [result, setResult] = useState("")
  const [error, setError] = useState("")

  // 历史记录
  const [history, setHistory] = useState<Analysis[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)

  const readyPapers = papers.filter((p) => p.status === "ready")
  const canStart = query.trim().length > 0 && selectedPaperIds.length > 0 && !isRunning

  // 加载历史列表
  useEffect(() => {
    listAnalyses().then(setHistory).catch(() => {})
  }, [])

  // 从历史加载某条分析
  async function handleLoadHistory(id: string) {
    try {
      const a = await getAnalysis(id)
      setActiveId(a.id)
      setQuery(a.query)
      setResult(a.result)
      setError("")
      // 从 node_outputs 重建 nodeSteps
      if (a.node_outputs) {
        const steps: NodeStep[] = []
        const nodeOrder: AgentNodeName[] = ["planner", "retriever", "writer", "reviewer"]
        for (const [key, data] of Object.entries(a.node_outputs)) {
          const baseName = key.replace(/_\d+$/, "") as AgentNodeName
          if (!nodeOrder.includes(baseName)) continue
          const iteration = steps.filter((s) => s.name === baseName).length + 1
          steps.push({
            name: baseName,
            label: { planner: "规划查询", retriever: "检索文献", writer: "撰写报告", reviewer: "质量评审" }[baseName],
            iteration,
            output: data as unknown as NodeOutputData,
          })
        }
        setNodeSteps(steps)
      } else {
        setNodeSteps([])
      }
    } catch {
      setError("加载历史记录失败")
    }
  }

  async function handleDeleteHistory(e: React.MouseEvent, id: string) {
    e.stopPropagation()
    try {
      await deleteAnalysis(id)
      setHistory((prev) => prev.filter((a) => a.id !== id))
      if (activeId === id) handleNewAnalysis()
    } catch {
      setError("删除失败")
    }
  }

  function handleNewAnalysis() {
    setActiveId(null)
    setQuery("")
    setResult("")
    setNodeSteps([])
    setError("")
  }

  async function handleAnalyze() {
    if (!canStart) return
    setIsRunning(true)
    setResult("")
    setError("")
    setNodeSteps([])
    setActiveId(null)

    try {
      const analysisId = await streamAnalyze(
        { paper_ids: selectedPaperIds, query, mode: "compare" },
        (name, label) => {
          const nodeName = name as AgentNodeName
          setNodeSteps((prev) => {
            const iteration = prev.filter((s) => s.name === nodeName).length + 1
            return [...prev, { name: nodeName, label, iteration }]
          })
        },
        (chunk) => setResult((prev) => prev + chunk),
        (name, data) => {
          setNodeSteps((prev) => {
            const idx = prev.findLastIndex((s) => s.name === name && !s.output)
            if (idx === -1) return prev
            const updated = [...prev]
            updated[idx] = { ...updated[idx], output: data as unknown as NodeOutputData }
            return updated
          })
        },
      )
      // 刷新历史列表
      if (analysisId) {
        setActiveId(analysisId)
        listAnalyses().then(setHistory).catch(() => {})
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "分析失败，请重试")
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* ── 左侧：历史侧边栏 ── */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r bg-muted/30">
        <div className="flex items-center justify-between px-3 py-3 border-b">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            分析历史
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleNewAnalysis}
            title="新分析"
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-0.5">
            {history.length === 0 ? (
              <p className="text-xs text-muted-foreground px-2 py-3 text-center">
                暂无分析记录
              </p>
            ) : (
              history.map((a) => (
                <button
                  key={a.id}
                  onClick={() => handleLoadHistory(a.id)}
                  className={cn(
                    "w-full group flex items-center justify-between gap-1 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                    a.id === activeId ? "bg-muted font-medium" : "text-muted-foreground",
                  )}
                >
                  <span className="truncate flex-1">
                    {a.query.slice(0, 30)}
                    {a.query.length > 30 ? "…" : ""}
                  </span>
                  <Trash2
                    className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-60 hover:!opacity-100 text-destructive transition-opacity"
                    onClick={(e) => handleDeleteHistory(e, a.id)}
                  />
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </aside>

      {/* ── 右侧：主内容区 ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-4xl px-4 py-8 space-y-6">
          <div>
            <h1 className="text-2xl font-bold">多文档分析</h1>
            <p className="text-sm text-muted-foreground mt-1">
              由 LangGraph 多 Agent 驱动：规划 → 检索 → 撰写 → 评审
            </p>
          </div>

          {/* 文献选择 */}
          <div className="space-y-2">
            <p className="text-sm font-medium">
              选择文献
              <span className="ml-1.5 text-muted-foreground">
                （{selectedPaperIds.length} 已选，至少选 1 篇）
              </span>
            </p>
            {readyPapers.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                请先在文献库上传并处理论文
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {readyPapers.map((paper) => {
                  const selected = selectedPaperIds.includes(paper.id)
                  return (
                    <button
                      key={paper.id}
                      onClick={() => togglePaper(paper.id)}
                      disabled={isRunning}
                      className={cn(
                        "text-xs px-3 py-1.5 rounded-full border transition-colors",
                        selected
                          ? "bg-primary text-primary-foreground border-primary"
                          : "border-border hover:border-primary/50 text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {paper.title}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* 问题输入 */}
          <Textarea
            placeholder="输入研究问题，例如：比较这些论文在方法论上的异同..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="min-h-[100px] resize-none"
            disabled={isRunning}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleAnalyze()
              }
            }}
          />

          <Button onClick={handleAnalyze} disabled={!canStart} className="w-full">
            {isRunning ? "Agent 分析中..." : "开始分析"}
          </Button>

          {/* Agent 执行进度（时间线） */}
          {nodeSteps.length > 0 && (
            <AgentProgress steps={nodeSteps} isRunning={isRunning} />
          )}

          {/* 错误提示 */}
          {error && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          {/* 分析结果 */}
          {result && (
            <div className="border rounded-lg p-6 bg-card prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
