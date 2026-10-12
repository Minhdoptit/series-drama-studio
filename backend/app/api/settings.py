from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import httpx

from app.database import get_session
from app.models import ApiKey, User, utcnow
from app.services.auth_service import get_current_user
from app.services.encryption_service import encrypt, decrypt

router = APIRouter()

# Danh sách model lấy thẳng từ tầng service — nơi thực sự gọi API. Khai báo lại
# ở đây từng khiến UI chào những model backend không hỗ trợ (Vidu, cogview-3-*).
from app.services.llm_service import LLM_MODELS
from app.services.image_service import IMAGE_MODELS
from app.services.video_service import VIDEO_MODELS


class ApiKeyUpdate(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_key: Optional[str] = None

    image_provider: Optional[str] = None
    image_model: Optional[str] = None
    image_key: Optional[str] = None

    video_provider: Optional[str] = None
    video_model: Optional[str] = None
    video_key: Optional[str] = None


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    config = result.scalar_one_or_none()
    if not config:
        return {
            "llm_provider": "gemini", "llm_model": "gemini-2.0-flash", "llm_key_set": False,
            "image_provider": "gemini", "image_model": "imagen-3", "image_key_set": False,
            "video_provider": "kling", "video_model": "kling-v2-master", "video_key_set": False,
        }
    return {
        "llm_provider": config.llm_provider, "llm_model": config.llm_model,
        "llm_key_set": bool(config.llm_key_enc),
        "image_provider": config.image_provider, "image_model": config.image_model,
        "image_key_set": bool(config.image_key_enc),
        "video_provider": config.video_provider, "video_model": config.video_model,
        "video_key_set": bool(config.video_key_enc),
    }


@router.put("/api-keys")
async def update_api_keys(
    body: ApiKeyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    config = result.scalar_one_or_none()
    if not config:
        config = ApiKey(user_id=current_user.id)

    if body.llm_provider is not None:
        config.llm_provider = body.llm_provider
    if body.llm_model is not None:
        config.llm_model = body.llm_model
    if body.llm_key:
        config.llm_key_enc = encrypt(body.llm_key)

    if body.image_provider is not None:
        config.image_provider = body.image_provider
    if body.image_model is not None:
        config.image_model = body.image_model
    if body.image_key:
        config.image_key_enc = encrypt(body.image_key)

    if body.video_provider is not None:
        config.video_provider = body.video_provider
    if body.video_model is not None:
        config.video_model = body.video_model
    if body.video_key:
        config.video_key_enc = encrypt(body.video_key)

    config.updated_at = utcnow()
    session.add(config)
    await session.commit()
    return {"message": "Đã lưu cài đặt API"}


@router.post("/api-keys/test")
async def test_api_key(
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Test API key connectivity."""
    key_type = body.get("type")  # "llm", "image", "video"
    provider = body.get("provider")
    api_key = body.get("api_key")

    if not all([key_type, provider, api_key]):
        raise HTTPException(400, "Thiếu thông tin: type, provider, api_key")

    # Nếu user test key đã lưu (chưa nhập key mới) → lấy từ DB
    if api_key == "___saved___":
        result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
        config = result.scalar_one_or_none()
        if not config:
            return {"ok": False, "message": "Chưa có API key nào được lưu"}
        key_field = f"{key_type}_key_enc"
        enc_key = getattr(config, key_field, None)
        if not enc_key:
            return {"ok": False, "message": f"Chưa lưu key cho {key_type}. Nhập key mới và bấm Lưu trước."}
        api_key = decrypt(enc_key)

    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return {"ok": True, "message": "Kết nối Gemini thành công ✓"}
                return {"ok": False, "message": f"Gemini trả về lỗi {resp.status_code}"}

        elif provider == "openai":
            url = "https://api.openai.com/v1/models"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    return {"ok": True, "message": "Kết nối OpenAI thành công ✓"}
                return {"ok": False, "message": f"OpenAI trả về lỗi {resp.status_code}"}

        elif provider == "minimax":
            # Test bằng cách gọi list models
            url = "https://api.minimax.io/v1/models"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    return {"ok": True, "message": "Kết nối MiniMax thành công ✓"}
                # MiniMax có thể không có /models — thử parse lỗi
                try:
                    err = resp.json().get("base_resp", {}).get("status_msg", f"HTTP {resp.status_code}")
                except Exception:
                    err = f"HTTP {resp.status_code}"
                return {"ok": False, "message": f"MiniMax: {err}"}

        elif provider == "glm":
            url = "https://api.z.ai/api/paas/v4/models"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    return {"ok": True, "message": "Kết nối GLM (Zhipu AI) thành công ✓"}
                return {"ok": False, "message": f"GLM trả về lỗi {resp.status_code}"}

        elif provider in ("kling", "runway"):
            return {"ok": True, "message": f"Key {provider} đã lưu — sẽ kiểm tra khi gen video thật"}

        return {"ok": False, "message": f"Provider không nhận ra: {provider}"}
    except Exception as e:
        return {"ok": False, "message": f"Lỗi kết nối: {e}"}


@router.get("/models")
async def get_model_options():
    """Return available models per provider."""
    return {"llm": LLM_MODELS, "image": IMAGE_MODELS, "video": VIDEO_MODELS}


@router.post("/test-gemini-raw")
async def test_gemini_raw(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Gửi request tối giản đến Gemini và trả về raw response để debug."""
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    config = result.scalar_one_or_none()
    if not config or not config.llm_key_enc:
        raise HTTPException(400, "Chưa có API key")

    from app.services.encryption_service import decrypt
    api_key = decrypt(config.llm_key_enc)
    model = config.llm_model or "gemini-2.0-flash"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "Trả lời 'OK' bằng tiếng Việt."}]}],
        "generationConfig": {"maxOutputTokens": 20}
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            return {
                "status_code": resp.status_code,
                "model": model,
                "key_prefix": api_key[:8] + "...",
                "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:500],
            }
    except Exception as e:
        return {"error": str(e)}
