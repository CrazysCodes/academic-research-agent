"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { fetchSettings, updateSettings } from "@/lib/api"
import type { LLMSettings } from "@/types"

const PRESET_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "gpt-4-turbo",
  "claude-sonnet-4-6-20250514",
  "claude-opus-4-6-20250514",
  "deepseek-chat",
  "deepseek-reasoner",
]

const INIT_FORM = {
  llm_model: "", openai_api_key: "", openai_base_url: "",
  embedding_model: "", embedding_dim: "1536", embedding_api_key: "", embedding_base_url: "",
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<LLMSettings | null>(null)
  const [form, setForm] = useState(INIT_FORM)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  useEffect(() => {
    fetchSettings()
      .then((s) => {
        setSettings(s)
        setForm({
          llm_model: s.llm_model, openai_api_key: "", openai_base_url: s.openai_base_url,
          embedding_model: s.embedding_model, embedding_dim: String(s.embedding_dim),
          embedding_api_key: "", embedding_base_url: s.embedding_base_url,
        })
      })
      .catch(() => setMessage({ type: "error", text: "无法获取当前配置" }))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      // 只发送有变化的字段，空 key 不发（避免覆盖已有值）
      const payload: Partial<LLMSettings> = {}
      if (form.llm_model !== settings?.llm_model) payload.llm_model = form.llm_model
      if (form.openai_base_url !== settings?.openai_base_url) payload.openai_base_url = form.openai_base_url
      if (form.embedding_model !== settings?.embedding_model) payload.embedding_model = form.embedding_model
      if (Number(form.embedding_dim) !== settings?.embedding_dim) payload.embedding_dim = Number(form.embedding_dim)
      if (form.embedding_base_url !== settings?.embedding_base_url) payload.embedding_base_url = form.embedding_base_url
      if (form.openai_api_key) payload.openai_api_key = form.openai_api_key
      if (form.embedding_api_key) payload.embedding_api_key = form.embedding_api_key

      const updated = await updateSettings(payload)
      setSettings(updated)
      setForm((f) => ({ ...f, openai_api_key: "", embedding_api_key: "" }))
      setMessage({ type: "success", text: "保存成功（运行时生效，重启恢复默认值）" })
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "保存失败" })
    } finally {
      setSaving(false)
    }
  }

  const hasChanges = settings && (
    form.llm_model !== settings.llm_model ||
    form.openai_base_url !== settings.openai_base_url ||
    form.embedding_model !== settings.embedding_model ||
    Number(form.embedding_dim) !== settings.embedding_dim ||
    form.embedding_base_url !== settings.embedding_base_url ||
    form.openai_api_key !== "" ||
    form.embedding_api_key !== ""
  )

  if (!settings) {
    return (
      <div className="mx-auto max-w-xl p-6 space-y-2">
        <p className="text-sm text-muted-foreground">加载中…</p>
        {message?.type === "error" && (
          <p className="text-sm text-destructive">{message.text} — 请确认后端已启动</p>
        )}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">模型设置</h1>
        <p className="text-sm text-muted-foreground">LLM 和 Embedding 可使用不同的 API 地址和密钥</p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-6">
          {/* LLM Section */}
          <p className="text-sm font-semibold">对话模型 (LLM)</p>

          <div className="space-y-2">
            <Label htmlFor="openai_api_key">API Key</Label>
            <Input
              id="openai_api_key"
              type="password"
              placeholder={settings.openai_api_key ? `当前: ${settings.openai_api_key}` : "输入 API Key"}
              value={form.openai_api_key}
              onChange={(e) => setForm((f) => ({ ...f, openai_api_key: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="base_url">API Base URL</Label>
            <Input
              id="base_url"
              placeholder="留空使用官方 OpenAI，或填入代理地址"
              value={form.openai_base_url}
              onChange={(e) => setForm((f) => ({ ...f, openai_base_url: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="llm_model">模型名称</Label>
            <Input
              id="llm_model"
              placeholder="模型名称"
              value={form.llm_model}
              onChange={(e) => setForm((f) => ({ ...f, llm_model: e.target.value }))}
            />
            <div className="flex flex-wrap gap-1.5">
              {PRESET_MODELS.map((m) => (
                <button
                  key={m}
                  onClick={() => setForm((f) => ({ ...f, llm_model: m }))}
                  className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
                    form.llm_model === m
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-muted-foreground/25 hover:border-primary/50"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <Separator />

          {/* Embedding Section */}
          <p className="text-sm font-semibold">Embedding 模型</p>
          <p className="text-xs text-muted-foreground">留空则复用上方 LLM 的 API 地址和密钥</p>

          <div className="space-y-2">
            <Label htmlFor="embedding_api_key">API Key</Label>
            <Input
              id="embedding_api_key"
              type="password"
              placeholder={settings.embedding_api_key ? `当前: ${settings.embedding_api_key}` : "留空复用 LLM 的 Key"}
              value={form.embedding_api_key}
              onChange={(e) => setForm((f) => ({ ...f, embedding_api_key: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="embedding_base_url">API Base URL</Label>
            <Input
              id="embedding_base_url"
              placeholder="留空则复用 LLM 的 API 地址"
              value={form.embedding_base_url}
              onChange={(e) => setForm((f) => ({ ...f, embedding_base_url: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="embedding_model">模型名称</Label>
            <Input
              id="embedding_model"
              placeholder="如 text-embedding-3-small"
              value={form.embedding_model}
              onChange={(e) => setForm((f) => ({ ...f, embedding_model: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="embedding_dim">向量维度</Label>
            <Input
              id="embedding_dim"
              type="number"
              min={1}
              placeholder="如 1536"
              value={form.embedding_dim}
              onChange={(e) => setForm((f) => ({ ...f, embedding_dim: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground">
              需与 Embedding 模型输出维度一致；更改后仅影响新建向量 collection。
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <Button onClick={handleSave} disabled={saving || !hasChanges}>
              {saving ? "保存中…" : "保存"}
            </Button>
            {message && (
              <p className={`text-xs ${message.type === "success" ? "text-green-600" : "text-destructive"}`}>
                {message.text}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
