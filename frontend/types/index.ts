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

export interface PaperChunk {
  index: number
  text: string
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

export interface LLMSettings {
  llm_model: string
  openai_api_key: string
  openai_base_url: string
  embedding_model: string
  embedding_api_key: string
  embedding_base_url: string
}

export interface Conversation {
  id: string
  title: string
  paper_ids: string[]
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}
