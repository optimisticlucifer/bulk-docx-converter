from sqlalchemy import Column, String, DateTime, Enum, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.config.database import Base
import uuid
import enum
from datetime import datetime


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    file_count = Column(Integer, nullable=False, default=0)
    upload_zip_path = Column(String, nullable=True)  # Path to uploaded zip file
    output_zip_path = Column(String, nullable=True)  # Path to final zip archive
    error_message = Column(Text, nullable=True)
    
    # Relationship to files
    files = relationship("ConversionFile", back_populates="job", cascade="all, delete-orphan")

    @property
    def download_url(self):
        if self.status == JobStatus.COMPLETED and self.output_zip_path:
            return f"/api/v1/jobs/{self.id}/download"
        return None


class ConversionFile(Base):
    __tablename__ = "conversion_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("conversion_jobs.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)  # Path to original DOCX file
    converted_path = Column(String, nullable=True)  # Path to converted PDF file
    status = Column(Enum(FileStatus), default=FileStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    
    # Relationship to job
    job = relationship("ConversionJob", back_populates="files")
