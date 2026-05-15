"use client"

import { useEffect, useRef, useState } from "react"
import type { ReactNode } from "react"
import { Check, Copy } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { ChatMessage } from "@/types"

interface Props {
  messages: ChatMessage[]
  streaming?: string
  loading?: boolean
  isRagMode?: boolean
  onSuggestion?: (text: string) => void
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity p-1 rounded text-muted-foreground hover:text-foreground"
      title="复制"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  )
}

function AssistantContent({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}

function AssistantShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-start gap-2 max-w-[85%]">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 text-[10px] font-bold text-white shadow-sm mt-0.5">
          AI
        </div>
        {children}
      </div>
    </div>
  )
}

function LoadingBubble() {
  return (
    <AssistantShell>
      <div className="rounded-2xl rounded-tl-sm bg-card border px-4 py-3 text-sm shadow-sm">
        <div className="flex items-center gap-1.5 text-muted-foreground" aria-label="AI 正在思考">
          <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.2s]" />
          <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.1s]" />
          <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce" />
        </div>
      </div>
    </AssistantShell>
  )
}

function EmptyState({ isRagMode, onSelect }: { isRagMode?: boolean; onSelect?: (text: string) => void }) {
  const suggestions = isRagMode
    ? ["这篇论文的核心贡献是什么？", "总结一下实验结果", "和现有方法相比有哪些优势？"]
    : ["解释一下 Transformer 架构", "RAG 和 Fine-tuning 有什么区别？", "如何评估一篇论文的质量？"]

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="space-y-1.5">
        <div className="text-3xl">🎓</div>
        <p className="text-base font-medium">学术研究 Agent</p>
        <p className="text-sm text-muted-foreground">
          {isRagMode ? "基于已选论文进行检索问答" : "直接提问，或选择论文启用 RAG"}
        </p>
      </div>
      <div className="grid gap-2 w-full max-w-md">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSelect?.(s)}
            className="rounded-lg border bg-card px-4 py-2.5 text-sm text-left text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

export function MessageList({ messages, streaming, loading, isRagMode, onSuggestion }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streaming, loading])

  if (!messages.length && !streaming && !loading) {
    return <EmptyState isRagMode={isRagMode} onSelect={onSuggestion} />
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-3xl flex flex-col gap-6 px-4 py-6">
        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="flex items-end gap-2 max-w-[80%]">
                <div className="rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground whitespace-pre-wrap shadow-sm">
                  {msg.content}
                </div>
                {/* 用户 avatar */}
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground shadow-sm">
                  你
                </div>
              </div>
            </div>
          ) : (
            <div key={i} className="flex justify-start group">
              <div className="flex items-start gap-2 max-w-[85%]">
                {/* AI avatar */}
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 text-[10px] font-bold text-white shadow-sm mt-0.5">
                  AI
                </div>
                <div className="space-y-1">
                  <div className="rounded-2xl rounded-tl-sm bg-card border px-4 py-3 text-sm shadow-sm">
                    <AssistantContent content={msg.content} />
                  </div>
                  <div className="flex justify-end">
                    <CopyButton text={msg.content} />
                  </div>
                </div>
              </div>
            </div>
          )
        )}

        {/* 流式输出中 */}
        {streaming && (
          <AssistantShell>
            <div className="rounded-2xl rounded-tl-sm bg-card border px-4 py-3 text-sm shadow-sm">
              <AssistantContent content={streaming} />
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-foreground/70 align-middle" />
            </div>
          </AssistantShell>
        )}

        {loading && !streaming && <LoadingBubble />}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
