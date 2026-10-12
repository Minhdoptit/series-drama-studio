"""
Test toàn bộ flow gen kịch bản với GLM
Chạy: python test_glm_flow.py
"""
import asyncio, json, sys, os
from dotenv import load_dotenv

load_dotenv()

# ─── Giả lập payload FE gửi xuống ────────────────────────────────────
FE_PAYLOAD = {
    "style": "3D Pixar mềm, nhân vật con vật cách điệu dáng người",
    "characters": [
        {"name": "Con Mèo", "age": "10", "description": "Nhân vật chính"},
        {"name": "Con Chó", "age": "30", "description": "Nhân Vật Phụ"},
    ],
    "content": "Con chó dạy con mèo học",
    "duration_sec": 50,
    "document_ids": [],
}

GLM_API_KEY = os.getenv("GLM_API_KEY", "")
if not GLM_API_KEY:
    GLM_API_KEY = input("Enter GLM API key (from open.bigmodel.cn): ").strip()

GLM_MODEL = os.getenv("GLM_MODEL", "glm-4-flash")


def test_build_prompt():
    print("\n" + "="*60)
    print("STEP 1: Build Prompt")
    print("="*60)

    from app.services.llm_service import _build_script_prompt

    class Char:
        def __init__(self, d):
            self.name = d["name"]
            self.age = d.get("age")
            self.description = d.get("description")

    characters = [Char(c) for c in FE_PAYLOAD["characters"]]
    prompt = _build_script_prompt(
        title=None,
        style=FE_PAYLOAD["style"],
        characters=characters,
        content=FE_PAYLOAD["content"],
        duration_sec=FE_PAYLOAD["duration_sec"],
        doc_texts=[],
    )
    print(f"OK  Prompt built — {len(prompt)} ky tu (~{len(prompt)//4} tokens)")
    print(f"\n--- PROMPT PREVIEW ---")
    print(prompt[:300])
    print("...")
    return prompt


async def test_glm_api_direct(prompt: str):
    print("\n" + "="*60)
    print(f"STEP 2: Goi GLM API ({GLM_MODEL})")
    print("="*60)

    import httpx
    url = "https://api.z.ai/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": "Ban la AI chuyen viet kich ban hoat hinh. Luon tra ve JSON hop le."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    print(f"-> URL: {url}")
    print(f"-> Model: {GLM_MODEL}")
    print(f"-> Est. input tokens: ~{len(json.dumps(payload, ensure_ascii=False))//4}")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)

        print(f"-> HTTP Status: {resp.status_code}")

        if resp.status_code == 429:
            print("FAIL 429 Rate limit — GLM Lite bi gioi han. Doi 1 phut roi thu lai.")
            try:
                print(f"   Detail: {resp.json()}")
            except Exception:
                print(f"   Body: {resp.text[:300]}")
            return None
        elif resp.status_code in (401, 403):
            print("FAIL 401/403 — API key sai hoac het han")
            print(f"   Response: {resp.text[:300]}")
            return None
        elif resp.status_code != 200:
            print(f"FAIL Loi {resp.status_code}: {resp.text[:300]}")
            return None

        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]
        print(f"OK  Nhan duoc {len(raw_text)} ky tu tu GLM")
        print(f"\n--- RAW RESPONSE (300 ky tu dau) ---")
        print(raw_text[:300])
        return raw_text

    except Exception as e:
        print(f"FAIL Exception: {type(e).__name__}: {e}")
        return None


def test_parse_json(raw_text: str):
    print("\n" + "="*60)
    print("STEP 3: Parse JSON tu response")
    print("="*60)

    from app.services.llm_service import _parse_json_response
    try:
        data = _parse_json_response(raw_text)
        print("OK  Parse JSON thanh cong!")
        print(f"   title  : {data.get('title')}")
        print(f"   content: {str(data.get('content',''))[:80]}...")
        scenes = data.get("scenes", [])
        print(f"   scenes : {len(scenes)} canh")
        for s in scenes[:3]:
            print(f"     [{s.get('scene_no')}] {s.get('location')} | {str(s.get('action_desc',''))[:60]}")
        return data
    except Exception as e:
        print(f"FAIL Parse loi: {e}")
        print(f"   Raw (300 ky tu): {raw_text[:300]}")
        return None


async def test_via_service():
    print("\n" + "="*60)
    print("STEP 4: Test qua generate_script_from_prompt (service layer)")
    print("="*60)

    from app.services.llm_service import generate_script_from_prompt
    from app.services.encryption_service import encrypt

    class MockApiConfig:
        llm_provider = "glm"
        llm_model = GLM_MODEL
        llm_key_enc = encrypt(GLM_API_KEY)

    class Char:
        def __init__(self, d):
            self.name = d["name"]
            self.age = d.get("age")
            self.description = d.get("description")

    try:
        result = await generate_script_from_prompt(
            title=None,
            style=FE_PAYLOAD["style"],
            characters=[Char(c) for c in FE_PAYLOAD["characters"]],
            content=FE_PAYLOAD["content"],
            duration_sec=FE_PAYLOAD["duration_sec"],
            doc_texts=[],
            api_config=MockApiConfig(),
        )
        print("OK  generate_script_from_prompt thanh cong!")
        print(f"   title  : {result.get('title')}")
        print(f"   scenes : {len(result.get('scenes', []))} canh")
        return True
    except Exception as e:
        print(f"FAIL Loi: {e}")
        return False


async def main():
    print("=" * 60)
    print("GLM SCRIPT GENERATION FLOW TEST")
    print(f"   Model: {GLM_MODEL}")
    print(f"   Key:   {GLM_API_KEY[:8]}...{GLM_API_KEY[-4:] if len(GLM_API_KEY) > 12 else '???'}")
    print("=" * 60)

    prompt = test_build_prompt()

    raw = await test_glm_api_direct(prompt)
    if raw is None:
        print("\n[STOP] Dung tai Step 2 — API call that bai")
        sys.exit(1)

    parsed = test_parse_json(raw)
    if parsed is None:
        print("\n[STOP] Dung tai Step 3 — JSON parse that bai")
        sys.exit(1)

    ok = await test_via_service()

    print("\n" + "="*60)
    if ok:
        print("ALL PASS — Flow GLM hoat dong binh thuong!")
    else:
        print("PARTIAL — Steps 1-3 OK nhung service layer co van de")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
