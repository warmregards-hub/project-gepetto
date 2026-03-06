import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.database import Base

class LearnedPreference(Base):
    __tablename__ = "learned_preferences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    key = Column(String, nullable=False) # e.g. "qc_threshold", "preferred_model_ugc"
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    template_content = Column(String, nullable=False)
    success_score = Column(Integer, default=0) # Tracks average QC score or user rating
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
