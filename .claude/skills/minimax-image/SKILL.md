---
name: minimax-image
description: MiniMax 生图服务，支持文生图（T2I）和图生图（I2I）两种模式。可根据描述生成图片，或基于参考图生成保持人物特征的新图片。
---

# MiniMax 生图服务

## 服务概述

- **文生图（Text-to-Image）**：通过文本描述直接生成图片
- **图生图（Image-to-Image）**：基于参考图+文字描述生成保持人物特征的新图片

**端点**：`POST https://api.minimaxi.com/v1/image_generation`
**认证**：`Authorization: Bearer {MINIMAX_API_KEY}`

---

## 通用参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | 模型：`image-01` 或 `image-01-live` |
| prompt | string | 是 | 文本描述，最长 1500 字符 |
| aspect_ratio | string | 否 | 宽高比：`1:1`、`16:9`、`4:3`、`3:2`、`2:3`、`3:4`、`9:16`、`21:9` |
| width/height | integer | 否 | 像素尺寸 [512-2048]，需为 8 的倍数，仅 image-01 |
| response_format | string | 否 | 返回格式：`url`(默认) 或 `base64` |
| n | integer | 否 | 生成数量 1-9，默认 1 |
| seed | integer | 否 | 随机种子，用于复现结果 |
| prompt_optimizer | boolean | 否 | 是否自动优化提示词，默认 false |
| aigc_watermark | boolean | 否 | 是否添加水印，默认 false |

---

## 文生图（Text-to-Image）

```bash
curl -X POST "https://api.minimaxi.com/v1/image_generation" \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "image-01",
    "prompt": "你的图片描述",
    "aspect_ratio": "16:9",
    "response_format": "url",
    "n": 1,
    "prompt_optimizer": true
  }'
```

**响应**：
```json
{
  "id": "任务ID",
  "data": {
    "image_urls": ["图片URL"]
  },
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

---

## 图生图（Image-to-Image）

### 额外参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subject_reference | array | 否 | 人物主体参考，最多 1 个 |
| subject_reference[].type | string | 是 | 类型：`character` |
| subject_reference[].image_file | string | 是 | 参考图：公网 URL 或 Base64 Data URL |

**参考图要求**：JPG/JPEG/PNG，小于 10MB，建议单人正面照

### style 画风（仅 image-01-live）

| 参数 | 类型 | 说明 |
|------|------|------|
| style_type | string | `漫画`、`元气`、`中世纪`、`水彩` |
| style_weight | float | 权重 (0, 1]，默认 0.8 |

```bash
curl -X POST "https://api.minimaxi.com/v1/image_generation" \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "image-01",
    "prompt": "描述内容",
    "aspect_ratio": "16:9",
    "subject_reference": [
      {
        "type": "character",
        "image_file": "https://example.com/reference.jpg"
      }
    ],
    "n": 1
  }'
```

---

## 下载图片

API 返回的 URL 是预签名链接，建议立即下载保存：

```bash
# 下载单张图片
curl -s -o ~/Pictures/生成的图片.jpg "图片URL"

# 下载并以时间戳命名
curl -s -o ~/Pictures/minimax_$(date +%Y%m%d_%H%M%S).jpg "图片URL"
```

**注意**：`response_format: "url"` 返回的图片 URL 有时效性，请及时下载。

---

## 错误码

| 状态码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1002 | 触发限流 |
| 1004 | 账号鉴权失败 |
| 1008 | 账号余额不足 |
| 1026 | 内容敏感 |
| 2013 | 参数异常 |
| 2049 | 无效 API Key |
