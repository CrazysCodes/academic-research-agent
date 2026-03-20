"use client"

import { useEffect, useState } from "react"
import { Download, FileText, Plus, Trash2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { AgentProgress } from "@/components/analyze/AgentProgress"
import { MermaidDiagram } from "@/components/analyze/MermaidDiagram"
import { ChatInput } from "@/components/chat/ChatInput"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import {
  deleteAnalysis,
  generateDiagram,
  getAnalysis,
  getExportMarkdownUrl,
  listAnalyses,
  streamAnalyze,
  streamDraftSection,
  streamRefineAnalysis,
} from "@/lib/api"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import type { AgentNodeName, Analysis, ChatMessage, DiagramType, NodeOutputData, NodeStep, SectionType } from "@/types"

export default function AnalyzePage() {
  const { papers, selectedPaperIds, togglePaper, setSelectedPaperIds } = useAppStore()
  const [query, setQuery] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [nodeSteps, setNodeSteps] = useState<NodeStep[]>([])
  const [result, setResult] = useState("")
  const [error, setError] = useState("")

  // 历史记录
  const [history, setHistory] = useState<Analysis[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)

  // 对话式优化
  const [refinementMessages, setRefinementMessages] = useState<ChatMessage[]>([])
  const [refining, setRefining] = useState(false)
  const [refinementStreaming, setRefinementStreaming] = useState("")

  // 图表
  const [diagramCode, setDiagramCode] = useState("")
  const [diagramLoading, setDiagramLoading] = useState(false)
  const [diagramError, setDiagramError] = useState("")

  const readyPapers = papers.filter((p) => p.status === "ready")
  const canStart = query.trim().length > 0 && selectedPaperIds.length > 0 && !isRunning
  const hasResult = !!(result || isRunning)

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
      setDiagramCode("")
      setSelectedPaperIds(a.paper_ids ?? [])
      setRefinementMessages(
        (a.refinements ?? []).map((r: ChatMessage) => ({ role: r.role, content: r.content }))
      )
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
    setRefinementMessages([])
    setDiagramCode("")
    setDiagramError("")
  }

  async function handleRefine(instruction: string) {
    if (!activeId || refining) return
    setRefining(true)
    setError("")
    setRefinementMessages((prev) => [...prev, { role: "user", content: instruction }])

    let newResult = ""
    setRefinementStreaming("")

    try {
      await streamRefineAnalysis(activeId, instruction, (chunk) => {
        newResult += chunk
        setRefinementStreaming(newResult)
      })
      setResult(newResult)
      setRefinementMessages((prev) => [
        ...prev,
        { role: "assistant", content: "已根据您的要求更新报告。" },
      ])
    } catch (e) {
      setError(e instanceof Error ? e.message : "优化失败，请重试")
    } finally {
      setRefinementStreaming("")
      setRefining(false)
    }
  }

  async function handleAnalyze() {
    if (!canStart) return
    setIsRunning(true)
    setResult("")
    setError("")
    setNodeSteps([])
    setActiveId(null)
    setRefinementMessages([])
    setDiagramCode("")
    setDiagramError("")

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

  // ── 图表生成 ──
  async function handleGenerateDiagram(type: DiagramType) {
    if (!activeId || diagramLoading) return
    setDiagramLoading(true)
    setDiagramError("")
    setDiagramCode("")
    try {
      const res = await generateDiagram(activeId, type)
      setDiagramCode(res.mermaid_code)
    } catch (e) {
      setDiagramError(e instanceof Error ? e.message : "图表生成失败")
    } finally {
      setDiagramLoading(false)
    }
  }

  // ── 章节草稿 ──
  async function handleDraftSection(sectionType: SectionType) {
    if (!activeId || refining) return
    const sectionLabels: Record<SectionType, string> = {
      abstract: "摘要",
      introduction: "引言",
      related_work: "相关工作",
    }
    const label = sectionLabels[sectionType]
    setRefining(true)
    setError("")
    setRefinementMessages((prev) => [...prev, { role: "user", content: `生成${label}章节草稿` }])

    let draft = ""
    setRefinementStreaming("")

    try {
      await streamDraftSection(activeId, sectionType, 500, (chunk) => {
        draft += chunk
        setRefinementStreaming(draft)
      })
      setRefinementMessages((prev) => [...prev, { role: "assistant", content: draft }])
    } catch (e) {
      setError(e instanceof Error ? e.message : "草稿生成失败")
    } finally {
      setRefinementStreaming("")
      setRefining(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] print:h-auto print:block">
      {/* ── 左侧：历史侧边栏 ── */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r bg-muted/30 print:hidden">
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
          <div className="print:hidden">
            <h1 className="text-2xl font-bold">多文档分析</h1>
            <p className="text-sm text-muted-foreground mt-1">
              由 LangGraph 多 Agent 驱动：规划 → 检索 → 撰写 → 评审
            </p>
          </div>

          {/* 文献选择 + 问题输入 + 开始按钮（有结果后隐藏） */}
          {!hasResult && (
            <>
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

              <Textarea
                placeholder="输入研究问题，例如：比较这些论文在方法论上的异同..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="min-h-[100px] resize-none"
                disabled={isRunning}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault()
                    handleAnalyze()
                  }
                }}
              />

              <Button onClick={handleAnalyze} disabled={!canStart} className="w-full">
                {isRunning ? "Agent 分析中..." : "开始分析"}
              </Button>
            </>
          )}

          {/* 结果模式下显示查询摘要 */}
          {hasResult && (
            <div className="rounded-lg border bg-muted/30 px-4 py-3 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium flex-1">{query}</p>
                {/* 导出按钮 */}
                {activeId && !isRunning && (
                  <div className="flex gap-1.5 shrink-0 print:hidden">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      onClick={() => window.open(getExportMarkdownUrl(activeId), "_blank")}
                      title="导出 Markdown"
                    >
                      <FileText className="h-3 w-3" />
                      Markdown
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      onClick={() => window.print()}
                      title="导出 PDF（打印）"
                    >
                      <Download className="h-3 w-3" />
                      PDF
                    </Button>
                  </div>
                )}
              </div>
              {/* 文献 pill */}
              {readyPapers.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {readyPapers.map((p) => {
                    const selected = selectedPaperIds.includes(p.id)
                    return (
                      <button
                        key={p.id}
                        onClick={() => togglePaper(p.id)}
                        disabled={isRunning || refining}
                        title={selected ? "点击取消选择" : "点击添加此文献"}
                        className={cn(
                          "text-[11px] px-2 py-0.5 rounded-full border transition-colors",
                          selected
                            ? "bg-primary text-primary-foreground border-primary"
                            : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground",
                        )}
                      >
                        {p.title}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Agent 执行进度（时间线） */}
          {nodeSteps.length > 0 && (
            <AgentProgress steps={nodeSteps} isRunning={isRunning} />
          )}

          {/* 错误提示 */}
          {error && (
            <p className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2 print:hidden">
              {error}
            </p>
          )}

          {/* 分析结果 */}
          {result && (
            <div
              id="analysis-result"
              className="border rounded-lg p-6 bg-card prose prose-sm max-w-none dark:prose-invert"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {refinementStreaming || result}
              </ReactMarkdown>
            </div>
          )}

          {/* 图表生成区域 */}
          {result && !isRunning && activeId && (
            <div className="space-y-3 border rounded-lg p-4 print:hidden">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">生成图表</h3>
                {diagramLoading && (
                  <span className="text-xs text-muted-foreground animate-pulse">生成中...</span>
                )}
              </div>
              <div className="flex gap-2 flex-wrap">
                {(["relationship", "flowchart", "timeline"] as DiagramType[]).map((type) => {
                  const labels = { relationship: "关系图", flowchart: "流程图", timeline: "时间线" }
                  return (
                    <Button
                      key={type}
                      variant="outline"
                      size="sm"
                      className="text-xs"
                      disabled={diagramLoading}
                      onClick={() => handleGenerateDiagram(type)}
                    >
                      {labels[type]}
                    </Button>
                  )
                })}
              </div>
              {diagramError && (
                <p className="text-xs text-destructive">{diagramError}</p>
              )}
              {diagramCode && <MermaidDiagram code={diagramCode} />}
            </div>
          )}

          {/* 对话式优化区域 */}
          {result && !isRunning && activeId && (
            <div className="space-y-4 border-t pt-4 print:hidden">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-muted-foreground">对话优化</h3>
                {/* 章节草稿快捷按钮 */}
                <div className="flex gap-1.5">
                  <span className="text-xs text-muted-foreground self-center">生成：</span>
                  {(["abstract", "introduction", "related_work"] as SectionType[]).map((type) => {
                    const labels = { abstract: "摘要", introduction: "引言", related_work: "相关工作" }
                    return (
                      <Button
                        key={type}
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs px-2"
                        disabled={refining}
                        onClick={() => handleDraftSection(type)}
                      >
                        {labels[type]}
                      </Button>
                    )
                  })}
                </div>
              </div>

              {refinementMessages.length > 0 && (
                <div className="space-y-2">
                  {refinementMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={cn(
                        "text-sm rounded-lg px-3 py-2",
                        msg.role === "user" ? "bg-muted ml-8" : "bg-primary/5 mr-8",
                      )}
                    >
                      <span className="text-xs text-muted-foreground block mb-0.5">
                        {msg.role === "user" ? "你" : "AI"}
                      </span>
                      {msg.role === "assistant" ? (
                        <div className="prose prose-sm max-w-none dark:prose-invert">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        msg.content
                      )}
                    </div>
                  ))}
                </div>
              )}

              {refining && (
                <div className="text-sm rounded-lg px-3 py-2 bg-primary/5 mr-8">
                  <span className="text-xs text-muted-foreground block mb-0.5">AI</span>
                  {refinementStreaming ? (
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {refinementStreaming}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground animate-pulse">正在生成...</p>
                  )}
                </div>
              )}

              <ChatInput
                onSend={handleRefine}
                disabled={refining}
                placeholder="输入优化指令，例如：请补充方法论对比的细节…"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
