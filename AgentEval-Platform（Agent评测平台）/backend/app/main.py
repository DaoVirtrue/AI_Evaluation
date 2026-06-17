"""AgentEval Platform - FastAPI Backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import traceback

logger = structlog.get_logger()

app = FastAPI(title="AgentEval-Platform", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_handler(request, exc):
    logger.error(f"Unhandled: {traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"code": 500, "msg": "Internal server error", "detail": None})

# Import route modules
from app.api.v1 import evaluations, projects, datasets

app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    from app.worker.eval_runner import start_worker
    start_worker()
    logger.info("Evaluation Worker started")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-eval-platform", "worker": "active"}
