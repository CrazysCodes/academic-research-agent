"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"
import type {
  NodeStep,
  PlannerOutput,
  RetrieverOutput,
  ReviewerOutput,
  WriterOutput,
} from "@/types"

interface AgentProgressProps {
  steps: NodeStep[]
  isRunning: boolean
}

export function AgentProgress({ steps, isRunning }: AgentProgressProps) {
  return (
    <div className="space-y-0">
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1
        const isActive = isLast && isRunning && !step.output
        const isCompleted = !!step.output

        return (
          <StepRow
            key={`${step.name}-${step.iteration}`}
            step={step}
            isActive={isActive}
            isCompleted={isCompleted}
            isLast={isLast}
          />
        )
      })}
    </div>
  )
}

function StepRow({
  step,
  isActive,
  isCompleted,
  isLast,
}: {
  step: NodeStep
  isActive: boolean
  isCompleted: boolean
  isLast: boolean
}) {
  const [open, setOpen] = useState(false)
  const hasOutput = !!step.output

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="flex">
        {/* 左侧时间线指示器 */}
        <div className="flex flex-col items-center mr-3 w-5">
          <div
            className={cn(
              "w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 transition-colors",
              isActive && "bg-primary animate-pulse",
              isCompleted && "bg-primary",
              !isActive && !isCompleted && "bg-muted-foreground/30",
            )}
          />
          {!isLast && (
            <div
              className={cn(
                "w-px flex-1 min-h-4",
                isCompleted ? "bg-primary/30" : "bg-border",
              )}
            />
          )}
        </div>

        {/* 右侧内容 */}
        <div className="flex-1 pb-3 min-w-0">
          {/* 标题行 */}
          <CollapsibleTrigger
            disabled={!hasOutput}
            className={cn(
              "flex items-center gap-2 w-full text-left py-0.5 group",
              hasOutput && "cursor-pointer hover:text-foreground",
            )}
          >
            <span
              className={cn(
                "text-sm font-medium",
                isActive && "text-primary",
                isCompleted && "text-foreground",
                !isActive && !isCompleted && "text-muted-foreground",
              )}
            >
              {step.label}
            </span>

            {step.iteration > 1 && (
              <Badge variant="outline" className="text-[10px] h-4 px-1.5">
                修订 {step.iteration - 1}
              </Badge>
            )}

            {isActive && (
              <span className="text-xs text-muted-foreground animate-pulse">
                执行中...
              </span>
            )}

            {/* 评分 badge */}
            {step.name === "reviewer" && step.output && (
              <ScoreBadge score={(step.output as ReviewerOutput).score} />
            )}

            {/* 展开/折叠箭头 */}
            {hasOutput && (
              <span
                className={cn(
                  "ml-auto text-muted-foreground text-xs transition-transform",
                  open && "rotate-90",
                )}
              >
                ▸
              </span>
            )}
          </CollapsibleTrigger>

          {/* 可折叠详情面板 */}
          <CollapsibleContent>
            {hasOutput && (
              <div className="mt-2 ml-0.5 pl-3 border-l-2 border-muted text-xs text-muted-foreground space-y-1.5">
                <NodeOutputDetail step={step} />
              </div>
            )}
          </CollapsibleContent>
        </div>
      </div>
    </Collapsible>
  )
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 7
      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
      : score >= 5
        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
        : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"

  return (
    <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded-full", color)}>
      {score}/10
    </span>
  )
}

function NodeOutputDetail({ step }: { step: NodeStep }) {
  const { name, output } = step
  if (!output) return null

  if (name === "planner") {
    const data = output as PlannerOutput
    return (
      <div className="space-y-1">
        <p className="font-medium text-foreground/80">子查询：</p>
        <ol className="list-decimal list-inside space-y-0.5">
          {data.sub_queries.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ol>
      </div>
    )
  }

  if (name === "retriever") {
    const data = output as RetrieverOutput
    return (
      <div className="space-y-1.5">
        <p className="font-medium text-foreground/80">
          检索到 {data.chunk_count} 个文本片段
        </p>
        {data.previews.length > 0 && (
          <div className="space-y-1">
            {data.previews.map((preview, i) => (
              <div
                key={i}
                className="bg-muted/50 rounded px-2 py-1 text-[11px] leading-relaxed line-clamp-3"
              >
                {preview}
              </div>
            ))}
            {data.chunk_count > data.previews.length && (
              <p className="text-muted-foreground/60">
                ... 及其余 {data.chunk_count - data.previews.length} 个片段
              </p>
            )}
          </div>
        )}
      </div>
    )
  }

  if (name === "writer") {
    const data = output as WriterOutput
    return (
      <p>
        {data.is_revision
          ? `基于评审反馈修订（第 ${data.iterations} 次撰写）`
          : "初次撰写完成"}
      </p>
    )
  }

  if (name === "reviewer") {
    const data = output as ReviewerOutput
    return (
      <div className="space-y-1">
        <p className="font-medium text-foreground/80">
          评分：{data.score}/10
        </p>
        {data.feedback ? (
          <p>{data.feedback}</p>
        ) : (
          <p className="text-muted-foreground/60">通过，无修改意见</p>
        )}
        {data.will_revise && (
          <p className="text-yellow-600 dark:text-yellow-400">
            → 将触发修订
          </p>
        )}
      </div>
    )
  }

  return null
}
