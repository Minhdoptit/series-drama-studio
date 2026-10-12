"""
Test Veo3 API - theo pattern chinh thuc (VideoGenerationSource, api_version=v1beta)
"""
import sys
import pathlib
import time

import os

API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
MODEL   = "veo-3.1-generate-preview"

# Tu dong tim anh test trong data/assets
TEST_IMAGE = None
DATA_DIR = pathlib.Path("../data/assets")
if DATA_DIR.exists():
    imgs = list(DATA_DIR.rglob("*.png")) + list(DATA_DIR.rglob("*.jpg"))
    if imgs:
        TEST_IMAGE = imgs[0]

print("=" * 60)
print("  Veo3 API Test (official pattern)")
print(f"  Model  : {MODEL}")
print(f"  Key    : {API_KEY[:12]}...")
print(f"  Image  : {TEST_IMAGE}")
print("=" * 60)

from google import genai
from google.genai import types

# QUAN TRONG: can api_version="v1beta"
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=API_KEY,
)

# Build config
config_kwargs = {
    "aspect_ratio": "9:16",
    "number_of_videos": 1,
}

# Them reference image neu co
if TEST_IMAGE and TEST_IMAGE.exists():
    print(f"\n[IMG] Dinh kem anh reference: {TEST_IMAGE.name}")
    with open(TEST_IMAGE, "rb") as f:
        img_bytes = f.read()
    ext = TEST_IMAGE.suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    config_kwargs["reference_images"] = [
        types.VideoGenerationReferenceImage(
            image=types.Image(image_bytes=img_bytes, mime_type=mime),
            reference_type=types.VideoGenerationReferenceType.ASSET,
        )
    ]
    print(f"[OK] reference_image: {len(img_bytes)//1024}KB, {mime}")
else:
    print("\n[SKIP] Khong co anh reference - text-to-video")

prompt = (
    "A cute cartoon deer character jumping happily on a rocky mountain path. "
    "3D Pixar-style soft animation, stylized animal character. Cinematic."
)
print(f"\n[PROMPT] {prompt[:100]}...")
print(f"[CONFIG] {list(config_kwargs.keys())}")

print("\n[GEN] Calling Veo3 API...")
try:
    t0 = time.time()
    operation = client.models.generate_videos(
        model=MODEL,
        source=types.GenerateVideosSource(prompt=prompt),
        config=types.GenerateVideosConfig(**config_kwargs),
    )
    print(f"[OK] Operation started: {operation.name}")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Poll
print("\n[POLL] Waiting for video (3-8 minutes)...")
elapsed = 0
while not operation.done:
    time.sleep(15)
    elapsed += 15
    operation = client.operations.get(operation)
    print(f"  [{elapsed}s] {'DONE!' if operation.done else 'processing...'}")

# Ket qua
result = operation.result
if not result:
    print(f"[FAIL] No result: {operation}")
    sys.exit(1)

videos = result.generated_videos
if not videos:
    print("[FAIL] No videos generated")
    sys.exit(1)

print(f"\n[OK] Got {len(videos)} video(s)")
for n, gv in enumerate(videos):
    assert gv.video is not None
    print(f"  URI: {gv.video.uri}")
    client.files.download(file=gv.video)
    out_path = f"test_veo3_output_{n}.mp4"
    gv.video.save(out_path)
    p = pathlib.Path(out_path)
    print(f"  Saved: {p.absolute()} ({p.stat().st_size//1024}KB)")

print(f"\n{'='*60}")
print(f"  SUCCESS! Time: {elapsed}s")
print(f"{'='*60}")
