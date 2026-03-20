import { create } from "zustand"
import type { Conversation, Paper, ChatMessage } from "@/types"

interface AppState {
  papers: Paper[]
  selectedPaperIds: string[]

  // 会话列表
  conversations: Conversation[]
  activeConversationId: string | null

  // 当前会话消息（与 activeConversation 同步）
  messages: ChatMessage[]

  // Papers
  setPapers: (papers: Paper[]) => void
  addPaper: (paper: Paper) => void
  updatePaper: (paper: Paper) => void
  removePaper: (id: string) => void

  // Selection
  togglePaper: (id: string) => void
  setSelectedPaperIds: (ids: string[]) => void
  clearSelection: () => void

  // Conversations
  setConversations: (convs: Conversation[]) => void
  addConversation: (conv: Conversation) => void
  removeConversation: (id: string) => void
  setActiveConversation: (conv: Conversation | null) => void   // 加载历史对话用（会重置 messages）
  setActiveConversationId: (id: string | null) => void         // 仅更新 ID，不触碰 messages

  // Chat（操作当前会话的消息）
  addMessage: (msg: ChatMessage) => void
  clearMessages: () => void
}

export const useAppStore = create<AppState>((set) => ({
  papers: [],
  selectedPaperIds: [],
  conversations: [],
  activeConversationId: null,
  messages: [],

  setPapers: (papers) => set({ papers }),
  addPaper: (paper) => set((s) => ({ papers: [paper, ...s.papers] })),
  updatePaper: (paper) =>
    set((s) => ({ papers: s.papers.map((p) => (p.id === paper.id ? paper : p)) })),
  removePaper: (id) =>
    set((s) => ({
      papers: s.papers.filter((p) => p.id !== id),
      selectedPaperIds: s.selectedPaperIds.filter((pid) => pid !== id),
    })),

  togglePaper: (id) =>
    set((s) => ({
      selectedPaperIds: s.selectedPaperIds.includes(id)
        ? s.selectedPaperIds.filter((p) => p !== id)
        : [...s.selectedPaperIds, id],
    })),
  setSelectedPaperIds: (ids) => set({ selectedPaperIds: ids }),
  clearSelection: () => set({ selectedPaperIds: [] }),

  setConversations: (conversations) => set({ conversations }),
  addConversation: (conv) => set((s) => ({ conversations: [conv, ...s.conversations] })),
  removeConversation: (id) =>
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      activeConversationId: s.activeConversationId === id ? null : s.activeConversationId,
      messages: s.activeConversationId === id ? [] : s.messages,
    })),
  setActiveConversation: (conv) =>
    set({
      activeConversationId: conv?.id ?? null,
      messages: conv?.messages ?? [],
      selectedPaperIds: conv?.paper_ids ?? [],
    }),
  setActiveConversationId: (id) => set({ activeConversationId: id }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  clearMessages: () => set({ messages: [] }),
}))
