"""Middleware 6: Trajectory tracer — records every step"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import structlog

logger = structlog.get_logger()

class Tracer(BaseMiddleware):
    async def after(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.response:
            ctx.response.metadata["trace"] = {
                "steps": len(ctx.response.steps),
                "model": ctx.metadata.get("selected_model"),
                "tokens": ctx.response.total_tokens,
            }
        return ctx
