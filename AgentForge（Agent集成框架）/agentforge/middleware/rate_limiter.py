"""Middleware 4: Redis-backed rate limiter"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import structlog
from agentforge.core.database import get_redis

logger = structlog.get_logger()

class RateLimiter(BaseMiddleware):
    def __init__(self, max_per_second: int = 10):
        self.max_per_second = max_per_second

    async def before(self, ctx: PipelineContext) -> PipelineContext:
        model = ctx.config.model
        try:
            redis = await get_redis()
            key = f"rate_limit:{model}"
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, 1)  # 1 second window
            if current > self.max_per_second:
                logger.warning("Rate limit exceeded", model=model, current=current)
                ctx.should_short_circuit = True
                from agentforge.agents.base import AgentResponse
                ctx.error_response = AgentResponse(
                    status="error",
                    error_message=f"Rate limit: {self.max_per_second}/s for {model}"
                )
        except Exception as e:
            logger.warning("Redis unavailable, skipping rate limit", error=str(e))
        return ctx
