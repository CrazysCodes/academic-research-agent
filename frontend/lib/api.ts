import type { AnalyzeRequest, Paper } from "@/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function fetchPapers(): Promise<Paper[]> {
  const res = await fetch(`${BASE_URL}/api/papers`)
  if (!res.ok) throw new Error("Failed to fetch papers")
  const data = await res.json()
  return data.papers
}

export async function uploadPaper(file: File, title: string): Promise<Paper> {
  const form = new FormData()
  form.append("file", file)
  form.append("title", title)
  const res = await fetch(`${BASE_URL}/api/papers/upload`, {
    method: "POST",
    body: form,
  })
  if (!res.ok) throw new Error("Upload failed")
  return res.json()
}

export async function deletePaper(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/papers/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error("Delete failed")
}

export async function streamAnalyze(
  request: AnalyzeRequest,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error("Analyze failed")

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value)
    const lines = chunk.split("\n").filter((l) => l.startsWith("data: "))
    for (const line of lines) {
      const raw = line.slice(6)
      if (raw === "[DONE]") return
      const data = JSON.parse(raw)
      if (data.delta) onChunk(data.delta)
    }
  }
}
