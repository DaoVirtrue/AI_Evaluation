"""Middleware 3: Redis-backed semantic cache"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import hashlib
import structlog
from agentforge.core.database import get_redis

logger = structlog.get_logger()

class SemanticCache(BaseMiddleware):
    def __init__(self, ttl: int = 300):
        self.ttl = ttl

    def _key(self, messages: list) -> str:
        content = "".join(m.content[-200:] if hasattr(m, "content") else str(m)[-200:] for m in messages[-4:])
        return f"cache:{hashlib.sha256(content.encode()).hexdigest()[:16]}"

    async def before(self, ctx: PipelineContext) -> PipelineContext:
        try:
            redis = await get_redis()
            key = self._key(ctx.messages)
            cached = await redis.get(key)
            if cached:
                logger.info("SemanticCache hit", key=key)
                ctx.metadata["cache_hit"] = True
            else:
                ctx.metadata["cache_key"] = key
                ctx.metadata["cache_hit"] = False
        except Exception as e:
            logger.warning("Redis unavailable, skipping cache", error=str(e))
        return ctx

    async def after(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.response and ctx.metadata.get("cache_key") and not ctx.metadata.get("cache_hit"):
            try:
                redis = await get_redis()
                await redis.setex(
                    ctx.metadata["cache_key"],
                    self.ttl,
                    ctx.response.output[:10000]
                )
            except Exception:
                pass
        return ctx
