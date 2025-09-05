#!/usr/bin/env python3
"""
Production test script for the deployed bulk DOCX to PDF converter service.

Usage: python test_production.py https://your-app.onrender.com
"""

import requests
import zipfile
import io
import time
import sys


def create_minimal_docx():
    """Create a minimal valid DOCX file structure"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as docx_zip:
        # Add [Content_Types].xml
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
        docx_zip.writestr('[Content_Types].xml', content_types)
        
        # Add _rels/.rels
        rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
        docx_zip.writestr('_rels/.rels', rels)
        
        # Add word/document.xml
        document = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>Test Document for PDF Conversion</w:t></w:r></w:p>
<w:p><w:r><w:t>This is a sample document created for testing the bulk DOCX to PDF converter service.</w:t></w:r></w:p>
<w:sectPr/>
</w:body>
</w:document>'''
        docx_zip.writestr('word/document.xml', document)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def create_test_zip():
    """Create a ZIP file containing test DOCX files"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Create test files with minimal DOCX content
        docx_content = create_minimal_docx()
        
        for i in range(2):  # Just 2 files for testing
            zip_file.writestr(f'test_document_{i+1}.docx', docx_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def test_service(base_url):
    """Test the bulk conversion service"""
    
    print("Testing Bulk DOCX to PDF Converter Service")
    print("=" * 50)
    print(f"Testing URL: {base_url}")
    
    # Check if service is running
    try:
        response = requests.get(f'{base_url}/')
        print(f"Service is running: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Service is not reachable")
        return
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    # Create test ZIP file
    print("\nCreating test ZIP file with 2 DOCX documents...")
    zip_content = create_test_zip()
    print(f"ZIP file size: {len(zip_content)} bytes")
    
    # Submit job
    print("Submitting conversion job...")
    try:
        response = requests.post(
            f'{base_url}/api/v1/jobs',
            files={'file': ('test_documents.zip', zip_content, 'application/zip')}
        )
        
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data['job_id']
            print(f"Job submitted successfully!")
            print(f"Job ID: {job_id}")
            print(f"File count: {job_data['file_count']}")
        else:
            print(f"Job submission failed: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
    except Exception as e:
        print(f"Error submitting job: {e}")
        return
    
    # Poll for completion
    print(f"\nPolling job status (Job ID: {job_id})...")
    max_attempts = 60  # 5 minutes max (Render free tier can be slow)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f'{base_url}/api/v1/jobs/{job_id}')
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data['status']
                
                print(f"Status: {status}")
                
                if status == 'COMPLETED':
                    print("Job completed successfully!")
                    print("File statuses:")
                    for file_info in status_data['files']:
                        status_symbol = "[OK]" if file_info['status'] == 'COMPLETED' else "[FAIL]"
                        print(f"   {status_symbol} {file_info['filename']}: {file_info['status']}")
                        if file_info.get('error_message'):
                            print(f"      Error: {file_info['error_message']}")
                    
                    # Download results
                    download_url = status_data.get('download_url')
                    if download_url:
                        print(f"\nDownloading results from: {download_url}")
                        download_response = requests.get(f"{base_url}{download_url}")
                        
                        if download_response.status_code == 200:
                            with open('converted_files.zip', 'wb') as f:
                                f.write(download_response.content)
                            print("Results downloaded successfully as 'converted_files.zip'")
                            print(f"Downloaded file size: {len(download_response.content)} bytes")
                        else:
                            print(f"Download failed: {download_response.status_code}")
                    
                    break
                    
                elif status == 'FAILED':
                    print("Job failed!")
                    break
                    
                else:  # PENDING or IN_PROGRESS
                    print(f"Waiting... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(5)
                    
            else:
                print(f"Error checking status: {response.status_code}")
                print(f"Response: {response.text}")
                break
                
        except Exception as e:
            print(f"Error polling status: {e}")
            break
            
        attempt += 1
    
    if attempt >= max_attempts:
        print("Polling timeout - job may still be processing")
        print("This is normal on Render free tier - try again later")
    
    print(f"\nTest completed!")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_production.py <base_url>")
        print("Example: python test_production.py https://docx-converter-api.onrender.com")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    test_service(base_url)
