import type { AnalyzeRequest, Paper, PaperStatus } from "@/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
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

// ---------- Analyze (SSE) ----------

export async function streamAnalyze(
  request: AnalyzeRequest,
  onChunk: (text: string) => void,
): Promise<void> {
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
        // 忽略
      }
    }
  }
}
