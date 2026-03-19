"use client"

import { useEffect, useState } from "react"
import { Plus, Trash2 } from "lucide-react"
import { MessageList } from "@/components/chat/MessageList"
import { ChatInput } from "@/components/chat/ChatInput"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  saveMessage,
  streamChat,
} from "@/lib/api"
import { useAppStore } from "@/lib/store"
import type { ChatMessage } from "@/types"

export default function ChatPage() {
  const {
    papers,
    selectedPaperIds,
    conversations,
    activeConversationId,
    messages,
    addMessage,
    clearMessages,
    setConversations,
    addConversation,
    removeConversation,
    setActiveConversation,
    setActiveConversationId,
    togglePaper,
  } = useAppStore()

  const [streaming, setStreaming] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedPapers = papers.filter((p) => selectedPaperIds.includes(p.id))
  const isRagMode = selectedPaperIds.length > 0

  // 加载对话历史列表
  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch(() => {})
  }, [setConversations])

  const handleNewChat = () => {
    setActiveConversation(null)
    clearMessages()
  }

  const handleSelectConversation = async (convId: string) => {
    try {
      const conv = await getConversation(convId)
      setActiveConversation(conv)
      // 同步论文选中状态到会话的论文列表
      conv.paper_ids.forEach((pid) => {
        if (!selectedPaperIds.includes(pid)) togglePaper(pid)
      })
    } catch {
      setError("加载对话失败")
    }
  }

  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation()
    try {
      await deleteConversation(convId)
      removeConversation(convId)
    } catch {
      setError("删除失败")
    }
  }

  const handleSend = async (query: string) => {
    setError(null)
    setLoading(true)
    addMessage({ role: "user", content: query })

    let convId = activeConversationId
    // 如果没有当前对话，自动创建
    if (!convId) {
      try {
        const title = query.slice(0, 30) + (query.length > 30 ? "…" : "")
        const conv = await createConversation(title, selectedPaperIds)
        addConversation(conv)
        setActiveConversationId(conv.id)   // 只更新 ID，不重置 messages
        convId = conv.id
      } catch {
        // 创建失败不阻断对话，仅不持久化
      }
    }

    // 保存用户消息
    if (convId) {
      saveMessage(convId, "user", query).catch(() => {})
    }

    let answer = ""
    setStreaming("")

    try {
      await streamChat(selectedPaperIds, query, (chunk) => {
        answer += chunk
        setStreaming(answer)
      })
      addMessage({ role: "assistant", content: answer })
      if (convId) {
        saveMessage(convId, "assistant", answer).catch(() => {})
      }
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
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* ── 左侧：对话历史侧边栏 ── */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r bg-muted/30">
        <div className="flex items-center justify-between px-3 py-3 border-b">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">历史对话</span>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleNewChat} title="新对话">
            <Plus className="h-3.5 w-3.5" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-0.5">
            {conversations.length === 0 ? (
              <p className="text-xs text-muted-foreground px-2 py-3 text-center">暂无对话记录</p>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  className={`w-full group flex items-center justify-between gap-1 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted ${
                    conv.id === activeConversationId ? "bg-muted font-medium" : "text-muted-foreground"
                  }`}
                >
                  <span className="truncate flex-1">{conv.title}</span>
                  <Trash2
                    className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-60 hover:!opacity-100 text-destructive transition-opacity"
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                  />
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </aside>

      {/* ── 右侧：对话主区域 ── */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* 已选论文 / 模式指示 */}
        <div className="flex flex-wrap items-center gap-1.5 border-b px-4 py-2 min-h-[2.5rem] bg-background/80 backdrop-blur">
          {isRagMode ? (
            <>
              <span className="text-xs text-muted-foreground mr-1">RAG 模式 ·</span>
              {selectedPapers.map((p) => (
                <Badge key={p.id} variant="secondary" className="text-xs">
                  {p.title}
                </Badge>
              ))}
            </>
          ) : (
            <span className="text-xs text-muted-foreground">
              通用问答模式 — 可前往
              <a href="/papers" className="underline underline-offset-2 mx-1">文献库</a>
              选择论文以启用 RAG 检索
            </span>
          )}
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-hidden">
          <MessageList
            messages={messages as ChatMessage[]}
            streaming={streaming || undefined}
            isRagMode={isRagMode}
            onSuggestion={handleSend}
          />
        </div>

        {/* 输入框 */}
        <div className="border-t bg-background/80 backdrop-blur p-4 space-y-2">
          {error && <p className="text-xs text-destructive">{error}</p>}
          <ChatInput
            onSend={handleSend}
            disabled={loading}
            placeholder={isRagMode ? "基于已选论文提问，Enter 发送…" : "直接提问，Enter 发送…"}
          />
        </div>
      </div>
    </div>
  )
}
