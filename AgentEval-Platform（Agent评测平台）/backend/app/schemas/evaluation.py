"""Pydantic schemas for evaluation API"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional
from datetime import datetime

class CreateEvaluationRequest(BaseModel):
    project_id: str = Field(default="default")
    name: str = Field(..., min_length=1, max_length=255)
    agent_config: dict = Field(default={})
    dataset_id: Optional[str] = None
    model: str = Field(default="claude-sonnet-4-6")
    max_cases: int = Field(default=100, ge=1, le=10000)

class EvaluationResponse(BaseModel):
    id: str
    name: str
    status: str
    total_cases: int = 0
    completed_cases: int = 0
    created_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, v: datetime | None) -> str | None:
        return v.isoformat() if v else None

    model_config = {"from_attributes": True}

class EvaluationListResponse(BaseModel):
    items: list[EvaluationResponse]
    total: int
    page: int
    page_size: int
