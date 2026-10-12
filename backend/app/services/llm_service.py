import httpx, json, re
from typing import Optional, List

from app.services.encryption_service import decrypt


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
OPENAI_BASE = "https://api.openai.com/v1"
CLAUDE_BASE = "https://api.anthropic.com/v1"
CLAUDE_VERSION = "2023-06-01"
MINIMAX_BASE = "https://api.minimax.io/v1"
GLM_BASE = "https://api.z.ai/api/paas/v4"  # Zhipu AI international endpoint

# Model chat hợp lệ trên z.ai (theo docs). Dùng cho cả validate lẫn danh sách UI.
GLM_CHAT_MODELS = {
    "glm-5.2", "glm-5.1", "glm-5", "glm-5-turbo",
    "glm-4.7", "glm-4.7-flash", "glm-4.7-flashx",
    "glm-4.6", "glm-4.5", "glm-4.5-air", "glm-4.5-airx", "glm-4.5-flash",
    "glm-4-plus", "glm-4-long", "glm-4-flash", "glm-4-flash-250414",
    "glm-4-air", "glm-4-airx",
    "glm-z1-flash", "glm-z1-air", "glm-z1-airx",
    "glm-4v-plus", "glm-4v-flash", "glm-4.5v-air", "glm-5v-turbo",
    "glm-4-32b-0414-128k",
}

# Nguồn dữ liệu DUY NHẤT cho model LLM mỗi provider (settings.py + FE dùng lại).
LLM_MODELS: dict[str, list[str]] = {
    "gemini": ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-1.5-pro"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    "minimax": ["abab6.5s-chat", "abab7-chat"],
    "claude": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"],
    "glm": [
        "glm-5.2", "glm-5.1", "glm-5", "glm-5-turbo",
        "glm-4.7", "glm-4.7-flash",
        "glm-4.6", "glm-4.5-air",
        "glm-4-plus", "glm-4-long", "glm-4-flash", "glm-4-flash-250414",
        "glm-4-air", "glm-4-airx",
        "glm-z1-flash", "glm-z1-air", "glm-z1-airx",
        "glm-4v-plus", "glm-4v-flash", "glm-4.5v-air", "glm-5v-turbo",
    ],
}


def _build_script_prompt(title, style, characters, content, duration_sec, doc_texts) -> str:
    char_block = ""
    if characters:
        char_block = "NHÂN VẬT:\n" + "\n".join(
            f"- {c.name} ({c.age or ''}): {c.description or ''}" for c in characters
        )

    doc_block = ""
    if doc_texts:
        # Giới hạn tổng doc để tránh vượt TPM của GLM Lite (~10k tokens/phút)
        combined = "\n\n".join(doc_texts)
        if len(combined) > 2000:
            combined = combined[:2000] + "\n...[đã cắt bớt để tiết kiệm token]"
        doc_block = "\n\nTÀI LIỆU THAM KHẢO:\n" + combined

    return f"""Bạn là chuyên gia viết kịch bản phim hoạt hình ngắn. Viết kịch bản hoàn chỉnh và chia thành danh sách cảnh.

PHONG CÁCH: {style or "3D Pixar mềm, nhân vật con vật cách điệu"}
{char_block}
{doc_block}

YÊU CẦU NỘI DUNG:
{content}

THỜI LƯỢNG MỤC TIÊU: {duration_sec} giây (chia đều các cảnh)

Hãy trả về JSON với cấu trúc sau:
{{
  "title": "Tên tập phim",
  "content": "Kịch bản hoàn chỉnh dạng văn xuôi...",
  "scenes": [
    {{
      "scene_no": 1,
      "location": "Tên địa điểm",
      "shot_type": "ESTABLISH-ACTION",
      "action_desc": "Mô tả hành động chi tiết, góc máy",
      "duration_sec": 3,
      "voice_over": "Thoại hoặc SFX nếu có, hoặc null"
    }}
  ]
}}

Chỉ trả về JSON, không có text khác."""


async def generate_script_from_prompt(
    title, style, characters, content, duration_sec, doc_texts, api_config
) -> dict:
    provider = api_config.llm_provider or "gemini"
    model = api_config.llm_model or "gemini-2.0-flash"
    api_key = decrypt(api_config.llm_key_enc)

    prompt = _build_script_prompt(title, style, characters, content, duration_sec, doc_texts)

    if provider == "gemini":
        return await _call_gemini_text(api_key, model, prompt)
    elif provider == "openai":
        return await _call_openai_text(api_key, model, prompt)
    elif provider == "claude":
        return await _call_claude_text(api_key, model, prompt)
    elif provider == "minimax":
        return await _call_minimax_text(api_key, model, prompt)
    elif provider == "glm":
        return await _call_glm_text(api_key, model, prompt)
    else:
        raise ValueError(f"Provider không hỗ trợ: {provider}")


async def _call_gemini_text(api_key: str, model: str, prompt: str) -> dict:
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 429:
            raise Exception("Gemini 429: Hết quota/rate limit. Kiểm tra plan tại https://ai.dev/rate-limit")
        if resp.status_code in (401, 403):
            raise Exception("Gemini 401/403: API key không hợp lệ. Kiểm tra lại trong Cài đặt")
        if resp.status_code != 200:
            raise Exception(f"Gemini API lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json_response(text)


async def _call_openai_text(api_key: str, model: str, prompt: str) -> dict:
    url = f"{OPENAI_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            raise Exception("OpenAI 429: Hết quota/rate limit")
        if resp.status_code in (401, 403):
            raise Exception("OpenAI 401/403: API key không hợp lệ. Kiểm tra lại trong Cài đặt")
        if resp.status_code != 200:
            raise Exception(f"OpenAI API lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return _parse_json_response(text)


async def _call_claude_text(api_key: str, model: str, prompt: str) -> dict:
    url = f"{CLAUDE_BASE}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": CLAUDE_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 8192,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            raise Exception("Claude 429: Hết quota/rate limit. Kiểm tra plan tại https://console.anthropic.com")
        if resp.status_code in (401, 403):
            raise Exception("Claude 401/403: API key không hợp lệ. Kiểm tra lại trong Cài đặt")
        if resp.status_code != 200:
            raise Exception(f"Claude API lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        text = data["content"][0]["text"]
        return _parse_json_response(text)


async def _call_minimax_text(api_key: str, model: str, prompt: str) -> dict:
    """MiniMax Chat — OpenAI-compatible format, chỉ đổi base URL."""
    url = f"{MINIMAX_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or "abab6.5s-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 8192,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            raise Exception("MiniMax 429: Hết quota/rate limit. Kiểm tra tại https://platform.minimax.io")
        if resp.status_code in (401, 403):
            raise Exception("MiniMax 401/403: API key không hợp lệ. Kiểm tra lại trong Cài đặt")
        if resp.status_code != 200:
            raise Exception(f"MiniMax API lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        # MiniMax trả về base_resp.status_code nếu có lỗi nghiệp vụ
        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) not in (0, None):
            raise Exception(f"MiniMax lỗi: {base_resp.get('status_msg', 'Unknown error')}")

        text_out = data["choices"][0]["message"]["content"]
        return _parse_json_response(text_out)


async def _call_glm_text(api_key: str, model: str, prompt: str) -> dict:
    """
    GLM (Zhipu AI) Chat Completion theo docs.z.ai.

    Endpoint: POST https://api.z.ai/api/paas/v4/chat/completions
    Docs:     https://docs.z.ai/api-reference/llm/chat-completion

    Tham số theo spec chính thức:
      - model:           required, enum (glm-4-flash, glm-5.2, glm-4.7-flash, ...)
      - messages:        required, array [{role, content}]
      - do_sample:       boolean, default true (bật sampling strategy)
      - temperature:     float [0.0, 1.0], default 1.0
      - top_p:           float [0.01, 1.0], default 0.95
      - max_tokens:      int [1, 131072]
      - response_format: {type: "text" | "json_object"}
      - stream:          boolean, default false
    """
    url = f"{GLM_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Model không rõ → dùng glm-4-flash (miễn phí). Khác với ảnh/video, ở đây
    # fallback chấp nhận được vì mọi model chat đều trả về cùng dạng JSON.
    safe_model = model if model in GLM_CHAT_MODELS else "glm-4-flash"

    payload = {
        "model": safe_model,
        "messages": [
            {
                "role": "system",
                "content": "Bạn là AI chuyên viết kịch bản hoạt hình. Luôn trả về JSON hợp lệ theo đúng schema được yêu cầu, không có text nào khác.",
            },
            {"role": "user", "content": prompt},
        ],
        # Sampling params theo docs
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 8192,          # API hỗ trợ tới 131072; 8192 đủ cho kịch bản
        # JSON mode: GLM hỗ trợ response_format json_object
        "response_format": {"type": "json_object"},
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            raise Exception("GLM 429: Hết quota/rate limit. Kiểm tra tại https://z.ai/manage-apikey/rate-limits")
        if resp.status_code in (401, 403):
            raise Exception("GLM 401/403: API key không hợp lệ. Kiểm tra lại trong Cài đặt")
        if resp.status_code != 200:
            raise Exception(f"GLM API lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()

        # Xử lý lỗi nghiệp vụ nếu có (một số model trả error trong body)
        if "error" in data:
            err = data["error"]
            raise Exception(f"GLM lỗi {err.get('code', '')}: {err.get('message', 'Unknown error')}")

        # Response schema: choices[0].message.content
        text_out = data["choices"][0]["message"]["content"]
        return _parse_json_response(text_out)


def _parse_json_response(text: str) -> dict:
    # Strip markdown code blocks if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise Exception(f"Không thể parse JSON từ AI: {e}\nText: {text[:200]}")


def _build_reparse_prompt(content: str) -> str:
    return f"""Bạn là AI phân tích kịch bản phim hoạt hình.

Đọc kịch bản sau và trích xuất danh sách các cảnh phim.

KỊCH BẢN:
{content}

Trả về JSON với cấu trúc CHÍNH XÁC sau (không có text khác):
{{
  "scenes": [
    {{
      "scene_no": 1,
      "location": "Tên địa điểm/bối cảnh",
      "shot_type": "WIDE hoặc CLOSE-UP hoặc ESTABLISH-ACTION hoặc MEDIUM",
      "action_desc": "Mô tả hành động trong cảnh",
      "duration_sec": 3,
      "voice_over": "Thoại hoặc null nếu không có"
    }}
  ]
}}

Chỉ trả về JSON, không có text nào khác."""


async def parse_scenes_from_content(content: str, api_config) -> list:
    """Parse lại scenes từ kịch bản full text.
    
    Gửi content lên LLM với prompt chuyên biệt để extract danh sách scenes.
    Trả về list of dicts (preview, chưa lưu vào DB).
    """
    provider = api_config.llm_provider or "gemini"
    model = api_config.llm_model or "gemini-2.0-flash"
    api_key = decrypt(api_config.llm_key_enc)

    prompt = _build_reparse_prompt(content)

    if provider == "gemini":
        result = await _call_gemini_text(api_key, model, prompt)
    elif provider == "openai":
        result = await _call_openai_text(api_key, model, prompt)
    elif provider == "claude":
        result = await _call_claude_text(api_key, model, prompt)
    elif provider == "minimax":
        result = await _call_minimax_text(api_key, model, prompt)
    elif provider == "glm":
        result = await _call_glm_text(api_key, model, prompt)
    else:
        raise ValueError(f"Provider không hỗ trợ: {provider}")

    # result có thể là {"scenes": [...]} hoặc chỉ là list
    if isinstance(result, dict) and "scenes" in result:
        return result["scenes"]
    elif isinstance(result, list):
        return result
    else:
        raise Exception("LLM không trả về danh sách cảnh hợp lệ")

