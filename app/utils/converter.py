import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DocxToPdfConverter:
    """
    Handles conversion of DOCX files to PDF using LibreOffice
    """
    
    def __init__(self):
        self.timeout = settings.libreoffice_timeout
    
    def convert_file(self, input_path: str, output_dir: str) -> Optional[str]:
        """
        Convert a single DOCX file to PDF
        
        Args:
            input_path: Path to the input DOCX file
            output_dir: Directory where PDF should be saved
            
        Returns:
            Path to the converted PDF file, or None if conversion failed
        """
        
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            return None
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Use LibreOffice headless mode to convert DOCX to PDF
            cmd = [
                'libreoffice',
                '--headless',
                '--convert-to',
                'pdf',
                '--outdir',
                output_dir,
                input_path
            ]
            
            logger.info(f"Converting {input_path} to PDF using command: {' '.join(cmd)}")
            
            # Run the conversion
            result = subprocess.run(
                cmd,
                timeout=self.timeout,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"LibreOffice conversion failed: {result.stderr}")
                return None
            
            # Determine output PDF path
            input_filename = Path(input_path).stem
            pdf_path = os.path.join(output_dir, f"{input_filename}.pdf")
            
            if os.path.exists(pdf_path):
                logger.info(f"Successfully converted {input_path} to {pdf_path}")
                return pdf_path
            else:
                logger.error(f"Expected PDF file not found: {pdf_path}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Conversion timeout for {input_path}")
            return None
        except Exception as e:
            logger.error(f"Error converting {input_path}: {str(e)}")
            return None
    
    def is_libreoffice_available(self) -> bool:
        """
        Check if LibreOffice is available on the system
        """
        try:
            result = subprocess.run(
                ['libreoffice', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def validate_conversion(self, pdf_path: str) -> bool:
        """
        Validate that the converted PDF file is valid
        """
        if not os.path.exists(pdf_path):
            return False
        
        # Check if file has content
        if os.path.getsize(pdf_path) == 0:
            return False
        
        # Basic PDF validation - check for PDF header
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    logger.warning(f"Invalid PDF header in {pdf_path}")
                    return False
        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {str(e)}")
            return False
        
        return True


# Create a global converter instance
converter = DocxToPdfConverter()
