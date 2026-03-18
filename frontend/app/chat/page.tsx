"use client"

import { useState } from "react"
import { MessageList } from "@/components/chat/MessageList"
import { ChatInput } from "@/components/chat/ChatInput"
import { Badge } from "@/components/ui/badge"
import { streamChat } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import type { ChatMessage } from "@/types"

export default function ChatPage() {
  const { papers, selectedPaperIds, messages, addMessage } = useAppStore()
  const [streaming, setStreaming] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedPapers = papers.filter((p) => selectedPaperIds.includes(p.id))

  const handleSend = async (query: string) => {
    if (!selectedPaperIds.length) {
      setError("请先在「文献库」页面选择论文")
      return
    }

    setError(null)
    setLoading(true)
    addMessage({ role: "user", content: query })

    let answer = ""
    setStreaming("")

    try {
      await streamChat(selectedPaperIds, query, (chunk) => {
        answer += chunk
        setStreaming(answer)
      })
      addMessage({ role: "assistant", content: answer })
    } catch (err) {
      const msg = err instanceof Error ? err.message : "请求失败"
      setError(msg)
      if (answer) addMessage({ role: "assistant", content: answer })
    } finally {
      setStreaming("")
      setLoading(false)
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* 已选论文 */}
      <div className="flex flex-wrap gap-1.5 border-b px-4 py-2">
        {selectedPapers.length === 0 ? (
          <span className="text-xs text-muted-foreground">未选择论文 — 前往文献库选择</span>
        ) : (
          selectedPapers.map((p) => (
            <Badge key={p.id} variant="secondary" className="text-xs">
              {p.title}
            </Badge>
          ))
        )}
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages as ChatMessage[]} streaming={streaming || undefined} />
      </div>

      {/* 输入框 */}
      <div className="border-t p-4 space-y-2">
        {error && <p className="text-xs text-destructive">{error}</p>}
        <ChatInput
          onSend={handleSend}
          disabled={loading}
          placeholder={selectedPaperIds.length ? "输入问题，Enter 发送…" : "请先选择论文"}
        />
      </div>
    </div>
  )
}
