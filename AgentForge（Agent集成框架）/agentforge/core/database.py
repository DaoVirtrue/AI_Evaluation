"""PostgreSQL + Redis connections for AgentForge"""
import os
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as aioredis

logger = structlog.get_logger()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://agent:devpass@postgres:5432/agent_eval"
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Redis connection pool
redis_pool = None

async def get_redis():
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True, max_connections=20)
    return redis_pool
