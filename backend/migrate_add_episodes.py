"""
Migration: Thêm bảng episodes và cập nhật FK của scripts/images

Chạy: python migrate_add_episodes.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows asyncio fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL, echo=True)


async def migrate():
    async with engine.begin() as conn:

        # 1. Tạo bảng episodes (nếu chưa có)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS episodes (
                id          VARCHAR PRIMARY KEY,
                project_id  VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                ep_no       INTEGER NOT NULL,
                title       VARCHAR NOT NULL,
                description TEXT,
                created_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_episodes_project_id ON episodes(project_id)"
        ))
        print("✓ Bảng episodes đã tạo")

        # 2. Thêm cột episode_id vào scripts (nếu chưa có)
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='scripts' AND column_name='episode_id'
        """))
        if not result.fetchone():
            await conn.execute(text(
                "ALTER TABLE scripts ADD COLUMN episode_id VARCHAR REFERENCES episodes(id) ON DELETE CASCADE"
            ))
            print("✓ Cột episode_id thêm vào scripts")
        else:
            print("→ scripts.episode_id đã tồn tại, bỏ qua")

        # 3. Thêm cột episode_id vào images (nếu chưa có)
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='images' AND column_name='episode_id'
        """))
        if not result.fetchone():
            await conn.execute(text(
                "ALTER TABLE images ADD COLUMN episode_id VARCHAR REFERENCES episodes(id) ON DELETE SET NULL"
            ))
            print("✓ Cột episode_id thêm vào images")
        else:
            print("→ images.episode_id đã tồn tại, bỏ qua")

        # 4. Migration scripts cũ: tạo Episode "Tập 1" cho mỗi script chưa có episode
        result = await conn.execute(text(
            "SELECT id, project_id FROM scripts WHERE episode_id IS NULL"
        ))
        orphan_scripts = result.fetchall()

        if orphan_scripts:
            import uuid
            from datetime import datetime
            # Group by project_id
            by_project: dict = {}
            for row in orphan_scripts:
                by_project.setdefault(row[1], []).append(row[0])

            for project_id, script_ids in by_project.items():
                # Tạo Episode "Tập 1" cho project này
                ep_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()
                await conn.execute(text("""
                    INSERT INTO episodes (id, project_id, ep_no, title, created_at)
                    VALUES (:id, :project_id, 1, 'Tập 1', :now)
                    ON CONFLICT DO NOTHING
                """), {"id": ep_id, "project_id": project_id, "now": now})

                # Gán scripts vào episode này
                for script_id in script_ids:
                    await conn.execute(text(
                        "UPDATE scripts SET episode_id = :ep_id WHERE id = :script_id"
                    ), {"ep_id": ep_id, "script_id": script_id})

            print(f"✓ Đã migrate {len(orphan_scripts)} script cũ → Episode 'Tập 1'")
        else:
            print("→ Không có script cũ cần migrate")

    print("\n✅ Migration hoàn tất!")


if __name__ == "__main__":
    asyncio.run(migrate())
