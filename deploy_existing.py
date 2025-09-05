#!/usr/bin/env python3
"""
Deployment script for bulk DOCX to PDF converter using existing Render databases
"""

import requests
import json
import argparse
import time
from datetime import datetime
from typing import Dict, Any, Optional

class RenderDeployer:
    def __init__(self, api_key: str, repo_url: str, timeout: int = 600):
        self.api_key = api_key
        self.repo_url = repo_url
        self.timeout = timeout
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.owner_id = None
        
        # Existing database IDs
        self.postgres_id = "dpg-d2tcequuk2gs73co9mk0-a"
        self.redis_id = "red-d2tcg1ur433s73d9fung"
        
        # Connection strings (using Render internal hostnames)
        self.postgres_url = f"postgresql://converter_user@dpg-d2tcequuk2gs73co9mk0-a-oregon-postgres.render.com:5432/docx_converter"
        self.redis_url = f"redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379"

    def log(self, level: str, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=data)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.log("ERROR", f"API request failed: {e}")
            if hasattr(e.response, 'text'):
                self.log("ERROR", f"Response: {e.response.text}")
            raise

    def get_owner_id(self) -> str:
        """Get the owner ID for the account"""
        self.log("INFO", "Getting owner information...")
        response = self.make_request("GET", "owners")
        owners = response.json()
        
        if not owners:
            raise Exception("No owners found")
        
        owner_id = owners[0]['owner']['id']
        self.log("INFO", f"Found owner ID: {owner_id}")
        return owner_id

    def create_web_service(self) -> str:
        """Create the FastAPI web service"""
        timestamp = int(time.time())
        service_name = f"docx-converter-web-{timestamp}"
        
        self.log("INFO", "Creating FastAPI web service...")
        
        service_data = {
            "type": "web_service",
            "name": service_name,
            "ownerId": self.owner_id,
            "repo": self.repo_url,
            "autoDeploy": "yes",
            "branch": "main",
            "rootDir": "",
            "serviceDetails": {
                "env": "python",
                "plan": "free",
                "region": "oregon",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port 10000",
                "numInstances": 1,
                "envVars": [
                    {"key": "DATABASE_URL", "value": self.postgres_url},
                    {"key": "REDIS_URL", "value": self.redis_url},
                    {"key": "CELERY_BROKER_URL", "value": self.redis_url},
                    {"key": "CELERY_RESULT_BACKEND", "value": self.redis_url},
                    {"key": "UPLOAD_DIR", "value": "/tmp/uploads"},
                    {"key": "CONVERTED_DIR", "value": "/tmp/converted"},
                    {"key": "MAX_FILE_SIZE_MB", "value": "50"},
                    {"key": "MAX_FILES_PER_BATCH", "value": "20"},
                    {"key": "CORS_ORIGINS", "value": "*"},
                    {"key": "ENVIRONMENT", "value": "production"}
                ]
            }
        }
        
        response = self.make_request("POST", "services", service_data)
        service_id = response.json()['id']
        service_url = response.json()['serviceDetails']['url']
        
        self.log("INFO", f"Created web service: {service_name} (ID: {service_id})")
        self.log("INFO", f"Web service URL: {service_url}")
        
        return service_id

    def create_worker_service(self) -> str:
        """Create the Celery worker service"""
        timestamp = int(time.time())
        service_name = f"docx-converter-worker-{timestamp}"
        
        self.log("INFO", "Creating Celery worker service...")
        
        service_data = {
            "type": "private_service",
            "name": service_name,
            "ownerId": self.owner_id,
            "repo": self.repo_url,
            "autoDeploy": "yes",
            "branch": "main",
            "rootDir": "",
            "serviceDetails": {
                "env": "python",
                "plan": "free",
                "region": "oregon",
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": "celery -A app.workers.celery_app worker --loglevel=info",
                "numInstances": 1,
                "envVars": [
                    {"key": "DATABASE_URL", "value": self.postgres_url},
                    {"key": "REDIS_URL", "value": self.redis_url},
                    {"key": "CELERY_BROKER_URL", "value": self.redis_url},
                    {"key": "CELERY_RESULT_BACKEND", "value": self.redis_url},
                    {"key": "UPLOAD_DIR", "value": "/tmp/uploads"},
                    {"key": "CONVERTED_DIR", "value": "/tmp/converted"},
                    {"key": "MAX_FILE_SIZE_MB", "value": "50"},
                    {"key": "MAX_FILES_PER_BATCH", "value": "20"},
                    {"key": "ENVIRONMENT", "value": "production"}
                ]
            }
        }
        
        response = self.make_request("POST", "services", service_data)
        service_id = response.json()['id']
        
        self.log("INFO", f"Created worker service: {service_name} (ID: {service_id})")
        
        return service_id

    def wait_for_service_deployment(self, service_id: str, service_type: str) -> bool:
        """Wait for service to be deployed"""
        self.log("INFO", f"Waiting for {service_type} service to deploy...")
        
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                response = self.make_request("GET", f"services/{service_id}")
                service_data = response.json()
                
                # Check if there are any deploys
                deploys_response = self.make_request("GET", f"services/{service_id}/deploys")
                deploys = deploys_response.json()
                
                if deploys:
                    latest_deploy = deploys[0]
                    status = latest_deploy['status']
                    
                    if status == 'live':
                        self.log("INFO", f"{service_type} service deployed successfully!")
                        return True
                    elif status in ['build_failed', 'update_failed', 'deactivated']:
                        self.log("ERROR", f"{service_type} service deployment failed with status: {status}")
                        return False
                    else:
                        self.log("INFO", f"{service_type} service status: {status}")
                
                time.sleep(30)
                
            except Exception as e:
                self.log("ERROR", f"Error checking service status: {e}")
                time.sleep(30)
        
        self.log("ERROR", f"{service_type} service deployment timed out")
        return False

    def deploy(self) -> bool:
        """Main deployment function"""
        try:
            print("\nBulk DOCX to PDF Converter - Render.com Deployment (Using Existing DBs)")
            print("="*80)
            print(f"Repository: {self.repo_url}")
            print(f"Timeout: {self.timeout} seconds")
            print(f"Using existing PostgreSQL: {self.postgres_id}")
            print(f"Using existing Redis: {self.redis_id}")
            print()
            
            self.log("INFO", "Starting deployment of bulk DOCX to PDF converter...")
            
            # Step 0: Get owner ID
            self.log("INFO", "Step 0: Getting account information...")
            self.owner_id = self.get_owner_id()
            
            # Step 1: Create web service
            self.log("INFO", "Step 1: Creating FastAPI web service...")
            web_service_id = self.create_web_service()
            
            # Step 2: Create worker service
            self.log("INFO", "Step 2: Creating Celery worker service...")
            worker_service_id = self.create_worker_service()
            
            # Step 3: Wait for deployments
            self.log("INFO", "Step 3: Waiting for services to deploy...")
            
            web_deployed = self.wait_for_service_deployment(web_service_id, "Web")
            worker_deployed = self.wait_for_service_deployment(worker_service_id, "Worker")
            
            if web_deployed and worker_deployed:
                # Get final service details
                web_response = self.make_request("GET", f"services/{web_service_id}")
                web_url = web_response.json()['serviceDetails']['url']
                
                print("\n" + "="*80)
                print("🎉 DEPLOYMENT SUCCESSFUL!")
                print("="*80)
                print(f"FastAPI Web Service: {web_url}")
                print(f"Celery Worker Service: {worker_service_id}")
                print(f"PostgreSQL Database: {self.postgres_id}")
                print(f"Redis Cache: {self.redis_id}")
                print("\nNext steps:")
                print(f"1. Test the API: curl {web_url}/health")
                print(f"2. Upload files: {web_url}/upload")
                print(f"3. Monitor logs in the Render dashboard")
                print("="*80)
                
                return True
            else:
                self.log("ERROR", "Some services failed to deploy")
                return False
                
        except Exception as e:
            self.log("ERROR", f"Deployment failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Deploy bulk DOCX to PDF converter to Render.com using existing databases")
    parser.add_argument("--api-key", required=True, help="Render API key")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--timeout", type=int, default=600, help="Deployment timeout in seconds")
    
    args = parser.parse_args()
    
    deployer = RenderDeployer(args.api_key, args.repo_url, args.timeout)
    success = deployer.deploy()
    
    if success:
        print("\nDeployment completed successfully!")
        exit(0)
    else:
        print("\nDeployment failed!")
        exit(1)

if __name__ == "__main__":
    main()
