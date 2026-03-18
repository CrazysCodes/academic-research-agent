"use client"

import { useEffect } from "react"
import { UploadDropzone } from "@/components/papers/UploadDropzone"
import { PaperCard } from "@/components/papers/PaperCard"
import { Separator } from "@/components/ui/separator"
import { fetchPapers } from "@/lib/api"
import { useAppStore } from "@/lib/store"

export default function PapersPage() {
  const { papers, setPapers, selectedPaperIds } = useAppStore()

  useEffect(() => {
    fetchPapers().then(setPapers).catch(console.error)
  }, [setPapers])

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">文献库</h1>
        <p className="text-sm text-muted-foreground">上传论文，点击卡片选中后去对话页提问</p>
      </div>

      <UploadDropzone />

      {papers.length > 0 && (
        <>
          <Separator />
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">全部论文（{papers.length}）</p>
              {selectedPaperIds.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  已选 {selectedPaperIds.length} 篇
                </p>
              )}
            </div>
            {papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
