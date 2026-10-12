"""
Migration: Them started_at vao bang videos + reset zombie 'running' tasks

Chay 1 lan tu thu muc backend/:
    python migrate_video_started_at.py

Idempotent: chay nhieu lan khong crash.
"""
import asyncio
import sys
import os
import selectors

if sys.platform == "win32":
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Kiem tra started_at da ton tai chua
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='videos' AND column_name='started_at'"
        ))
        if not result.fetchone():
            print("Running migration: add started_at to videos...")
            await conn.execute(text(
                "ALTER TABLE videos ADD COLUMN started_at TIMESTAMP WITHOUT TIME ZONE"
            ))
            print("[OK] started_at column added")
        else:
            print("[OK] started_at already exists, skipping alter")

        # Reset zombie: video bi ket 'running' vi backend restart
        r = await conn.execute(text(
            "UPDATE videos SET status='error', error_msg='Task bi huy do backend restart' "
            "WHERE status='running'"
        ))
        print(f"[OK] Reset {r.rowcount} zombie 'running' video(s) -> error")

        print("[DONE] Migration complete")


if __name__ == "__main__":
    if sys.platform == "win32":
        loop.run_until_complete(migrate())
    else:
        asyncio.run(migrate())
