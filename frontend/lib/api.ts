import type { Analysis, AnalyzeRequest, CitationFormat, CitationResponse, Conversation, DiagramResponse, DiagramType, LLMSettings, Paper, PaperStatus, SectionType } from "@/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ---------- Papers ----------

export async function fetchPapers(): Promise<Paper[]> {
  const data = await request<{ papers: Paper[] }>("/api/papers")
  return data.papers
}

export async function uploadPaper(file: File, title: string): Promise<Paper> {
  const form = new FormData()
  form.append("file", file)
  form.append("title", title)
  const data = await request<{ paper: Paper }>("/api/papers/upload", {
    method: "POST",
    body: form,
  })
  return data.paper
}

export async function fetchPaperStatus(paperId: string): Promise<PaperStatus> {
  return request<PaperStatus>(`/api/papers/${paperId}/status`)
}

export async function fetchPaper(paperId: string): Promise<Paper> {
  return request<Paper>(`/api/papers/${paperId}`)
}

export async function fetchPaperChunks(paperId: string): Promise<{ paper_id: string; chunks: import("@/types").PaperChunk[] }> {
  return request(`/api/papers/${paperId}/chunks`)
}

export async function deletePaper(paperId: string): Promise<void> {
  await request(`/api/papers/${paperId}`, { method: "DELETE" })
}

// ---------- Chat (SSE) ----------

export async function streamChat(
  paperIds: string[],
  query: string,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper_ids: paperIds, query }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split("\n").filter((l) => l.startsWith("data: "))
    for (const line of lines) {
      const raw = line.slice(6)
      if (raw === "[DONE]") return
      try {
        const data = JSON.parse(raw)
        if (data.delta) onChunk(data.delta)
      } catch {
        // 忽略格式错误的 SSE 行
      }
    }
  }
}

// ---------- Conversations ----------

export async function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/api/conversations")
}

export async function createConversation(title: string, paperIds: string[]): Promise<Conversation> {
  return request<Conversation>("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, paper_ids: paperIds }),
  })
}

export async function getConversation(convId: string): Promise<Conversation> {
  return request<Conversation>(`/api/conversations/${convId}`)
}

export async function deleteConversation(convId: string): Promise<void> {
  await request(`/api/conversations/${convId}`, { method: "DELETE" })
}

export async function saveMessage(convId: string, role: "user" | "assistant", content: string): Promise<void> {
  await request(`/api/conversations/${convId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, content }),
  })
}

export async function renameConversation(convId: string, title: string): Promise<void> {
  await request(`/api/conversations/${convId}/title`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  })
}

// ---------- Settings ----------

export async function fetchSettings(): Promise<LLMSettings> {
  return request<LLMSettings>("/api/settings")
}

export async function updateSettings(data: Partial<LLMSettings>): Promise<LLMSettings> {
  return request<LLMSettings>("/api/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
}

// ---------- Analyze (SSE, LangGraph Agent) ----------

export async function streamAnalyze(
  request: AnalyzeRequest,
  onNode: (name: string, label: string) => void,
  onChunk: (text: string) => void,
  onNodeOutput?: (name: string, data: Record<string, unknown>) => void,
): Promise<string | undefined> {
  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let analysisId: string | undefined

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split("\n").filter((l) => l.startsWith("data: "))
    for (const line of lines) {
      const raw = line.slice(6)
      if (raw === "[DONE]") return analysisId
      try {
        const data = JSON.parse(raw)
        if (data.event === "node") onNode(data.name, data.label)
        else if (data.event === "delta") onChunk(data.content)
        else if (data.event === "node_output") onNodeOutput?.(data.name, data.data)
        else if (data.event === "done") analysisId = data.analysis_id
      } catch {
        // 忽略格式错误的 SSE 行
      }
    }
  }
  return analysisId
}

// ---------- Analysis History ----------

export async function listAnalyses(): Promise<Analysis[]> {
  return request<Analysis[]>("/api/analyze/history")
}

export async function getAnalysis(id: string): Promise<Analysis> {
  return request<Analysis>(`/api/analyze/history/${id}`)
}

export async function deleteAnalysis(id: string): Promise<void> {
  await request(`/api/analyze/history/${id}`, { method: "DELETE" })
}

// ---------- Analysis Refinement (SSE) ----------

export async function streamRefineAnalysis(
  analysisId: string,
  instruction: string,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/analyze/${analysisId}/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split("\n").filter((l) => l.startsWith("data: "))
    for (const line of lines) {
      const raw = line.slice(6)
      if (raw === "[DONE]") return
      try {
        const data = JSON.parse(raw)
        if (data.delta) onChunk(data.delta)
      } catch {
        // 忽略格式错误的 SSE 行
      }
    }
  }
}

// ---------- Export ----------

export function getExportMarkdownUrl(analysisId: string): string {
  return `${BASE_URL}/api/analyze/${analysisId}/export/markdown`
}

// ---------- Diagram ----------

export async function generateDiagram(analysisId: string, diagramType: DiagramType): Promise<DiagramResponse> {
  return request<DiagramResponse>(`/api/analyze/${analysisId}/diagram`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diagram_type: diagramType }),
  })
}

// ---------- Citation ----------

export async function generateCitation(paperId: string, format: CitationFormat): Promise<CitationResponse> {
  return request<CitationResponse>(`/api/papers/${paperId}/citation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ format }),
  })
}

// ---------- Draft Section (SSE) ----------

export async function streamDraftSection(
  analysisId: string,
  sectionType: SectionType,
  targetLength: number,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/analyze/${analysisId}/draft-section`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ section_type: sectionType, target_length: targetLength }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split("\n").filter((l) => l.startsWith("data: "))
    for (const line of lines) {
      const raw = line.slice(6)
      if (raw === "[DONE]") return
      try {
        const data = JSON.parse(raw)
        if (data.delta) onChunk(data.delta)
      } catch {
        // 忽略格式错误的 SSE 行
      }
    }
  }
}
