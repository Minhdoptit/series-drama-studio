"""
Migration: Thêm cột image_ids và extra_prompt vào bảng scenes (nếu chưa có)

Chạy 1 lần từ thư mục backend/:
    python migrate_scene_image_ids.py

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


async def add_column_if_not_exists(conn, table: str, column: str, col_type: str):
    result = await conn.execute(text(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_name='{table}' AND column_name='{column}'"
    ))
    if result.fetchone():
        print(f"[SKIP] Column '{column}' already exists in '{table}'")
        return False
    print(f"[ADD ] Adding column '{column}' ({col_type}) to '{table}'...")
    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
    print(f"[OK  ] Column '{column}' added.")
    return True


async def migrate():
    async with engine.begin() as conn:
        changed = False

        # 1. image_ids: JSON array of image IDs e.g. '["id1","id2"]'
        r1 = await add_column_if_not_exists(conn, "scenes", "image_ids", "VARCHAR")
        changed = changed or r1

        # 2. extra_prompt: optional user prompt appended to video prompt
        r2 = await add_column_if_not_exists(conn, "scenes", "extra_prompt", "VARCHAR")
        changed = changed or r2

        if changed:
            print("[DONE] Migration complete.")
        else:
            print("[DONE] Nothing to migrate — all columns already exist.")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop.run_until_complete(migrate())
    else:
        asyncio.run(migrate())
