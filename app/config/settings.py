from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database settings
    database_url: str = "postgresql://converter_user:converter_pass@db:5432/docx_converter"
    
    # Redis settings
    redis_url: str = "redis://redis:6379/0"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Bulk DOCX to PDF Converter"
    api_version: str = "1.0.0"
    
    # Storage settings
    storage_path: str = "/tmp/storage"
    upload_path: str = "uploads"
    output_path: str = "outputs"
    temp_path: str = "temp"
    
    # File settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB per file
    max_files_per_job: int = 1000
    allowed_extensions: list = [".docx"]
    
    # Worker settings
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    
    # Security settings
    secret_key: str = "your-secret-key-change-this-in-production"
    
    # LibreOffice settings
    libreoffice_timeout: int = 300  # 5 minutes
    
    @property
    def full_upload_path(self) -> str:
        return os.path.join(self.storage_path, self.upload_path)
    
    @property
    def full_output_path(self) -> str:
        return os.path.join(self.storage_path, self.output_path)
    
    @property
    def full_temp_path(self) -> str:
        return os.path.join(self.storage_path, self.temp_path)

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
