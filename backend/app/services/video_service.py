import httpx, pathlib, os, uuid, asyncio
from app.services.encryption_service import decrypt

DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))
KLING_BASE = "https://api.klingai.com/v1"
RUNWAY_BASE = "https://api.dev.runwayml.com/v1"
GLM_VIDEO_BASE = "https://api.z.ai/api/paas/v4"
VEO3_BASE = "https://generativelanguage.googleapis.com"


def _build_video_prompt(scene, images_data: list, extra_prompt: str) -> str:
    parts = []
    if images_data:
        label_lines = []
        for idx, img in enumerate(images_data, 1):
            lbl = img.get("label") or f"Nhân vật #{idx}"
            label_lines.append(f"Ảnh #{idx} ({lbl})")
        parts.append(f"[TẠO HÌNH NHÂN VẬT THAM CHIẾU: {', '.join(label_lines)}].")

    if scene.shot_type:
        parts.append(f"[{scene.shot_type}]")
    if scene.action_desc:
        parts.append(scene.action_desc)
    if scene.location:
        parts.append(f"Địa điểm: {scene.location}.")
    if extra_prompt:
        parts.append(extra_prompt)
    parts.append("Phong cách hoạt hình 3D Pixar mềm. Nhân vật con vật cách điệu dáng người. Khung dọc 9:16.")
    return " ".join(parts)


def _build_veo3_prompt(scene, images_data: list, extra_prompt: str) -> str:
    """
    Prompt tối ưu cho Veo3: đưa đầy đủ hội thoại (voice_over) vào
    để Veo3 sync animation với lời thoại của nhân vật.
    """
    parts = []

    # Mô tả nhân vật từ ảnh tham chiếu (tối đa 3 ảnh với Veo3)
    if images_data:
        chars = [img.get("label") or f"Nhân vật #{i+1}" for i, img in enumerate(images_data[:3])]
        parts.append(f"Nhân vật tham chiếu: {', '.join(chars)}.")

    # Góc máy và bối cảnh
    if scene.shot_type:
        parts.append(f"[{scene.shot_type}]")
    if scene.location:
        parts.append(f"Bối cảnh: {scene.location}.")

    # Hành động
    if scene.action_desc:
        parts.append(scene.action_desc)

    # Hội thoại — Veo3 có thể sync animation với lời thoại
    if scene.voice_over:
        parts.append(f'Lời thoại trong cảnh: "{scene.voice_over}"')

    if extra_prompt:
        parts.append(extra_prompt)

    parts.append("Phong cách hoạt hình 3D Pixar mềm. Nhân vật con vật cách điệu dáng người. Tỉ lệ dọc 9:16.")
    return " ".join(parts)


async def generate_video_ai(scene, images_data, extra_prompt, api_config, project_id, video_size: str = "720x1280", duration: int = 5) -> str:
    provider = api_config.video_provider or "kling"
    model = api_config.video_model or "kling-v2-master"

    # Tất cả Gemini video models dùng chung Gemini API key
    # Ưu tiên video_key_enc, fallback sang image_key_enc (user thường đã cài ở Image AI)
    if provider == "gemini":
        raw_key = api_config.video_key_enc or api_config.image_key_enc
        if not raw_key:
            raise ValueError("Chưa cấu hình Gemini API key cho Video AI hoặc Image AI")
        api_key = decrypt(raw_key)
    else:
        api_key = decrypt(api_config.video_key_enc)

    if isinstance(images_data, str):
        images_data = [{"path": images_data, "label": "Nhân vật tham chiếu"}]
    elif not images_data:
        images_data = []

    # Dispatch Gemini video models
    if provider == "gemini":
        prompt = _build_veo3_prompt(scene, images_data, extra_prompt or "")
        if model.startswith("veo") or model.startswith("gemini-omni"):
            return await _veo3_generate(api_key, model, prompt, images_data, project_id, scene.id, video_size)
        raise ValueError(f"Gemini video model không hỗ trợ: {model}")

    prompt = _build_video_prompt(scene, images_data, extra_prompt or "")

    if provider == "kling":
        return await _kling_generate(api_key, model, prompt, images_data, project_id, scene.id)
    elif provider == "runway":
        return await _runway_generate(api_key, model, prompt, images_data, project_id, scene.id)
    elif provider == "glm":
        return await _glm_generate(api_key, model, prompt, images_data, project_id, scene.id, video_size, duration)
    else:
        raise ValueError(f"Video provider không hỗ trợ: {provider}")


# ─── Kling ────────────────────────────────────────────────

async def _kling_generate(api_key, model, prompt, images_data, project_id, scene_id) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "duration": 5,
        "aspect_ratio": "9:16",
        "cfg_scale": 0.5,
    }
    if images_data and isinstance(images_data, list) and len(images_data) > 0:
        first_img = images_data[0].get("path")
        if first_img and pathlib.Path(first_img).exists():
            import base64, aiofiles
            async with aiofiles.open(first_img, "rb") as f:
                img_data = await f.read()
            payload["image"] = f"data:image/png;base64,{base64.b64encode(img_data).decode()}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{KLING_BASE}/videos/image2video", json=payload, headers=headers)
        if resp.status_code not in (200, 201, 202):
            raise Exception(f"Kling API lỗi {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        task_id = data.get("data", {}).get("task_id") or data.get("task_id")
        if not task_id:
            raise Exception(f"Kling không trả về task_id: {data}")

    return await _kling_poll(api_key, task_id, project_id, scene_id)


async def _kling_poll(api_key, task_id, project_id, scene_id, max_wait=600) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    elapsed = 0
    while elapsed < max_wait:
        await asyncio.sleep(10)
        elapsed += 10
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{KLING_BASE}/videos/image2video/{task_id}", headers=headers)
            data = resp.json()
        status = data.get("data", {}).get("task_status") or data.get("status")
        if status == "succeed":
            video_url = (
                data.get("data", {}).get("task_result", {}).get("videos", [{}])[0].get("url")
                or data.get("video_url")
            )
            if not video_url:
                raise Exception("Kling không trả về video URL")
            return await _download_video(video_url, project_id, scene_id)
        elif status in ("failed", "error"):
            msg = data.get("data", {}).get("task_status_msg") or "Kling gen video thất bại"
            raise Exception(msg)
    raise Exception("Timeout chờ Kling gen video (>10 phút)")


# ─── Runway ───────────────────────────────────────────────

async def _runway_generate(api_key, model, prompt, images_data, project_id, scene_id) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }
    payload = {
        "model": model or "gen3a_turbo",
        "promptText": prompt,
        "ratio": "720:1280",
        "duration": 5,
    }
    if images_data and isinstance(images_data, list) and len(images_data) > 0:
        first_img = images_data[0].get("path")
        if first_img and pathlib.Path(first_img).exists():
            import base64, aiofiles
            async with aiofiles.open(first_img, "rb") as f:
                img_data = await f.read()
            payload["promptImage"] = f"data:image/png;base64,{base64.b64encode(img_data).decode()}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{RUNWAY_BASE}/image_to_video", json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            raise Exception(f"Runway API lỗi {resp.status_code}: {resp.text[:300]}")
        task_id = resp.json().get("id")

    elapsed = 0
    while elapsed < 600:
        await asyncio.sleep(10)
        elapsed += 10
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{RUNWAY_BASE}/tasks/{task_id}", headers=headers)
            data = resp.json()
        status = data.get("status")
        if status == "SUCCEEDED":
            return await _download_video(data.get("output", [None])[0], project_id, scene_id)
        elif status in ("FAILED", "CANCELLED"):
            raise Exception(data.get("failure") or "Runway gen video thất bại")
    raise Exception("Timeout chờ Runway gen video (>10 phút)")


# ─── GLM / CogVideoX (image-to-video async) ──────────────

# Nguồn dữ liệu DUY NHẤT cho model video mỗi provider. settings.py import từ đây
# thay vì khai báo lại, và frontend lấy qua GET /settings/models.
#
# Lưu ý: danh sách GLM chỉ gồm model mà _glm_generate thực sự gọi được. Trước đây
# UI còn chào cả vidu-q1/vidu-q2/... nhưng backend âm thầm đổi hết về cogvideox-3,
# nên người dùng chọn Vidu vẫn nhận video CogVideoX mà không hề biết. Muốn hỗ trợ
# Vidu thì phải viết thêm nhánh gọi API riêng rồi bổ sung vào đây.
VIDEO_MODELS: dict[str, list[str]] = {
    "kling": ["kling-v2-master", "kling-v1.6-standard", "kling-v1-5"],
    "runway": ["gen3a_turbo", "gen3a"],
    "glm": ["cogvideox-3"],
    "gemini": [
        "veo-3.1-generate-preview",        # Standard — $0.40/s (720p & 1080p), $0.60/s (4k)
        "veo-3.1-fast-generate-preview",   # Fast     — $0.10/s (720p), $0.12/s (1080p), $0.30/s (4k)
        "veo-3.1-lite-generate-preview",   # Lite     — $0.05/s (720p), $0.08/s (1080p), không có 4k
        "veo-3.0-generate-001",            # Veo 3 cũ, đã deprecated — $0.40/s, giá bằng 3.1 Standard
        "gemini-omni-flash-preview",       # ~$0.10/s quy đổi từ giá token
    ],
}

# Quy đổi video_size (do user chọn) → (aspect_ratio, resolution) cho Veo.
# Veo chỉ nhận aspect "16:9" / "9:16" và resolution "720p" / "1080p" / "4k".
# Trước đây code chỉ suy ra aspect rồi bỏ qua resolution, nên bấm 4K vẫn nhận
# 720p — nút chọn tỉ lệ trên UI không có tác dụng gì tới chất lượng.
_VEO_SIZE_MAP: dict[str, tuple[str, str]] = {
    "720x1280":  ("9:16", "720p"),
    "1280x720":  ("16:9", "720p"),
    "1080x1920": ("9:16", "1080p"),
    "1920x1080": ("16:9", "1080p"),
    "2048x1080": ("16:9", "1080p"),   # 2K DCI — Veo không có mức này, lấy gần nhất
    "3840x2160": ("16:9", "4k"),
    "1024x1024": ("16:9", "720p"),    # Veo không hỗ trợ khung vuông
}

# Model không hỗ trợ 4k (theo bảng tính năng của Google)
_VEO_MODELS_WITHOUT_4K = {
    "veo-3.1-lite-generate-preview",
    "veo-3.0-generate-001",
    "gemini-omni-flash-preview",
}


async def _glm_generate(api_key: str, model: str, prompt: str, images_data, project_id: str, scene_id: str, video_size: str = "720x1280", duration: int = 5) -> str:
    """
    GLM Video generation (async).
    - Có ảnh  → dùng Vidu image-to-video (hỗ trợ nhiều ảnh)
    - Không ảnh → dùng CogVideoX text-to-video

    Docs: https://docs.z.ai/api-reference/video/generate-video
    POST  {GLM_VIDEO_BASE}/videos/generations
    GET   {GLM_VIDEO_BASE}/videos/generations/{task_id}
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Báo lỗi rõ ràng thay vì âm thầm đổi model — user cần biết mình gen bằng gì
    if model not in VIDEO_MODELS["glm"]:
        raise ValueError(
            f"Model video GLM không hỗ trợ: {model}. "
            f"Hiện hỗ trợ: {', '.join(VIDEO_MODELS['glm'])}"
        )
    safe_duration = 10 if duration == 10 else 5

    payload: dict = {
        "model": model,
        "prompt": prompt,
        "duration": safe_duration,
        "size": video_size,          # ti le duoc chon boi user
        "quality": "speed",          # nhanh hon; dung "quality" neu muon chat luong cao
        "with_audio": True,          # gen AI sound effects (tieng dong, nhac nen)
    }

    # Gắn tất cả các ảnh tham chiếu dạng mảng base64
    if images_data and isinstance(images_data, list):
        import base64, aiofiles
        img_urls = []
        for img_item in images_data:
            ipath = img_item.get("path")
            if ipath and pathlib.Path(ipath).exists():
                async with aiofiles.open(ipath, "rb") as f:
                    img_bytes = await f.read()
                size_mb = len(img_bytes) / (1024 * 1024)
                if size_mb <= 5:
                    b64 = base64.b64encode(img_bytes).decode()
                    img_urls.append(f"data:image/png;base64,{b64}")
        if img_urls:
            payload["image_url"] = img_urls   # array of base64 images!

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{GLM_VIDEO_BASE}/videos/generations",
            json=payload,
            headers=headers,
        )
        if resp.status_code == 429:
            raise Exception("GLM 429: Hết quota. Xem https://z.ai/manage-apikey/rate-limits")
        if resp.status_code in (401, 403):
            raise Exception("GLM 401/403: API key không hợp lệ")
        if resp.status_code not in (200, 201, 202):
            raise Exception(f"GLM Video API lỗi {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise Exception(f"GLM không trả về task id: {data}")

    return await _glm_poll(api_key, task_id, project_id, scene_id)


async def _glm_poll(api_key: str, task_id: str, project_id: str, scene_id: str, max_wait: int = 1200) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    elapsed = 0

    while elapsed < max_wait:
        await asyncio.sleep(15)
        elapsed += 15

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GLM_VIDEO_BASE}/async-result/{task_id}",   # endpoint đúng theo docs
                headers=headers,
            )
            data = resp.json()

        # GLM status: PROCESSING | SUCCESS | FAIL
        raw_status = data.get("task_status") or data.get("status") or ""
        status = str(raw_status).upper()

        if status == "SUCCESS":
            result = data.get("video_result") or data.get("result") or {}
            if isinstance(result, list):
                result = result[0] if result else {}
            video_url = result.get("url") or result.get("video_url")
            if not video_url:
                raise Exception(f"GLM không trả về video URL: {data}")
            return await _download_video(video_url, project_id, scene_id)

        elif status in ("FAIL", "FAILED", "ERROR"):
            msg = data.get("task_status_msg") or data.get("message") or "GLM gen video thất bại"
            raise Exception(f"GLM lỗi: {msg}")

    raise Exception(f"Timeout chờ GLM gen video (>{max_wait // 60} phút)")


# ─── Veo3 (Google AI) ───────────────────────────────────

async def _veo3_generate(
    api_key: str, model: str, prompt: str, images_data: list,
    project_id: str, scene_id: str, video_size: str = "720x1280"
) -> str:
    """
    Veo image-to-video qua google-genai SDK.

    video_size: một trong các khoá của _VEO_SIZE_MAP, quyết định CẢ tỉ lệ khung
    lẫn độ phân giải xuất ra (và do đó cả chi phí — Veo tính tiền theo giây và
    theo mức phân giải).
    """
    import concurrent.futures

    veo_aspect, veo_resolution = _VEO_SIZE_MAP.get(video_size, ("9:16", "720p"))

    if veo_resolution == "4k" and model in _VEO_MODELS_WITHOUT_4K:
        raise ValueError(
            f"Model {model} không hỗ trợ 4K. Chọn veo-3.1-generate-preview / "
            f"veo-3.1-fast-generate-preview, hoặc giảm xuống 1080p."
        )

    safe_model = model

    def _sync_generate():
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise Exception("Thiếu thư viện google-genai. Chạy: pip install google-genai>=1.0.0")

        import time
        # QUAN TRỌNG: phải có api_version="v1beta" để Veo3 hoạt động
        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=api_key,
        )

        # Build reference images từ ảnh nhân vật (đọc bytes trực tiếp)
        ref_images = []
        for img_item in images_data[:3]:  # max 3 ảnh reference
            ipath = img_item.get("path")
            if ipath and pathlib.Path(ipath).exists():
                try:
                    with open(ipath, "rb") as f:
                        img_bytes = f.read()
                    ext = pathlib.Path(ipath).suffix.lower()
                    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
                    ref_images.append(
                        types.VideoGenerationReferenceImage(
                            image=types.Image(image_bytes=img_bytes, mime_type=mime),
                            reference_type=types.VideoGenerationReferenceType.ASSET,
                        )
                    )
                except Exception as e:
                    import logging
                    logging.warning(f"Veo3: không đọc được ảnh {ipath}: {e}")

        # Veo nhận duration 4/6/8 giây, nhưng 1080p và 4k bắt buộc đúng 8 giây —
        # giữ cố định 8 để mọi mức phân giải đều hợp lệ (UI cũng khoá 8s cho Veo).
        config_kwargs: dict = {
            "aspect_ratio": veo_aspect,
            "resolution": veo_resolution,
            "number_of_videos": 1,
            "duration_seconds": 8,
        }
        if ref_images:
            config_kwargs["reference_images"] = ref_images

        # Gọi Veo3 API — dùng source=GenerateVideosSource(prompt=), KHÔNG dùng prompt= trực tiếp
        last_err = None
        for attempt in range(2):
            try:
                operation = client.models.generate_videos(
                    model=safe_model,
                    source=types.GenerateVideosSource(prompt=prompt),
                    config=types.GenerateVideosConfig(**config_kwargs),
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt == 0:
                    import logging, time as t2
                    logging.warning("Veo3 429 — chờ 60s rồi thử lại...")
                    t2.sleep(60)
                    last_err = e
                    continue
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    raise Exception(
                        "Veo3 429 RESOURCE_EXHAUSTED: Hết quota hoặc chưa bật billing. "
                        "Veo3 yêu cầu gói Paid tại https://aistudio.google.com/plan_information"
                    )
                raise
        else:
            if last_err:
                raise Exception("Veo3 429: Hết quota hoặc chưa bật billing.")

        # Poll đến khi xong
        max_wait = 1200
        elapsed = 0
        while not operation.done and elapsed < max_wait:
            time.sleep(20)
            elapsed += 20
            operation = client.operations.get(operation)

        if not operation.done:
            raise Exception("Timeout chờ Veo3 gen video (>20 phút)")

        # Lấy kết quả — dùng operation.result (không phải operation.response)
        result = operation.result
        if not result:
            raise Exception(f"Veo3 không có result: {operation}")

        videos = result.generated_videos
        if not videos:
            raise Exception("Veo3 không trả về video nào")

        return videos[0], client

    # Chạy sync code trong thread pool (genai SDK không async native)
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        generated_video, client_ref = await loop.run_in_executor(pool, _sync_generate)

    # Lưu video xuống disk — dùng generated_video.video.save() theo pattern chính thức
    video_dir = DATA_DIR / "videos" / project_id
    video_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"scene_{scene_id[:8]}_{uuid.uuid4().hex[:6]}.mp4"
    file_path = video_dir / file_name

    def _save_video():
        client_ref.files.download(file=generated_video.video)
        generated_video.video.save(str(file_path))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, _save_video)

    if not file_path.exists() or file_path.stat().st_size < 1000:
        raise Exception("File video Veo3 tải về không hợp lệ hoặc rỗng")

    return str(file_path.relative_to(DATA_DIR)).replace("\\", "/")



# ─── Ghép video (FFmpeg concat) ──────────────────────────

async def concat_videos(video_abs_paths: list, output_abs_path: str) -> None:
    """
    Ghép nhiều clip thành 1 file bằng FFmpeg concat demuxer (stream copy, không re-encode).

    Args:
        video_abs_paths: list đường dẫn tuyệt đối đến từng clip theo thứ tự cảnh
        output_abs_path: đường dẫn output tuyệt đối

    Raises:
        Exception nếu FFmpeg không tìm thấy hoặc ghép lỗi
    """
    if not video_abs_paths:
        raise ValueError("Không có video nào để ghép")

    # Tạo file list tạm cho ffmpeg
    list_path = pathlib.Path(output_abs_path).parent / f"_concat_{uuid.uuid4().hex[:6]}.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for p in video_abs_paths:
            # concat demuxer: escape dấu nháy đơn trong đường dẫn
            safe_p = str(p).replace("\\", "/").replace("'", r"'\''")
            f.write(f"file '{safe_p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(output_abs_path),
    ]

    # Dùng subprocess đồng bộ trong thread thay vì asyncio.create_subprocess_exec:
    # trên Windows app chạy SelectorEventLoop (bắt buộc cho psycopg async), mà loop
    # này KHÔNG hỗ trợ subprocess → create_subprocess_exec ném NotImplementedError.
    import subprocess

    def _run_ffmpeg():
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )

    try:
        proc = await asyncio.to_thread(_run_ffmpeg)
        if proc.returncode != 0:
            raise Exception(f"FFmpeg lỗi: {proc.stderr.decode(errors='replace')[-500:]}")
    except subprocess.TimeoutExpired:
        raise Exception("Timeout ghép video (>5 phút)")
    except FileNotFoundError:
        raise Exception("FFmpeg không tìm thấy — cần cài ffmpeg và thêm vào PATH")
    finally:
        list_path.unlink(missing_ok=True)


# ─── Download helper ─────────────────────────────────────

async def _download_video(url: str, project_id: str, scene_id: str) -> str:
    video_dir = DATA_DIR / "videos" / project_id
    video_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"scene_{scene_id[:8]}_{uuid.uuid4().hex[:6]}.mp4"
    file_path = video_dir / file_name

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    last_err = ""
    import aiofiles

    # Retry up to 5 times (Z.AI CDN propagation delay)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        for attempt in range(5):
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    async with aiofiles.open(file_path, "wb") as f:
                        await f.write(resp.content)
                    safe_path = str(file_path.relative_to(DATA_DIR)).replace("\\", "/")
                    return safe_path
                else:
                    last_err = f"HTTP {resp.status_code}"
            except Exception as e:
                last_err = str(e)
            await asyncio.sleep(3)

    raise Exception(f"Không thể tải video từ URL Z.AI ({last_err})")
