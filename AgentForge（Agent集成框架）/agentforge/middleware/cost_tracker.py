"""Middleware 7: Cost tracker — accumulates cost per session"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import structlog

logger = structlog.get_logger()

class CostTracker(BaseMiddleware):
    async def after(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.response:
            cost = ctx.response.total_tokens * 0.000005  # simplified estimate
            ctx.response.total_cost = round(cost, 6)
            logger.info("CostTracker", session_id=ctx.response.session_id, cost=cost)
        return ctx
