"""Middleware pipeline - onion model execution"""
from dataclasses import dataclass, field
from typing import Callable, Optional
from agentforge.agents.base import AgentConfig, AgentResponse
import structlog
import time

logger = structlog.get_logger()

@dataclass
class PipelineContext:
    config: AgentConfig
    messages: list = field(default_factory=list)
    selected_model: Optional[str] = None
    should_short_circuit: bool = False
    error_response: Optional[AgentResponse] = None
    response: Optional[AgentResponse] = None
    metadata: dict = field(default_factory=dict)

class BaseMiddleware:
    async def before(self, ctx: PipelineContext) -> PipelineContext:
        return ctx
    async def after(self, ctx: PipelineContext) -> PipelineContext:
        return ctx

class MiddlewarePipeline:
    def __init__(self, middlewares: list[BaseMiddleware] | None = None):
        self.middlewares = middlewares or []

    def add(self, mw: BaseMiddleware):
        self.middlewares.append(mw)

    async def process(self, config: AgentConfig, messages: list, handler: Callable) -> AgentResponse:
        ctx = PipelineContext(config=config, messages=messages)
        t0 = time.time()

        # Forward pass (1 → N)
        for mw in self.middlewares:
            ctx = await mw.before(ctx)
            if ctx.should_short_circuit:
                logger.warning("Pipeline short-circuited", middleware=mw.__class__.__name__)
                return ctx.error_response or AgentResponse(status="error", error_message="Pipeline short-circuited")

        # Core execution
        ctx.response = await handler(ctx)

        # Backward pass (N → 1)
        for mw in reversed(self.middlewares):
            ctx = await mw.after(ctx)

        if ctx.response:
            ctx.response.total_latency_ms = int((time.time() - t0) * 1000)

        return ctx.response or AgentResponse(status="error", error_message="No response produced")
