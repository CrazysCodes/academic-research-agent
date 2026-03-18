import { create } from "zustand"
import type { Paper, ChatMessage } from "@/types"

interface AppState {
  papers: Paper[]
  selectedPaperIds: string[]
  messages: ChatMessage[]

  // Papers
  setPapers: (papers: Paper[]) => void
  addPaper: (paper: Paper) => void
  updatePaper: (paper: Paper) => void
  removePaper: (id: string) => void

  // Selection
  togglePaper: (id: string) => void
  clearSelection: () => void

  // Chat
  addMessage: (msg: ChatMessage) => void
  clearMessages: () => void
}

export const useAppStore = create<AppState>((set) => ({
  papers: [],
  selectedPaperIds: [],
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
  clearSelection: () => set({ selectedPaperIds: [] }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  clearMessages: () => set({ messages: [] }),
}))
