from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import logging

from app.config.database import get_db
from app.config.settings import settings
from app.models.models import ConversionJob, ConversionFile, JobStatus, FileStatus
from app.api.schemas import (
    JobCreateResponse, 
    JobStatusResponse, 
    FileStatusResponse,
    ErrorResponse,
    JobNotFoundResponse
)
from app.utils.file_utils import (
    ensure_directories,
    extract_zip_file,
    validate_file_size,
    is_valid_docx_file,
    create_job_directory,
    safe_filename
)
from app.workers.tasks import process_conversion_job

logger = logging.getLogger(__name__)
router = APIRouter()




@router.post(
    "/jobs",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
    }
)
async def submit_conversion_job(
    file: UploadFile = File(..., description="ZIP file containing DOCX files to convert"),
    db: Session = Depends(get_db)
):
    """
    Submit a new conversion job with a ZIP file containing DOCX files.
    
    The service will:
    1. Validate the uploaded ZIP file
    2. Extract and validate DOCX files
    3. Create a new job in the database
    4. Queue the job for processing
    5. Return a job ID for tracking progress
    """
    
    # Validate file type
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are accepted"
        )
    
    # Validate file size
    if file.size and not validate_file_size(file.size):
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
        )
    
    try:
        # Generate job ID
        job_id = uuid.uuid4()
        
        # Create directories for this job
        input_dir, output_dir = create_job_directory(str(job_id))
        
        # Save uploaded ZIP file
        zip_filename = safe_filename(file.filename)
        zip_path = os.path.join(settings.full_upload_path, f"{job_id}_{zip_filename}")
        
        # Save uploaded file
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Saved uploaded ZIP file to: {zip_path}")
        
        # Extract ZIP file and validate contents
        try:
            extracted_files = extract_zip_file(zip_path, input_dir)
        except ValueError as e:
            # Clean up uploaded file
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise HTTPException(status_code=400, detail=str(e))
        
        if not extracted_files:
            # Clean up
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise HTTPException(
                status_code=400,
                detail="No valid DOCX files found in ZIP archive"
            )
        
        # Create job record in database
        db_job = ConversionJob(
            id=job_id,
            status=JobStatus.PENDING,
            file_count=len(extracted_files),
            upload_zip_path=zip_path
        )
        db.add(db_job)
        db.flush()  # Get the ID before committing
        
        # Create file records
        for filename, file_path in extracted_files:
            # Validate each DOCX file
            if not is_valid_docx_file(file_path):
                logger.warning(f"Invalid DOCX file: {filename}")
                continue
                
            db_file = ConversionFile(
                job_id=job_id,
                filename=filename,
                original_path=file_path,
                status=FileStatus.PENDING,
                file_size=os.path.getsize(file_path)
            )
            db.add(db_file)
        
        db.commit()
        logger.info(f"Created job {job_id} with {len(extracted_files)} files")
        
        # Queue job for processing
        process_conversion_job.delay(str(job_id))
        logger.info(f"Queued job {job_id} for processing")
        
        return JobCreateResponse(
            job_id=job_id,
            file_count=len(extracted_files)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred while processing the request"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: {"model": JobNotFoundResponse},
    }
)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of a conversion job.
    
    Returns detailed information about the job including:
    - Overall job status
    - Status of each individual file
    - Download URL when job is completed
    """
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid job ID format")
    
    # Get job from database
    job = db.query(ConversionJob).filter(ConversionJob.id == job_uuid).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get file statuses
    file_responses = []
    for file_record in job.files:
        file_responses.append(FileStatusResponse(
            filename=file_record.filename,
            status=file_record.status,
            error_message=file_record.error_message
        ))
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        download_url=job.download_url,
        files=file_responses
    )


@router.get(
    "/jobs/{job_id}/download",
    response_class=FileResponse,
    responses={
        404: {"model": JobNotFoundResponse},
        400: {"model": ErrorResponse},
    }
)
async def download_converted_files(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Download the converted PDF files as a ZIP archive.
    
    This endpoint is only available when the job status is COMPLETED.
    """
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid job ID format")
    
    # Get job from database
    job = db.query(ConversionJob).filter(ConversionJob.id == job_uuid).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Job is not completed. Current status: {job.status.value}"
        )
    
    if not job.output_zip_path or not os.path.exists(job.output_zip_path):
        raise HTTPException(
            status_code=404,
            detail="Converted files not found"
        )
    
    # Return file response
    filename = f"converted_files_{job_id}.zip"
    
    return FileResponse(
        path=job.output_zip_path,
        media_type="application/zip",
        filename=filename
    )


