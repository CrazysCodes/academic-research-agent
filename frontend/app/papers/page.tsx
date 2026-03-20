"use client"

import { useEffect } from "react"
import { UploadDropzone } from "@/components/papers/UploadDropzone"
import { PaperCard } from "@/components/papers/PaperCard"
import { Separator } from "@/components/ui/separator"
import { fetchPapers } from "@/lib/api"
import { useAppStore } from "@/lib/store"

export default function PapersPage() {
  const { papers, setPapers } = useAppStore()

  useEffect(() => {
    fetchPapers().then(setPapers).catch(console.error)
  }, [setPapers])

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">文献库</h1>
        <p className="text-sm text-muted-foreground">上传论文，在问答或分析页选择使用</p>
      </div>

      <UploadDropzone />

      {papers.length > 0 && (
        <>
          <Separator />
          <div className="space-y-2">
            <p className="text-sm font-medium">全部论文（{papers.length}）</p>
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
