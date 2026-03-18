import { create } from "zustand"
import type { Paper, ChatMessage } from "@/types"

interface AppState {
  papers: Paper[]
  selectedPaperIds: string[]
  messages: ChatMessage[]
  setPapers: (papers: Paper[]) => void
  togglePaper: (id: string) => void
  addMessage: (msg: ChatMessage) => void
  clearMessages: () => void
}

export const useAppStore = create<AppState>((set) => ({
  papers: [],
  selectedPaperIds: [],
  messages: [],
  setPapers: (papers) => set({ papers }),
  togglePaper: (id) =>
    set((state) => ({
      selectedPaperIds: state.selectedPaperIds.includes(id)
        ? state.selectedPaperIds.filter((p) => p !== id)
        : [...state.selectedPaperIds, id],
    })),
  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
  clearMessages: () => set({ messages: [] }),
}))
