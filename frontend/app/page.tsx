import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export default function Home() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-8 px-4 py-24 text-center">
      <h1 className="text-4xl font-bold tracking-tight">学术研究 Agent</h1>
      <p className="text-lg text-muted-foreground">
        上传论文 → 多文档检索问答 → 对比分析 → 辅助写作
      </p>
      <div className="flex gap-3">
        <Link href="/papers" className={cn(buttonVariants({ size: "lg" }))}>
          上传文献
        </Link>
        <Link href="/chat" className={cn(buttonVariants({ variant: "outline", size: "lg" }))}>
          开始问答
        </Link>
      </div>
    </div>
  )
}
