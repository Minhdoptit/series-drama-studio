"""Seed 1 user vào DB để test"""
import asyncio, selectors, os, uuid
from dotenv import load_dotenv
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import bcrypt

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:changeme@localhost:5432/drama_studio")
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    from app.models import User, Project, Script, Scene, Image, Video, Document, ApiKey

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "test@drama.com"))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[OK] User da ton tai: {existing.email} (id={existing.id})")
            return

        hashed = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
        user = User(
            id=str(uuid.uuid4()),
            email="test@drama.com",
            hashed_password=hashed,
            full_name="Test User",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print("[OK] Da tao user:")
        print("   Email   : test@drama.com")
        print("   Password: 123456")
        print(f"  ID      : {user.id}")


asyncio.run(seed(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
