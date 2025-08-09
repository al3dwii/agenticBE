from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from contextlib import asynccontextmanager
from app.core.config import settings
from app.models.base import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

@asynccontextmanager
async def tenant_session(tenant_id: str):
    async with SessionLocal() as session:
        # Use set_config so we can bind parameters; third arg TRUE == LOCAL to current xact.
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        yield session

async def init_models():
    # Alembic is authoritative; no-op here. Kept for convenience in tests.
    pass


# from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
# from sqlalchemy.orm import DeclarativeBase
# from sqlalchemy import text
# from contextlib import asynccontextmanager
# from app.core.config import settings
# from app.models.base import Base

# engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
# SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# async def get_session() -> AsyncSession:
#     async with SessionLocal() as session:
#         yield session

# @asynccontextmanager
# async def tenant_session(tenant_id: str):
#     async with SessionLocal() as session:
#         # Set a custom GUC used by RLS policies
#         await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
#         yield session

# async def init_models():
#     # Alembic is authoritative; no-op here. Kept for convenience in tests.
#     pass
