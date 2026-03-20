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

export type AgentNodeName = "planner" | "retriever" | "writer" | "reviewer"

export interface AgentNodeEvent {
  event: "node"
  name: AgentNodeName
  label: string
}

export interface AgentDeltaEvent {
  event: "delta"
  content: string
}

export interface AgentDoneEvent {
  event: "done"
}

// ---------- 节点输出 payload ----------

export interface PlannerOutput {
  sub_queries: string[]
}

export interface RetrieverOutput {
  chunk_count: number
  previews: string[]
}

export interface WriterOutput {
  iterations: number
  is_revision: boolean
}

export interface ReviewerOutput {
  score: number
  feedback: string
  will_revise: boolean
}

export type NodeOutputData = PlannerOutput | RetrieverOutput | WriterOutput | ReviewerOutput

export interface AgentNodeOutputEvent {
  event: "node_output"
  name: AgentNodeName
  data: NodeOutputData
}

// ---------- NodeStep（前端状态用） ----------

export interface NodeStep {
  name: AgentNodeName
  label: string
  iteration: number        // 1=首次, 2=修订
  output?: NodeOutputData  // on_chain_end 后填充
}

export type AgentSSEEvent = AgentNodeEvent | AgentDeltaEvent | AgentNodeOutputEvent | AgentDoneEvent

export interface LLMSettings {
  llm_model: string
  openai_api_key: string
  openai_base_url: string
  embedding_model: string
  embedding_api_key: string
  embedding_base_url: string
}

export interface Analysis {
  id: string
  query: string
  mode: string
  paper_ids: string[]
  result: string
  score: number
  iterations: number
  node_outputs: Record<string, NodeOutputData>
  created_at: string
}

export interface Conversation {
  id: string
  title: string
  paper_ids: string[]
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}
