import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="client")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    name = Column(String, nullable=False, unique=True) # e.g. drew-5trips
    folder_path = Column(String, nullable=False) # e.g. projects/drew-5trips
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    client = relationship("Client", back_populates="projects")
    generation_jobs = relationship("GenerationJob", back_populates="project")
    conversations = relationship("Conversation", back_populates="project")
    cost_entries = relationship("CostEntry", back_populates="project")


class CostEntry(Base):
    __tablename__ = "cost_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    service = Column(String, nullable=False)
    model = Column(String, nullable=False)
    amount_usd = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    job_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="cost_entries")
