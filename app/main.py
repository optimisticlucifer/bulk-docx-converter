from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.config.settings import settings
from app.config.database import engine, Base
from app.api.routes import router
from app.utils.logging_config import setup_logging
from app.utils.file_utils import ensure_directories


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting up the application")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Ensure storage directories exist
    ensure_directories()
    logger.info("Storage directories ensured")
    
    yield
    
    logger.info("Shutting down the application")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
    ## Bulk DOCX to PDF Converter
    
    A robust, scalable, and asynchronous web service that converts DOCX files into PDF format.
    
    ### Features:
    - **Bulk Processing**: Upload a ZIP file containing multiple DOCX files
    - **Asynchronous Processing**: Non-blocking conversion using Celery workers
    - **Real-time Status**: Track conversion progress with detailed status updates
    - **Download Results**: Get converted PDFs as a single ZIP archive
    - **Error Handling**: Robust error handling with detailed error messages
    
    ### Usage:
    1. Upload a ZIP file containing DOCX files to `/api/v1/jobs`
    2. Get a job ID and track progress with `/api/v1/jobs/{job_id}`
    3. Download converted PDFs from `/api/v1/jobs/{job_id}/download` when complete
    """,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred"
        }
    )


# Include API routes
app.include_router(router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Bulk DOCX to PDF Converter",
        "version": settings.api_version,
        "status": "healthy",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", settings.api_port))
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=port,
        reload=False,  # Disable reload in production
        log_config=None  # Use our custom logging configuration
    )
