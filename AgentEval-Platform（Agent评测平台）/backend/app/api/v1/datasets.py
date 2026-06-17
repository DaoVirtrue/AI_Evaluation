"""Dataset management API — files persist to /app/datasets/"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.models import Dataset
from app.core.database import get_db, AsyncSessionLocal
import json, uuid, os, logging

logger = logging.getLogger("agent-eval.datasets")
router = APIRouter()
DATA_DIR = "/app/datasets"

@router.on_event("startup")
async def auto_import_samples():
    """Auto-import sample_qa.jsonl if not already in DB"""
    os.makedirs(DATA_DIR, exist_ok=True)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Dataset).where(Dataset.name == "sample_qa.jsonl"))
        if result.scalar_one_or_none():
            return  # Already imported
        sample_path = os.path.join(DATA_DIR, "sample_qa.jsonl")
        if os.path.exists(sample_path):
            with open(sample_path, encoding="utf-8") as f:
                cases = [json.loads(line) for line in f if line.strip()]
            ds = Dataset(id=str(uuid.uuid4()), name="sample_qa.jsonl", format="jsonl",
                         case_count=len(cases), preview_data=cases[:5], file_path=sample_path)
            db.add(ds)
            await db.commit()
            logger.info(f"Auto-imported sample_qa.jsonl: {len(cases)} cases")

@router.post("/datasets", status_code=201)
async def upload_dataset(name: str = Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    cases = [json.loads(line) for line in text.strip().split("\n") if line.strip()]
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, f"{name}.jsonl")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    did = str(uuid.uuid4())
    ds = Dataset(id=did, name=name, format="jsonl", case_count=len(cases), preview_data=cases[:5], file_path=file_path)
    db.add(ds); await db.commit()
    logger.info(f"Dataset uploaded: {name} ({len(cases)} cases) → {file_path}")
    return {"id": did, "name": name, "case_count": len(cases), "format": "jsonl", "file_path": file_path}

@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return [{"id": d.id, "name": d.name, "format": d.format, "case_count": d.case_count, "file_path": d.file_path, "created_at": d.created_at.isoformat() if d.created_at else None} for d in result.scalars().all()]

@router.get("/datasets/{did}/preview")
async def preview_dataset(did: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == did))
    ds = result.scalar_one_or_none()
    if not ds: raise HTTPException(status_code=404, detail={"code": 404, "msg": "Not found"})
    # Try reading full file if it exists on disk
    cases = ds.preview_data or []
    if ds.file_path and os.path.exists(ds.file_path):
        with open(ds.file_path, encoding="utf-8") as f:
            cases = [json.loads(line) for line in f if line.strip()]
    return {"id": ds.id, "name": ds.name, "case_count": ds.case_count, "preview": cases[:5], "full_count": len(cases)}

@router.delete("/datasets/{did}")
async def delete_dataset(did: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == did))
    ds = result.scalar_one_or_none()
    if ds and ds.file_path and os.path.exists(ds.file_path):
        os.remove(ds.file_path)
    await db.execute(delete(Dataset).where(Dataset.id == did))
    await db.commit()
    return {"id": did, "deleted": True}
