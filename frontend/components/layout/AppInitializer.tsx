"use client"

import { useEffect } from "react"
import { fetchPapers } from "@/lib/api"
import { useAppStore } from "@/lib/store"

/**
 * 全局数据初始化：在 layout 层加载 papers 到 store，
 * 确保问答页、分析页无需先访问文献库即可看到已上传文献。
 */
export function AppInitializer() {
  const setPapers = useAppStore((s) => s.setPapers)

  useEffect(() => {
    fetchPapers().then(setPapers).catch(() => {})
  }, [setPapers])

  return null
}
