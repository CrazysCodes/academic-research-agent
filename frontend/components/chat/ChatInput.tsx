"use client"

import { KeyboardEvent, useRef } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled, placeholder = "输入问题…" }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const value = ref.current?.value.trim()
    if (!value || disabled) return
    onSend(value)
    ref.current!.value = ""
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // isComposing=true 表示输入法正在组合字符（中文候选词阶段），
    // 此时 Enter 是确认候选词而非发送，不应触发 handleSend
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-2">
      <Textarea
        ref={ref}
        placeholder={placeholder}
        className="min-h-[44px] max-h-32 resize-none"
        disabled={disabled}
        onKeyDown={handleKeyDown}
        rows={1}
      />
      <Button onClick={handleSend} disabled={disabled} className="shrink-0">
        发送
      </Button>
    </div>
  )
}
