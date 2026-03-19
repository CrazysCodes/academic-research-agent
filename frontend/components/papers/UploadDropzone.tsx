"use client"

import { useCallback, useState } from "react"
import { uploadPaper } from "@/lib/api"
import { useAppStore } from "@/lib/store"
import { Button } from "@/components/ui/button"

const ACCEPTED = ".pdf,.docx,.doc"
const MAX_MB = 50

export function UploadDropzone() {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const addPaper = useAppStore((s) => s.addPaper)

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return
      const file = files[0]

      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`文件不能超过 ${MAX_MB}MB`)
        return
      }

      setError(null)
      setUploading(true)
      try {
        const title = file.name.replace(/\.[^.]+$/, "")
        const paper = await uploadPaper(file, title)
        addPaper(paper)
      } catch {
        setError("上传失败，请重试")
      } finally {
        setUploading(false)
      }
    },
    [addPaper],
  )

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files) }}
      className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 transition-colors ${
        dragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
      }`}
    >
      <div className="text-4xl">📄</div>
      <p className="text-sm text-muted-foreground">
        拖拽文件到此处，或
      </p>
      <label className="cursor-pointer">
        <input
          type="file"
          accept={ACCEPTED}
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={uploading}
        />
        <span className={`inline-flex h-8 items-center rounded-md border px-3 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground ${uploading ? "pointer-events-none opacity-50" : ""}`}>
          {uploading ? "上传中…" : "选择文件"}
        </span>
      </label>
      <p className="text-xs text-muted-foreground">支持 PDF、Word（最大 {MAX_MB}MB）</p>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
