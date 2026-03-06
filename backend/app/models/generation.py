import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String, default="pending") # pending, processing, completed, failed
    model_used = Column(String)
    parameters = Column(JSON) # e.g. batch size, concept list
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="generation_jobs")
    assets = relationship("GeneratedAsset", back_populates="job")

class GeneratedAsset(Base):
    __tablename__ = "generated_assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("generation_jobs.id"), nullable=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    asset_type = Column(String, nullable=False) # image, video
    file_path = Column(String, nullable=False) # local storage path
    drive_id = Column(String, nullable=True)
    drive_url = Column(String, nullable=True)
    drive_direct_url = Column(String, nullable=True)
    original_prompt = Column(String)
    
    # Vision QC scores
    qc_composition = Column(JSON, nullable=True) # e.g. score out of 10 and reason
    qc_clarity = Column(JSON, nullable=True)
    qc_prompt_adherence = Column(JSON, nullable=True)
    qc_style_match = Column(JSON, nullable=True)
    qc_overall_score = Column(JSON, nullable=True) # just the numerical score

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    job = relationship("GenerationJob", back_populates="assets")
    conversation = relationship("Conversation", back_populates="assets")
