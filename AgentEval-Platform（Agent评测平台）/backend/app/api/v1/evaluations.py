"""Evaluation API endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.schemas.evaluation import CreateEvaluationRequest, EvaluationResponse, EvaluationListResponse
from app.models.models import Evaluation, EvaluationResult, Project
from app.core.database import get_db, init_db
import structlog
import uuid
from datetime import datetime

logger = structlog.get_logger()
router = APIRouter()

@router.on_event("startup")
async def startup():
    await init_db()
    # Ensure default project exists
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Project).where(Project.id == "default"))
        if not result.scalar_one_or_none():
            db.add(Project(id="default", name="Default Project", owner_id="admin"))
            await db.commit()

@router.post("/evaluations", response_model=EvaluationResponse, status_code=201)
async def create_evaluation(req: CreateEvaluationRequest, db: AsyncSession = Depends(get_db)):
    eval_id = str(uuid.uuid4())
    evaluation = Evaluation(
        id=eval_id, project_id=req.project_id, name=req.name,
        agent_config=req.agent_config, status="queued", total_cases=req.max_cases,
        created_at=datetime.utcnow(),
    )
    db.add(evaluation)
    await db.commit()
    # Simulate async execution start
    logger.info("Evaluation created", id=eval_id, name=req.name)
    evaluation.status = "running"
    evaluation.started_at = datetime.utcnow()
    await db.commit()
    return evaluation

@router.get("/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(project_id: str = "default", page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Evaluation).where(Evaluation.project_id == project_id).order_by(Evaluation.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    )
    items = result.scalars().all()
    total = (await db.execute(select(func.count(Evaluation.id)).where(Evaluation.project_id == project_id))).scalar()
    return EvaluationListResponse(items=[EvaluationResponse.model_validate(i) for i in items], total=total, page=page, page_size=page_size)

@router.get("/evaluations/{eid}", response_model=EvaluationResponse)
async def get_evaluation(eid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Evaluation).where(Evaluation.id == eid))
    ev = result.scalar_one_or_none()
    if not ev: raise HTTPException(status_code=404, detail={"code": 404, "msg": "Evaluation not found"})
    return ev

@router.get("/evaluations/{eid}/status")
async def get_status(eid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Evaluation).where(Evaluation.id == eid))
    ev = result.scalar_one_or_none()
    if not ev: raise HTTPException(status_code=404, detail={"code": 404, "msg": "Not found"})
    return {"id": ev.id, "status": ev.status, "completed": ev.completed_cases, "total": ev.total_cases}

@router.delete("/evaluations/{eid}")
async def cancel_evaluation(eid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Evaluation).where(Evaluation.id == eid))
    ev = result.scalar_one_or_none()
    if not ev: raise HTTPException(status_code=404, detail={"code": 404, "msg": "Not found"})
    ev.status = "cancelled"
    await db.commit()
    return {"id": eid, "status": "cancelled"}

@router.get("/evaluations/{eid}/metrics")
async def get_metrics(eid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Evaluation).where(Evaluation.id == eid))
    ev = result.scalar_one_or_none()
    if not ev: raise HTTPException(status_code=404, detail={"code": 404, "msg": "Not found"})
    return {"id": eid, "status": ev.status, "metrics": ev.metrics, "completed": ev.completed_cases, "total": ev.total_cases}

@router.get("/evaluations/{eid}/results")
async def get_results(eid: str, filter: str = "all", page: int = 1, page_size: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(EvaluationResult).where(EvaluationResult.evaluation_id == eid)
    if filter == "passed": q = q.where(EvaluationResult.passed == True)
    elif filter == "failed": q = q.where(EvaluationResult.passed == False)
    q = q.order_by(EvaluationResult.case_id).offset((page-1)*page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()
    total_result = await db.execute(select(func.count(EvaluationResult.id)).where(EvaluationResult.evaluation_id == eid))
    return {"items": [{"id": r.id, "case_id": r.case_id, "input": r.input, "expected_output": r.expected_output, "actual_output": r.actual_output, "passed": r.passed, "score": r.score, "token_usage": r.token_usage, "latency_ms": r.latency_ms} for r in items], "total": total_result.scalar(), "page": page, "page_size": page_size}

@router.get("/evaluations/{eid}/stats")
async def get_stats(eid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EvaluationResult).where(EvaluationResult.evaluation_id == eid))
    items = result.scalars().all()
    total = len(items)
    passed = sum(1 for r in items if r.passed)
    failed = total - passed
    total_tokens = sum((r.token_usage or {}).get("prompt_tokens", 0) + (r.token_usage or {}).get("completion_tokens", 0) for r in items)
    total_cost = sum((r.token_usage or {}).get("total_cost", 0) for r in items)
    avg_latency = sum(r.latency_ms or 0 for r in items) / total if total > 0 else 0
    return {"total": total, "passed": passed, "failed": failed, "pass_rate": round(passed/total*100, 1) if total > 0 else 0, "total_tokens": total_tokens, "total_cost": round(total_cost, 6), "avg_latency_ms": round(avg_latency, 1)}
