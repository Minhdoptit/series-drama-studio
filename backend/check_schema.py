import os, psycopg
from dotenv import load_dotenv
load_dotenv()

db_url = (os.getenv("DATABASE_URL", "")
    .replace("postgresql+psycopg://", "postgresql://")
    .replace("postgresql+asyncpg://", "postgresql://"))

with psycopg.connect(db_url) as conn:
    tables = ["users","projects","episodes","scripts","scenes","images","videos","api_keys","documents"]
    for t in tables:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position",
            (t,)
        ).fetchall()
        cols = [r[0] for r in rows]
        print(f"{t}: {cols}")
