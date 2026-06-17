"""Middleware 1: Context Window check using token-core"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import structlog

logger = structlog.get_logger()

class ContextWindowCheck(BaseMiddleware):
    async def before(self, ctx: PipelineContext) -> PipelineContext:
        model = ctx.config.model
        # In production: call token-core PyO3 for exact count
        estimated_tokens = sum(len(m.content) // 3 for m in ctx.messages)
        ctx.metadata["estimated_tokens"] = estimated_tokens
        logger.info("ContextWindowCheck", model=model, estimated_tokens=estimated_tokens)
        return ctx
