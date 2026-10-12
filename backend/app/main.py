# Lưu ý về event loop trên Windows:
# psycopg async cần SelectorEventLoop. Việc chọn loop được xử lý ở run.py (uvicorn
# tự tạo loop mới qua asyncio.run nên mọi lệnh set_event_loop ở đây đều bị bỏ qua).
# Hệ quả: SelectorEventLoop không hỗ trợ subprocess, nên chỗ gọi ffmpeg dùng
# subprocess đồng bộ trong thread — xem video_service.concat_videos.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os, pathlib

from app.database import create_db_and_tables

# Ensure data dirs exist
DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))
for sub in ["uploads", "assets", "videos", "thumbnails"]:
    (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    # Reset zombie videos: task bị chết vì backend restart
    from app.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(
            "UPDATE videos SET status='error', error_msg='Task bi huy do backend restart' "
            "WHERE status='running'"
        ))
        await session.commit()
        if result.rowcount:
            import logging
            logging.getLogger("main").warning(f"Reset {result.rowcount} zombie video task(s) on startup")
    
    # Tự động dọn dẹp DB: mỗi scene chỉ giữ tối đa 2 video mới nhất (xóa tất cả video cũ hơn khỏi DB & đĩa)
    try:
        from app.api.videos import cleanup_all_old_videos
        await cleanup_all_old_videos()
    except Exception as e:
        import logging
        logging.getLogger("main").error(f"Lỗi khi cleanup old videos on startup: {e}")

    yield


app = FastAPI(
    title="Series Drama Studio API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: KHÔNG dùng "*" kèm allow_credentials=True — Starlette sẽ echo lại mọi
# Origin, tức là bất kỳ website nào cũng gọi được API kèm thông tin xác thực.
# Khai báo whitelist qua biến môi trường CORS_ORIGINS (ngăn cách bằng dấu phẩy).
_default_origins = "http://localhost:5173,http://localhost:3000"
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", _default_origins).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")

# Routers (import after app created)
from app.api import auth, projects, episodes, scripts, documents, images, videos, settings

app.include_router(auth.router,      prefix="/auth",      tags=["Auth"])
app.include_router(projects.router,  prefix="/projects",  tags=["Projects"])
app.include_router(episodes.router,  prefix="/projects",  tags=["Episodes"])
app.include_router(scripts.router,   prefix="/projects",  tags=["Scripts"])
app.include_router(documents.router, prefix="/projects",  tags=["Documents"])
app.include_router(images.router,    prefix="/projects",  tags=["Images"])
app.include_router(videos.router,    prefix="/projects",  tags=["Videos"])
app.include_router(settings.router,  prefix="/settings",  tags=["Settings"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Series Drama Studio"}
