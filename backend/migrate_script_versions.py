"""
Migration: Thêm version, is_active, parent_id vào bảng scripts

Chạy 1 lần từ thư mục backend/:
    python migrate_script_versions.py

Idempotent: chạy nhiều lần không crash.
"""
import asyncio
import sys
import os
import selectors

# Fix Windows ProactorEventLoop incompatibility with psycopg async
if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.DefaultEventLoopPolicy()
    )
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)


# Đảm bảo import được app khi chạy từ thư mục backend
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Kiểm tra column đã tồn tại chưa (idempotent check)
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='scripts' AND column_name='version'"
        ))
        if result.fetchone():
            print("✓ Already migrated — skipping")
            return

        print("Running migration: add version tracking to scripts...")

        await conn.execute(text(
            "ALTER TABLE scripts ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
        ))
        await conn.execute(text(
            "ALTER TABLE scripts ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        await conn.execute(text(
            "ALTER TABLE scripts ADD COLUMN parent_id VARCHAR REFERENCES scripts(id)"
        ))

        # Đối với scripts đã tồn tại: set version theo thứ tự created_at trong episode
        # Giữ tất cả is_active=TRUE ban đầu, sau đó normalize
        print("Normalizing existing scripts (1 active per episode)...")
        await conn.execute(text("""
            UPDATE scripts s
            SET is_active = FALSE
            WHERE s.id NOT IN (
                SELECT DISTINCT ON (episode_id) id
                FROM scripts
                ORDER BY episode_id, created_at DESC
            )
        """))

        print("OK Migration complete")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop.run_until_complete(migrate())
    else:
        asyncio.run(migrate())
