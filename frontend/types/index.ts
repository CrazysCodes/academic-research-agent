export type PaperStatusValue = "processing" | "ready" | "failed"

export interface Paper {
  id: string
  title: string
  filename: string
  status: PaperStatusValue
  error?: string
  chunk_count: number
  created_at: string
}

export interface PaperStatus {
  paper_id: string
  status: PaperStatusValue
  chunk_count: number
  error?: string | null
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
