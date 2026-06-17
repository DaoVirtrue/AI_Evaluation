"""SQLAlchemy models for AgentForge persistence"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, Text
from agentforge.core.database import Base
import uuid

def gen_id():
    return str(uuid.uuid4())

class AgentConfigModel(Base):
    __tablename__ = "agent_configs"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False, unique=True)
    framework = Column(String(32), default="native")
    model = Column(String(64), default="claude-sonnet-4-6")
    system_prompt = Column(Text, default="You are a helpful assistant.")
    middleware_pipeline = Column(JSON, default=list)
    tool_registry = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(String, primary_key=True, default=gen_id)
    config_id = Column(String, nullable=True)
    status = Column(String(32), default="active")
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
