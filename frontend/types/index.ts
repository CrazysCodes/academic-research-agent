export interface Paper {
  id: string
  title: string
  abstract: string
  created_at: string
  chunk_count: number
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

export interface AnalyzeRequest {
  paper_ids: string[]
  query: string
  mode: "single" | "compare"
}

export interface AnalyzeResponse {
  answer: string
  sources: string[]
  tokens_used: number
  mermaid_diagram?: string
}
