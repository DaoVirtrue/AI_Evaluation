"""Middleware 2: Tool call safety validation"""
from agentforge.middleware.pipeline import BaseMiddleware, PipelineContext
import structlog

logger = structlog.get_logger()

DANGEROUS_PATTERNS = ["rm -rf", "sudo", "DROP TABLE", "DELETE FROM", "__import__", "eval(", "exec(", "subprocess", "os.system"]

class ToolCallSanitizer(BaseMiddleware):
    async def before(self, ctx: PipelineContext) -> PipelineContext:
        for msg in ctx.messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                for pattern in DANGEROUS_PATTERNS:
                    if pattern.lower() in msg.content.lower():
                        logger.warning("Dangerous pattern blocked", pattern=pattern)
                        ctx.should_short_circuit = True
                        from agentforge.agents.base import AgentResponse
                        ctx.error_response = AgentResponse(status="error", error_message=f"Blocked dangerous pattern: {pattern}")
                        return ctx
        return ctx
