"""
Migration: Thêm cột extra_prompt vào bảng scenes (nếu chưa có)

Chạy 1 lần từ thư mục backend/:
    python migrate_scene_extra_prompt.py

Idempotent: chạy nhiều lần không crash.
"""
import asyncio
import sys
import os
import selectors

# Fix Windows ProactorEventLoop incompatibility with psycopg async
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Kiểm tra extra_prompt đã tồn tại chưa
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='scenes' AND column_name='extra_prompt'"
        ))
        if result.fetchone():
            print("[OK] Already migrated -- extra_prompt column exists, skipping")
            return

        print("Running migration: add extra_prompt to scenes...")
        await conn.execute(text(
            "ALTER TABLE scenes ADD COLUMN extra_prompt VARCHAR"
        ))
        print("[OK] Migration complete: extra_prompt column added to scenes")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop.run_until_complete(migrate())
    else:
        asyncio.run(migrate())
