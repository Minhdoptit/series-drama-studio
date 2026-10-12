import httpx, base64, asyncio
from app.services.encryption_service import decrypt

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
OPENAI_BASE = "https://api.openai.com/v1"
MINIMAX_BASE = "https://api.minimax.io/v1"
GLM_BASE = "https://api.z.ai/api/paas/v4"  # Zhipu AI international endpoint


async def generate_images_ai(
    prompt: str,
    style: str,
    reference_images_b64: list[str],
    api_config,
    n: int = 3,
) -> list[str]:
    provider = api_config.image_provider or "gemini"
    # Fallback model theo từng provider để tránh lỗi "Unknown Model"
    _default_models = {
        "gemini": "imagen-3",
        "openai": "dall-e-3",
        "minimax": "image-01",
        "glm": "glm-image",
    }
    model = api_config.image_model or _default_models.get(provider, "imagen-3")
    api_key = decrypt(api_config.image_key_enc)

    full_prompt = f"{prompt}. Phong cách: {style}. Nền xám studio. Chất lượng cao, 3D render."

    if provider == "gemini":
        return await _gemini_imagen(api_key, model, full_prompt, reference_images_b64, n)
    elif provider == "openai":
        return await _dalle(api_key, model, full_prompt, n)
    elif provider == "minimax":
        return await _minimax_image(api_key, model, full_prompt, reference_images_b64, n)
    elif provider == "glm":
        return await _cogview_image(api_key, model, full_prompt, n)
    else:
        raise ValueError(f"Image provider không hỗ trợ: {provider}")


async def _gemini_imagen(api_key: str, model: str, prompt: str, refs: list[str], n: int) -> list[str]:
    url = f"{GEMINI_BASE}/models/{model}:predict?key={api_key}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": n, "aspectRatio": "9:16"}
    }

    # Add reference image if available
    if refs:
        payload["instances"][0]["image"] = {
            "bytesBase64Encoded": refs[0]
        }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise Exception(f"Gemini Imagen lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        b64_list = [
            pred["bytesBase64Encoded"]
            for pred in data.get("predictions", [])
        ]
        return [f"data:image/png;base64,{b}" for b in b64_list]


async def _dalle(api_key: str, model: str, prompt: str, n: int) -> list[str]:
    url = f"{OPENAI_BASE}/images/generations"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model or "dall-e-3",
        "prompt": prompt,
        "n": min(n, 1),  # DALL-E 3 only supports n=1
        "size": "1024x1792",  # 9:16 portrait
        "response_format": "b64_json"
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"DALL-E lỗi {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return [f"data:image/png;base64,{d['b64_json']}" for d in data["data"]]


# Model names theo docs.z.ai (https://docs.z.ai/api-reference/image/generate-image)
# Sync: supports glm-image và cogview-4-250304
# Async: chỉ supports glm-image
GLM_IMAGE_MODELS = {
    "glm-image",       # Flagship, HD quality (~20s), hỗ trợ async
    "cogview-4-250304", # Standard quality (5-10s), sync only
}

# Nguồn dữ liệu DUY NHẤT cho model ảnh mỗi provider (settings.py + FE dùng lại).
# Danh sách GLM khớp đúng GLM_IMAGE_MODELS ở trên; trước đây UI chào cogview-4 /
# cogview-3-plus / cogview-3-flash nhưng không tên nào được backend chấp nhận.
IMAGE_MODELS: dict[str, list[str]] = {
    "gemini": ["imagen-3", "imagen-2"],
    "openai": ["dall-e-3", "dall-e-2"],
    "minimax": ["image-01", "image-01-live"],
    "glm": ["glm-image", "cogview-4-250304"],
}

# Size hợp lệ theo từng model
# glm-image:        1024-2048px, chia hết 32, max 2^22 px tổng
# cogview-4-250304: 512-2048px, chia hết 16, max 2^21 px tổng
_GLM_PORTRAIT_SIZES = {
    "glm-image":        "1056x1568",  # 9:16 portrait, chia hết 32
    "cogview-4-250304": "768x1344",   # 9:16 portrait, chia hết 16
}


async def _cogview_image(api_key: str, model: str, prompt: str, n: int) -> list[str]:
    """
    Z.ai CogView / GLM-Image generation theo docs.z.ai.

    Endpoint:  POST https://api.z.ai/api/paas/v4/images/generations
    Models:    glm-image (HD ~20s) | cogview-4-250304 (standard 5-10s)
    Response:  {created, data: [{url}], content_filter}
    - Không có tham số n → gọi n requests song song
    - URL ảnh temporary (30 ngày) → download về base64
    """
    # Báo lỗi rõ ràng thay vì âm thầm đổi model
    if model not in GLM_IMAGE_MODELS:
        raise Exception(
            f"Model ảnh GLM không hỗ trợ: {model}. "
            f"Hiện hỗ trợ: {', '.join(sorted(GLM_IMAGE_MODELS))}"
        )
    safe_model = model

    # Chọn size portrait phù hợp với model
    size = _GLM_PORTRAIT_SIZES.get(safe_model, "768x1344")

    url = f"{GLM_BASE}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async def _single_request(client: httpx.AsyncClient) -> str | None:
        """
        Một request theo đúng schema docs.z.ai:
        Body: {model, prompt, quality?, size?, user_id?}
        Không có trường 'n'.
        """
        payload: dict = {
            "model": safe_model,
            "prompt": prompt,
            "size": size,
        }
        # glm-image mặc định hd; cogview-4-250304 mặc định standard
        if safe_model == "cogview-4-250304":
            payload["quality"] = "standard"

        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            raise Exception("GLM/CogView 429: Hết quota/rate limit. Kiểm tra tại https://z.ai")
        if resp.status_code in (401, 403):
            raise Exception("GLM/CogView 401/403: API key không hợp lệ")
        if resp.status_code != 200:
            raise Exception(f"CogView lỗi {resp.status_code}: {resp.text[:300]}")

        # Response schema: {created, data: [{url}], content_filter}
        data = resp.json()
        items = data.get("data", [])
        return items[0]["url"] if items else None

    # Gọi n requests song song (mỗi request trả về 1 ảnh)
    actual_n = min(n, 4)
    async with httpx.AsyncClient(timeout=120) as client:
        tasks = [_single_request(client) for _ in range(actual_n)]
        image_urls = await asyncio.gather(*tasks, return_exceptions=True)

    # Download ảnh từ URL về và convert sang base64
    results = []
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=60) as dl:
        for item in image_urls:
            if isinstance(item, Exception):
                errors.append(str(item))
                continue
            if not item:
                errors.append("CogView không trả về URL ảnh")
                continue
            img_resp = await dl.get(item)
            if img_resp.status_code == 200:
                b64 = base64.b64encode(img_resp.content).decode()
                results.append(f"data:image/png;base64,{b64}")
            else:
                errors.append(f"Tải ảnh về lỗi HTTP {img_resp.status_code}")

    # Nếu KHÔNG ảnh nào thành công thì phải báo lỗi. Trước đây hàm trả về []
    # nên UI hiện "Gen xong 0 ảnh!" và người dùng không biết chuyện gì xảy ra.
    if not results:
        raise Exception(f"Gen ảnh GLM thất bại: {errors[0] if errors else 'không rõ nguyên nhân'}")
    return results


async def _minimax_image(
    api_key: str,
    model: str,
    prompt: str,
    refs: list[str],
    n: int,
) -> list[str]:
    """
    MiniMax Image Generation (image-01 / image-01-live).
    Hỗ trợ subject_reference — giữ nguyên ngoại hình nhân vật.
    API trả về task_id, cần poll cho đến khi done.
    """
    url = f"{MINIMAX_BASE}/image_generation"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "model": model or "image-01",
        "prompt": prompt,
        "n": min(n, 9),  # MiniMax hỗ trợ 1-9 ảnh
        "aspect_ratio": "9:16",
        "response_format": "url",
        "output_format": "png",
    }

    # Subject reference: dùng ảnh tham chiếu đầu tiên nếu có
    if refs:
        payload["subject_reference"] = [{
            "type": "character",
            "image_base64": refs[0],
        }]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            raise Exception("MiniMax Image 429: Hết quota/rate limit")
        if resp.status_code in (401, 403):
            raise Exception("MiniMax Image 401/403: API key không hợp lệ")
        if resp.status_code != 200:
            raise Exception(f"MiniMax Image lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) not in (0, None):
            raise Exception(f"MiniMax lỗi: {base_resp.get('status_msg', 'Unknown')}")

        task_id = data.get("task_id")
        if not task_id:
            raise Exception("MiniMax không trả về task_id")

    # Poll kết quả
    poll_url = f"{MINIMAX_BASE}/query/image_generation"
    for attempt in range(30):  # Tối đa 30 lần × 3s = 90s
        await asyncio.sleep(3)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                poll_url,
                params={"task_id": task_id},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if r.status_code != 200:
                continue
            poll_data = r.json()
            status = poll_data.get("status", "")
            if status == "Success":
                images_data = poll_data.get("data", {}).get("image_urls", [])
                # Download ảnh về và convert sang base64
                results = []
                async with httpx.AsyncClient(timeout=30) as dl:
                    for img_url in images_data:
                        img_resp = await dl.get(img_url)
                        b64 = base64.b64encode(img_resp.content).decode()
                        results.append(f"data:image/png;base64,{b64}")
                return results
            elif status in ("Failed", "Error"):
                raise Exception(f"MiniMax gen ảnh thất bại: {poll_data.get('message', '')}")
            # status == "Processing" → tiếp tục poll

    raise Exception("MiniMax Image timeout: quá 90 giây chưa có kết quả")
