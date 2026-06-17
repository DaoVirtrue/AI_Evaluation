"""SQLAlchemy models for AgentEval Platform"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, JSON, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid, os

Base = declarative_base()
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./eval.db")

def gen_id():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False)
    owner_id = Column(String, default="admin")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"))
    name = Column(String(255), nullable=False)
    agent_config = Column(JSON, default=dict)
    status = Column(String(32), default="queued")
    metrics = Column(JSON, default=dict)
    total_cases = Column(Integer, default=0)
    completed_cases = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id = Column(String, primary_key=True, default=gen_id)
    evaluation_id = Column(String, ForeignKey("evaluations.id", ondelete="CASCADE"))
    case_id = Column(String, nullable=False)
    input = Column(Text)
    expected_output = Column(Text)
    actual_output = Column(Text)
    passed = Column(Boolean)
    score = Column(Float)
    trajectory = Column(JSON)
    token_usage = Column(JSON)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, default="default")
    name = Column(String(255), nullable=False)
    format = Column(String(16), default="jsonl")
    case_count = Column(Integer, default=0)
    file_path = Column(String(512))
    preview_data = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
