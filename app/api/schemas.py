from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.models import JobStatus, FileStatus


class FileStatusResponse(BaseModel):
    filename: str
    status: FileStatus
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobCreateResponse(BaseModel):
    job_id: UUID
    file_count: int
    
    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime
    download_url: Optional[str] = None
    files: List[FileStatusResponse]
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    

class JobNotFoundResponse(BaseModel):
    error: str = "Job not found"
    detail: str = "The specified job ID does not exist"


class ValidationErrorResponse(BaseModel):
    error: str
    detail: str
