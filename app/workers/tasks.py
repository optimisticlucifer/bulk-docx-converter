from celery import current_task
from sqlalchemy.orm import Session
import os
import uuid
import logging
from datetime import datetime
from typing import List, Tuple

from app.workers.celery_app import celery_app
from app.config.database import SessionLocal
from app.models.models import ConversionJob, ConversionFile, JobStatus, FileStatus
from app.utils.converter import converter
from app.utils.file_utils import create_zip_archive, cleanup_directory
from app.config.settings import settings

logger = logging.getLogger(__name__)


def get_db_session():
    """Get database session for tasks"""
    return SessionLocal()


@celery_app.task(bind=True, name='app.workers.tasks.convert_docx_to_pdf')
def convert_docx_to_pdf(self, file_id: str, input_path: str, output_dir: str):
    return _convert_docx_to_pdf_impl(file_id, input_path, output_dir, self)


def _convert_docx_to_pdf_impl(file_id: str, input_path: str, output_dir: str, task_context=None):
    """
    Convert a single DOCX file to PDF
    
    Args:
        file_id: UUID of the file record in database
        input_path: Path to the DOCX file
        output_dir: Directory to save the PDF
    """
    db = get_db_session()
    
    try:
        # Update task progress if task context is available
        if task_context:
            task_context.update_state(state='PROGRESS', meta={'status': 'Converting file'})
        
        # Get file record
        file_record = db.query(ConversionFile).filter(
            ConversionFile.id == uuid.UUID(file_id)
        ).first()
        
        if not file_record:
            logger.error(f"File record not found: {file_id}")
            return {'status': 'ERROR', 'message': 'File record not found'}
        
        # Update file status to IN_PROGRESS
        file_record.status = FileStatus.IN_PROGRESS
        db.commit()
        
        logger.info(f"Starting conversion of {file_record.filename}")
        
        # Convert file
        pdf_path = converter.convert_file(input_path, output_dir)
        
        if pdf_path and converter.validate_conversion(pdf_path):
            # Successful conversion
            file_record.status = FileStatus.COMPLETED
            file_record.converted_path = pdf_path
            file_record.completed_at = datetime.utcnow()
            file_record.error_message = None
            
            logger.info(f"Successfully converted {file_record.filename}")
            
            result = {
                'status': 'SUCCESS',
                'file_id': file_id,
                'pdf_path': pdf_path,
                'original_filename': file_record.filename
            }
        else:
            # Conversion failed
            file_record.status = FileStatus.FAILED
            file_record.error_message = "Conversion failed or produced invalid PDF"
            
            logger.error(f"Failed to convert {file_record.filename}")
            
            result = {
                'status': 'FAILED',
                'file_id': file_id,
                'error': 'Conversion failed'
            }
        
        db.commit()
        return result
        
    except Exception as e:
        logger.error(f"Error in convert_docx_to_pdf task: {str(e)}")
        
        # Update file status to failed
        try:
            if 'file_record' in locals():
                file_record.status = FileStatus.FAILED
                file_record.error_message = str(e)
                db.commit()
        except:
            pass
        
        return {'status': 'ERROR', 'message': str(e)}
    
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.tasks.process_conversion_job')
def process_conversion_job(self, job_id: str):
    """
    Process all files in a conversion job
    
    Args:
        job_id: UUID of the job to process
    """
    db = get_db_session()
    
    try:
        # Update task progress
        self.update_state(state='PROGRESS', meta={'status': 'Processing job'})
        
        # Get job record
        job = db.query(ConversionJob).filter(
            ConversionJob.id == uuid.UUID(job_id)
        ).first()
        
        if not job:
            logger.error(f"Job not found: {job_id}")
            return {'status': 'ERROR', 'message': 'Job not found'}
        
        # Update job status
        job.status = JobStatus.IN_PROGRESS
        db.commit()
        
        logger.info(f"Processing job {job_id} with {job.file_count} files")
        
        # Create output directory for this job
        job_output_dir = os.path.join(settings.full_temp_path, f"job_{job_id}_output")
        os.makedirs(job_output_dir, exist_ok=True)
        
        # Get all files for this job
        files = db.query(ConversionFile).filter(
            ConversionFile.job_id == uuid.UUID(job_id)
        ).all()
        
        if not files:
            job.status = JobStatus.FAILED
            job.error_message = "No files found in job"
            db.commit()
            return {'status': 'ERROR', 'message': 'No files found'}
        
        # Process each file by calling convert tasks directly
        # We can't use .delay().get() pattern within a task, so we'll call the function directly
        completed_files = 0
        failed_files = 0
        
        for file_record in files:
            if file_record.status == FileStatus.PENDING:
                try:
                    # Call conversion implementation function directly
                    result = _convert_docx_to_pdf_impl(
                        str(file_record.id),
                        file_record.original_path,
                        job_output_dir
                    )
                    
                    if result['status'] == 'SUCCESS':
                        completed_files += 1
                    else:
                        failed_files += 1
                        
                except Exception as e:
                    logger.error(f"Conversion failed for {file_record.filename}: {str(e)}")
                    failed_files += 1
        
        logger.info(f"Job {job_id}: {completed_files} completed, {failed_files} failed out of {len(files)}")
        
        # Refresh job data
        db.refresh(job)
        
        if completed_files > 0:
            # Create final ZIP archive by calling the function directly
            try:
                archive_result = _create_final_archive_impl(job_id)
                
                if archive_result.get('status') == 'SUCCESS':
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    job.output_zip_path = archive_result.get('zip_path')
                    logger.info(f"Job {job_id} completed successfully")
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = "Failed to create final archive"
                    logger.error(f"Job {job_id} failed during archiving")
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_message = f"Error creating archive: {str(e)}"
                logger.error(f"Job {job_id} failed during archiving: {str(e)}")
        else:
            # All files failed
            job.status = JobStatus.FAILED
            job.error_message = "All file conversions failed"
            logger.error(f"Job {job_id} failed - all conversions failed")
        
        db.commit()
        
        return {
            'status': 'SUCCESS',
            'job_id': job_id,
            'completed_files': completed_files,
            'failed_files': failed_files,
            'final_status': job.status.value
        }
        
    except Exception as e:
        logger.error(f"Error in process_conversion_job task: {str(e)}")
        
        # Update job status to failed
        try:
            if 'job' in locals():
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                db.commit()
        except:
            pass
        
        return {'status': 'ERROR', 'message': str(e)}
    
    finally:
        db.close()


@celery_app.task(bind=True, name='app.workers.tasks.create_final_archive')
def create_final_archive(self, job_id: str):
    return _create_final_archive_impl(job_id, self)


def _create_final_archive_impl(job_id: str, task_context=None):
    """
    Create final ZIP archive with all converted PDFs
    
    Args:
        job_id: UUID of the job
    """
    db = get_db_session()
    
    try:
        # Update task progress if task context is available
        if task_context:
            task_context.update_state(state='PROGRESS', meta={'status': 'Creating archive'})
        
        # Get job record
        job = db.query(ConversionJob).filter(
            ConversionJob.id == uuid.UUID(job_id)
        ).first()
        
        if not job:
            logger.error(f"Job not found: {job_id}")
            return {'status': 'ERROR', 'message': 'Job not found'}
        
        # Get all successfully converted files
        completed_files = db.query(ConversionFile).filter(
            ConversionFile.job_id == uuid.UUID(job_id),
            ConversionFile.status == FileStatus.COMPLETED,
            ConversionFile.converted_path.isnot(None)
        ).all()
        
        if not completed_files:
            logger.error(f"No completed files found for job {job_id}")
            return {'status': 'ERROR', 'message': 'No completed files found'}
        
        # Prepare files for archiving
        files_to_archive = []
        for file_record in completed_files:
            if os.path.exists(file_record.converted_path):
                files_to_archive.append((
                    file_record.filename,
                    file_record.converted_path
                ))
        
        if not files_to_archive:
            logger.error(f"No valid PDF files found for job {job_id}")
            return {'status': 'ERROR', 'message': 'No valid PDF files found'}
        
        # Create ZIP archive
        archive_filename = f"converted_files_{job_id}.zip"
        archive_path = os.path.join(settings.full_output_path, archive_filename)
        
        logger.info(f"Creating archive with {len(files_to_archive)} files: {archive_path}")
        
        final_archive_path = create_zip_archive(files_to_archive, archive_path)
        
        logger.info(f"Successfully created archive for job {job_id}: {final_archive_path}")
        
        return {
            'status': 'SUCCESS',
            'zip_path': final_archive_path,
            'files_count': len(files_to_archive)
        }
        
    except Exception as e:
        logger.error(f"Error in create_final_archive task: {str(e)}")
        return {'status': 'ERROR', 'message': str(e)}
    
    finally:
        db.close()


@celery_app.task(name='app.workers.tasks.cleanup_job_files')
def cleanup_job_files(job_id: str, max_age_days: int = 7):
    """
    Clean up temporary files for a job
    
    Args:
        job_id: UUID of the job
        max_age_days: Maximum age in days before cleanup
    """
    try:
        # Clean up temporary directories
        input_dir = os.path.join(settings.full_temp_path, f"job_{job_id}_input")
        output_dir = os.path.join(settings.full_temp_path, f"job_{job_id}_output")
        
        cleanup_directory(input_dir)
        cleanup_directory(output_dir)
        
        logger.info(f"Cleaned up temporary files for job {job_id}")
        
        return {'status': 'SUCCESS', 'message': f'Cleaned up job {job_id}'}
        
    except Exception as e:
        logger.error(f"Error in cleanup_job_files task: {str(e)}")
        return {'status': 'ERROR', 'message': str(e)}
