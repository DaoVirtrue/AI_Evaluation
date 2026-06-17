"""Project management endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Project
from app.core.database import get_db
import uuid

router = APIRouter()

@router.post("/projects", status_code=201)
async def create_project(name: str = "default", db: AsyncSession = Depends(get_db)):
    pid = str(uuid.uuid4())
    project = Project(id=pid, name=name, owner_id="admin")
    db.add(project)
    await db.commit()
    return {"id": pid, "name": name}

@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    return [{"id": p.id, "name": p.name} for p in result.scalars().all()]
