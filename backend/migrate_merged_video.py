"""
migrate_merged_video.py
Them 3 cot merged_video_* vao bang episodes (PostgreSQL)
Chay: python migrate_merged_video.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

import psycopg

def main():
    db_url = os.getenv("DATABASE_URL", "")
    # psycopg sync dung postgresql+psycopg:// -> postgresql://
    db_url = (db_url
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )

    print(f"Connecting to: {db_url[:50]}...")

    with psycopg.connect(db_url, autocommit=True) as conn:
        migrations = [
            "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS merged_video_path TEXT",
            "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS merged_video_status TEXT",
            "ALTER TABLE episodes ADD COLUMN IF NOT EXISTS merged_video_error TEXT",
        ]
        for sql in migrations:
            try:
                conn.execute(sql)
                print(f"  OK: {sql}")
            except Exception as e:
                print(f"  SKIP ({e}): {sql}")

    print("\nDone! Restart backend de ap dung thay doi.")

if __name__ == "__main__":
    main()
