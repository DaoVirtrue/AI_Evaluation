"""Middleware 5: Smart model routing based on cost/latency/capability"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import structlog

logger = structlog.get_logger()

MODEL_TIERS = {
    "simple": ["claude-haiku-4-5", "gpt-4.1-nano", "gemini-3.1-flash-lite", "deepseek-v4-flash"],
    "moderate": ["claude-sonnet-4-6", "gpt-4.1", "deepseek-v4-pro"],
    "complex": ["claude-opus-4-8", "gpt-5.5", "deepseek-v4-pro"],
    "extreme": ["claude-fable-5", "gpt-5.5"],
}

MODEL_COSTS = {
    "claude-fable-5": 30.0, "claude-opus-4-8": 15.0, "claude-sonnet-4-6": 9.0,
    "claude-haiku-4-5": 3.0, "gpt-5.5": 17.5, "gpt-4.1": 5.0,
    "gpt-4.1-nano": 0.25, "deepseek-v4-pro": 0.65, "deepseek-v4-flash": 0.21,
    "gemini-3.1-flash-lite": 0.875,
}

class ModelRouter(BaseMiddleware):
    async def before(self, ctx: PipelineContext) -> PipelineContext:
        strategy = ctx.config.routing_strategy
        model = ctx.config.model

        # Simple routing: use configured model, fallback if needed
        ctx.selected_model = model
        ctx.metadata["routing_strategy"] = strategy
        ctx.metadata["selected_model"] = model

        logger.info("ModelRouter", model=model, strategy=strategy)
        return ctx

    @staticmethod
    def get_fallback(model: str) -> str:
        """Get a fallback model if the primary fails"""
        fallbacks = {
            "claude-opus-4-8": "claude-sonnet-4-6",
            "claude-sonnet-4-6": "claude-haiku-4-5",
            "gpt-5.5": "gpt-5.4",
            "deepseek-v4-pro": "deepseek-v4-flash",
        }
        return fallbacks.get(model, "claude-haiku-4-5")
