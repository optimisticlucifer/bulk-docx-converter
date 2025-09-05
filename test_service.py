#!/usr/bin/env python3
"""
Simple test script to verify the bulk DOCX to PDF converter service is working.

This script creates a sample DOCX file, zips it, submits it to the service,
and polls for completion.
"""

import requests
import zipfile
import io
import time
import json


def create_sample_docx():
    """Create a simple DOCX file for testing"""
    doc = Document()
    doc.add_heading('Test Document', 0)
    doc.add_paragraph('This is a test document for the bulk DOCX to PDF converter.')
    doc.add_paragraph('It contains some sample text to verify the conversion works properly.')
    
    # Save to bytes
    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)
    return docx_buffer.getvalue()


def create_test_zip():
    """Create a ZIP file containing sample DOCX files"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Create multiple test files
        for i in range(3):
            docx_content = create_sample_docx()
            zip_file.writestr(f'test_document_{i+1}.docx', docx_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def test_service(base_url='http://localhost:8000'):
    """Test the bulk conversion service"""
    
    print("🧪 Testing Bulk DOCX to PDF Converter Service")
    print("=" * 50)
    
    # Check if service is running
    try:
        response = requests.get(f'{base_url}/')
        print(f" Service is running: {response.json()}")
    except requests.exceptions.ConnectionError:
        print(" Service is not running. Please start it with: docker-compose up")
        return
    
    # Create test ZIP file
    print("\n📁 Creating test ZIP file with 3 DOCX documents...")
    zip_content = create_test_zip()
    
    # Submit job
    print("📤 Submitting conversion job...")
    try:
        response = requests.post(
            f'{base_url}/api/v1/jobs',
            files={'file': ('test_documents.zip', zip_content, 'application/zip')}
        )
        
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data['job_id']
            print(f" Job submitted successfully!")
            print(f"   Job ID: {job_id}")
            print(f"   File count: {job_data['file_count']}")
        else:
            print(f" Job submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
            
    except Exception as e:
        print(f" Error submitting job: {e}")
        return
    
    # Poll for completion
    print(f"\n⏳ Polling job status (Job ID: {job_id})...")
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f'{base_url}/api/v1/jobs/{job_id}')
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data['status']
                
                print(f"   Status: {status}")
                
                if status == 'COMPLETED':
                    print(" Job completed successfully!")
                    print("   File statuses:")
                    for file_info in status_data['files']:
                        status_icon = "" if file_info['status'] == 'COMPLETED' else ""
                        print(f"   {status_icon} {file_info['filename']}: {file_info['status']}")
                        if file_info.get('error_message'):
                            print(f"      Error: {file_info['error_message']}")
                    
                    # Download results
                    download_url = status_data.get('download_url')
                    if download_url:
                        print(f"\n📥 Downloading results from: {download_url}")
                        download_response = requests.get(f"{base_url}{download_url}")
                        
                        if download_response.status_code == 200:
                            with open('converted_files.zip', 'wb') as f:
                                f.write(download_response.content)
                            print(" Results downloaded successfully as 'converted_files.zip'")
                        else:
                            print(f" Download failed: {download_response.status_code}")
                    
                    break
                    
                elif status == 'FAILED':
                    print(" Job failed!")
                    if status_data.get('error_message'):
                        print(f"   Error: {status_data['error_message']}")
                    break
                    
                else:  # PENDING or IN_PROGRESS
                    print(f"   Waiting... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(5)
                    
            else:
                print(f" Error checking status: {response.status_code}")
                print(f"   Response: {response.text}")
                break
                
        except Exception as e:
            print(f" Error polling status: {e}")
            break
            
        attempt += 1
    
    if attempt >= max_attempts:
        print("⏰ Polling timeout - job may still be processing")
    
    print(f"\n🏁 Test completed!")


if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
    test_service(base_url)
