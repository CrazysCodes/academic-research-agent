"use client"

import { useEffect, useId, useRef, useState } from "react"

interface Props {
  code: string
}

export function MermaidDiagram({ code }: Props) {
  const id = useId().replace(/:/g, "")
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState("")
  const [svg, setSvg] = useState("")

  useEffect(() => {
    if (!code) return
    let cancelled = false

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default
        mermaid.initialize({ startOnLoad: false, theme: "neutral" })
        const { svg } = await mermaid.render(`mermaid-${id}`, code)
        if (!cancelled) setSvg(svg)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "渲染失败")
      }
    }

    render()
    return () => { cancelled = true }
  }, [code, id])

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
        图表渲染失败：{error}
        <pre className="mt-2 text-xs whitespace-pre-wrap opacity-70">{code}</pre>
      </div>
    )
  }

  if (!svg) {
    return <div className="text-sm text-muted-foreground animate-pulse">正在渲染图表...</div>
  }

  return (
    <div
      ref={containerRef}
      className="overflow-x-auto rounded-md border bg-muted/20 p-4"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}
