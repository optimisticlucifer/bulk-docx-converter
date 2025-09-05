import os
import zipfile
import shutil
import mimetypes
from typing import List, Tuple, Optional
from pathlib import Path
from app.config.settings import settings
import logging
import tempfile

logger = logging.getLogger(__name__)


def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        settings.full_upload_path,
        settings.full_output_path,
        settings.full_temp_path
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def validate_file_extension(filename: str) -> bool:
    """Validate if file has allowed extension"""
    file_ext = Path(filename).suffix.lower()
    return file_ext in settings.allowed_extensions


def validate_file_size(file_size: int) -> bool:
    """Validate if file size is within limits"""
    return file_size <= settings.max_file_size


def extract_zip_file(zip_path: str, extract_to: str) -> List[Tuple[str, str]]:
    """
    Extract zip file and return list of (filename, extracted_path) tuples
    Only extracts DOCX files
    """
    extracted_files = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files in zip
            file_list = zip_ref.namelist()
            
            # Filter for DOCX files
            docx_files = [f for f in file_list if validate_file_extension(f) and not f.endswith('/')]
            
            if len(docx_files) > settings.max_files_per_job:
                raise ValueError(f"Too many files in zip. Maximum allowed: {settings.max_files_per_job}")
            
            # Extract each DOCX file
            for file_info in zip_ref.infolist():
                if file_info.filename in docx_files:
                    # Check file size
                    if file_info.file_size > settings.max_file_size:
                        logger.warning(f"Skipping {file_info.filename}: file too large ({file_info.file_size} bytes)")
                        continue
                    
                    # Extract file
                    extracted_path = zip_ref.extract(file_info, extract_to)
                    extracted_files.append((file_info.filename, extracted_path))
                    
                    logger.info(f"Extracted {file_info.filename} to {extracted_path}")
    
    except zipfile.BadZipFile:
        raise ValueError("Invalid zip file")
    except Exception as e:
        logger.error(f"Error extracting zip file: {str(e)}")
        raise ValueError(f"Error extracting zip file: {str(e)}")
    
    return extracted_files


def create_zip_archive(files: List[Tuple[str, str]], output_path: str) -> str:
    """
    Create zip archive from list of (original_filename, file_path) tuples
    Returns path to created zip file
    """
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for original_filename, file_path in files:
                if os.path.exists(file_path):
                    # Use original filename in zip, but change extension to .pdf
                    zip_filename = Path(original_filename).stem + ".pdf"
                    zip_ref.write(file_path, zip_filename)
                    logger.info(f"Added {file_path} to zip as {zip_filename}")
                else:
                    logger.warning(f"File not found: {file_path}")
        
        logger.info(f"Created zip archive: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error creating zip archive: {str(e)}")
        raise ValueError(f"Error creating zip archive: {str(e)}")


def cleanup_directory(directory_path: str):
    """Remove directory and all its contents"""
    try:
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
            logger.info(f"Cleaned up directory: {directory_path}")
    except Exception as e:
        logger.error(f"Error cleaning up directory {directory_path}: {str(e)}")


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def is_valid_docx_file(file_path: str) -> bool:
    """
    Check if file is a valid DOCX file
    This is a basic check - could be enhanced with more sophisticated validation
    """
    try:
        # Check if it's a valid zip file (DOCX files are zip archives)
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # DOCX files should contain these files
            required_files = ['word/document.xml', '[Content_Types].xml']
            file_list = zip_ref.namelist()
            
            for required_file in required_files:
                if required_file not in file_list:
                    return False
            
            return True
    except (zipfile.BadZipFile, FileNotFoundError):
        return False


def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing problematic characters
    """
    # Remove path separators and other problematic characters
    import re
    safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
    return safe_name


def create_job_directory(job_id: str) -> Tuple[str, str]:
    """
    Create directories for a job and return (input_dir, output_dir) paths
    """
    input_dir = os.path.join(settings.full_temp_path, f"job_{job_id}_input")
    output_dir = os.path.join(settings.full_temp_path, f"job_{job_id}_output")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    return input_dir, output_dir
