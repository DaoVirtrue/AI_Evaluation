"""AgentForge HTTP API (FastAPI)"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from agentforge.agents.registry import get_adapter
from agentforge.agents.base import Message, ToolDefinition, AgentConfig
from agentforge.middleware.pipeline import MiddlewarePipeline
from agentforge.middleware.context_window import ContextWindowCheck
from agentforge.middleware.tool_sanitizer import ToolCallSanitizer
from agentforge.middleware.model_router import ModelRouter
from agentforge.middleware.rate_limiter import RateLimiter
from agentforge.middleware.cost_tracker import CostTracker
from agentforge.middleware.tracer import Tracer
from agentforge.core.database import init_db, get_db
from agentforge.models.models import AgentConfigModel, AgentSession
import structlog
import time
import json

logger = structlog.get_logger()

app = FastAPI(title="AgentForge", version="0.1.0")

@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("AgentForge started, DB initialized")

# Build default pipeline
default_pipeline = MiddlewarePipeline([
    ContextWindowCheck(),
    ToolCallSanitizer(),
    RateLimiter(max_per_second=10),
    ModelRouter(),
    Tracer(),
    CostTracker(),
])

@app.exception_handler(Exception)
async def global_handler(request, exc):
    return JSONResponse(status_code=500, content={"code": 500, "msg": "Internal error", "detail": None})

class RunRequest(BaseModel):
    messages: list[dict] = Field(..., min_length=1)
    framework: str = Field(default="native")
    model: str = Field(default="claude-sonnet-4-6")
    system_prompt: str = Field(default="You are a helpful assistant.")
    max_tokens: int = Field(default=64_000)

@app.post("/api/v1/agents/run")
async def run_agent(req: RunRequest):
    """Run an agent synchronously"""
    try:
        adapter = get_adapter(req.framework)
        messages = [Message(role=m["role"], content=m["content"]) for m in req.messages]
        config = AgentConfig(model=req.model, max_tokens=req.max_tokens, system_prompt=req.system_prompt)

        async def handler(ctx):
            return await adapter.run(messages, config=config)

        response = await default_pipeline.process(config, messages, handler)

        # Persist session to PostgreSQL
        try:
            db = await anext(get_db())
            session = AgentSession(
                id=response.session_id,
                status=response.status,
                total_tokens=response.total_tokens,
                total_cost=response.total_cost,
                total_latency_ms=response.total_latency_ms,
            )
            db.add(session)
            await db.commit()
        except Exception:
            pass  # Non-critical: session logging failure shouldn't block response

        logger.info("Agent run complete", framework=req.framework, status=response.status)

        return {
            "session_id": response.session_id,
            "status": response.status,
            "output": response.output,
            "steps": len(response.steps),
            "total_tokens": response.total_tokens,
            "total_cost": response.total_cost,
            "total_latency_ms": response.total_latency_ms,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "msg": str(e)})

# --- Config CRUD ---
class CreateConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    framework: str = Field(default="native")
    model: str = Field(default="claude-sonnet-4-6")
    system_prompt: str = Field(default="You are a helpful assistant.")

@app.post("/api/v1/configs", status_code=201)
async def create_config(req: CreateConfigRequest, db: AsyncSession = Depends(get_db)):
    config = AgentConfigModel(
        name=req.name, framework=req.framework,
        model=req.model, system_prompt=req.system_prompt,
    )
    db.add(config)
    await db.commit()
    return {"id": config.id, "name": config.name}

@app.get("/api/v1/configs")
async def list_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentConfigModel).order_by(AgentConfigModel.created_at.desc()))
    configs = result.scalars().all()
    return [{"id": c.id, "name": c.name, "framework": c.framework, "model": c.model} for c in configs]

@app.get("/api/v1/sessions")
async def list_sessions(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentSession).order_by(AgentSession.created_at.desc()).limit(limit))
    sessions = result.scalars().all()
    return [{"id": s.id, "status": s.status, "total_tokens": s.total_tokens, "total_cost": s.total_cost} for s in sessions]

@app.get("/health")
async def health():
    return {"status": "ok", "frameworks": ["langchain", "openai_agents", "native"], "db": "postgresql", "cache": "redis"}

@app.get("/api/v1/health")
async def health_v1():
    return await health()
