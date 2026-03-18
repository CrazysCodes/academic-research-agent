# 文档解析方案

## 选型结论

| 格式 | 库 | 原因 |
|------|----|------|
| Word (.docx/.doc) | `markitdown` | Microsoft 维护，底层用 mammoth 转 HTML→Markdown，结构保留完整（标题/表格/列表），LLM-ready |
| PDF (.pdf) | `pymupdf4llm` | 比 marker 快 **94x**（0.12s vs 11s/页），无 GPU 依赖，学术结构化 PDF 质量足够 |

## 处理流程

```
上传请求
  │
  ▼
POST /api/papers/upload
  │  立即返回 { paper_id, status: "processing" }
  │
  ▼ BackgroundTasks（异步）
doc_service.parse_document()
  ├── .docx → markitdown.convert()      → Markdown
  └── .pdf  → pymupdf4llm.to_markdown() → Markdown
  │
  ▼
rag_service.index_paper()
  ├── RecursiveCharacterTextSplitter (chunk_size=512, overlap=64)
  ├── OpenAI text-embedding-3-small (1536 dim)
  └── Qdrant upsert (collection: "paper_{id}")
  │
  ▼
paper.status = "ready" / "failed"

前端轮询 GET /api/papers/{id}/status
```

## PDF 质量降级策略

| 场景 | 方案 |
|------|------|
| 结构化学术 PDF（默认） | pymupdf4llm（快，无需 GPU） |
| 扫描件 / 复杂排版 / 公式密集 | marker（需单独安装，`use_ocr=True` 参数触发） |

marker 作为可选降级方案，**不在默认依赖中**，按需安装：

```bash
uv add marker-pdf
```

代码层面在 `doc_service.py` 中通过参数路由：

```python
def parse_document(filename: str, content: bytes, use_ocr: bool = False) -> str:
    ...
    if ext == ".pdf":
        return _parse_pdf_ocr(path) if use_ocr else _parse_pdf(path)
```

## 文件限制

- 最大文件大小：50 MB
- 支持格式：`.pdf`、`.docx`、`.doc`

## 性能参考

| 库 | 速度 | GPU | OCR | 适合场景 |
|----|------|-----|-----|----------|
| pymupdf4llm | 0.12s/页 | 不需要 | ❌ | 文字型学术 PDF |
| markitdown | 快（同步） | 不需要 | 可选插件 | Word 文档 |
| marker | ~11s/页（CPU） | 推荐 | ✅ Surya | 扫描件、复杂排版 |
