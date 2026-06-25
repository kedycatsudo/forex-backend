from collections.abc import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DB_URL=os.getenv("DATABASE_URL","postgresql+psycopg://postgres:postgres@localhost:5432/forex_db")

engine = create_async_engine(DB_URL,future=True,pool_pre_ping=True)
SessionLocal=async_sessionmaker(bind=engine,class_=AsyncSession,expire_on_commit=False)

async def get_db()->AsyncGenerator[AsyncSession,None]:
    async with SessionLocal() as session:
        yield session