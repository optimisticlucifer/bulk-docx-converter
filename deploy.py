#!/usr/bin/env python3
"""
Automated deployment script for Render.com
Deploys the entire bulk DOCX to PDF converter service with a single command.

Usage: python deploy.py --api-key YOUR_RENDER_API_KEY --repo-url https://github.com/username/repo
"""

import requests
import json
import time
import argparse
import sys
from typing import Dict, Any


class RenderDeployer:
    def __init__(self, api_key: str, repo_url: str):
        self.api_key = api_key
        self.repo_url = repo_url
        self.base_url = "https://api.render.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.services = {}
        self.owner_id = None
        # Add timestamp to avoid naming conflicts
        import time
        self.timestamp = str(int(time.time()))
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def get_owner_id(self) -> str:
        """Get the owner ID for the authenticated user"""
        try:
            self.log("Getting owner information...")
            response = self.make_request("GET", "owners")
            
            if response and len(response) > 0:
                owner = response[0]  # Get the first (usually only) owner
                owner_id = owner.get("owner", {}).get("id")
                if owner_id:
                    self.owner_id = owner_id
                    self.log(f"Found owner ID: {owner_id}")
                    return owner_id
                else:
                    raise Exception("Could not find owner ID in response")
            else:
                raise Exception("No owners found for this account")
        except Exception as e:
            self.log(f"Failed to get owner ID: {e}", "ERROR")
            raise
    
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make API request to Render"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.log(f"API request failed: {e}", "ERROR")
            if hasattr(e.response, 'text'):
                self.log(f"Response: {e.response.text}", "ERROR")
            raise
    
    def wait_for_service(self, service_id: str, service_type: str, timeout: int = 600):
        """Wait for a service to be ready"""
        self.log(f"Waiting for {service_type} service {service_id} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if service_type in ["pserv", "redis"]:
                    endpoint = f"services/{service_id}"
                else:
                    endpoint = f"services/{service_id}"
                
                service = self.make_request("GET", endpoint)
                status = service.get("service", {}).get("status", "unknown")
                
                self.log(f"{service_type} status: {status}")
                
                if status in ["available", "running"]:
                    self.log(f"{service_type} is ready!")
                    return service
                elif status in ["failed", "suspended"]:
                    self.log(f"{service_type} deployment failed with status: {status}", "ERROR")
                    return None
                
                time.sleep(30)  # Wait 30 seconds before checking again
                
            except Exception as e:
                self.log(f"Error checking service status: {e}", "ERROR")
                time.sleep(30)
        
        self.log(f"Timeout waiting for {service_type} to be ready", "ERROR")
        return None
    
    def wait_for_postgres_service(self, service_id: str, timeout: int = 600):
        """Wait for a PostgreSQL service to be ready"""
        self.log(f"Waiting for PostgreSQL service {service_id} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                service = self.make_request("GET", f"postgres/{service_id}")
                status = service.get("status", "unknown")
                
                self.log(f"PostgreSQL status: {status}")
                
                if status == "available":
                    self.log("PostgreSQL is ready!")
                    # Update connection info
                    self.services["database"]["connection_info"] = service
                    self.log(f"PostgreSQL connection string: {service.get('connectionString', 'NOT_FOUND')}")
                    return service
                elif status in ["failed", "suspended"]:
                    self.log(f"PostgreSQL deployment failed with status: {status}", "ERROR")
                    return None
                
                time.sleep(30)  # Wait 30 seconds before checking again
                
            except Exception as e:
                self.log(f"Error checking PostgreSQL status: {e}", "ERROR")
                time.sleep(30)
        
        self.log(f"Timeout waiting for PostgreSQL to be ready", "ERROR")
        return None
    
    def wait_for_redis_service(self, service_id: str, timeout: int = 600):
        """Wait for a Redis service to be ready"""
        self.log(f"Waiting for Redis service {service_id} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                service = self.make_request("GET", f"redis/{service_id}")
                status = service.get("status", "unknown")
                
                self.log(f"Redis status: {status}")
                
                if status == "available":
                    self.log("Redis is ready!")
                    # Update connection string
                    connection_string = service.get("connectionString")
                    self.services["redis"]["connection_string"] = connection_string
                    self.log(f"Redis connection string: {connection_string or 'NOT_FOUND'}")
                    return service
                elif status in ["failed", "suspended"]:
                    self.log(f"Redis deployment failed with status: {status}", "ERROR")
                    return None
                
                time.sleep(30)  # Wait 30 seconds before checking again
                
            except Exception as e:
                self.log(f"Error checking Redis status: {e}", "ERROR")
                time.sleep(30)
        
        self.log(f"Timeout waiting for Redis to be ready", "ERROR")
        return None
    
    def create_postgresql_database(self) -> str:
        """Create PostgreSQL database"""
        self.log("Creating PostgreSQL database...")
        
        if not self.owner_id:
            raise Exception("Owner ID not set. Call get_owner_id() first.")
        
        postgres_config = {
            "name": f"docx-converter-db-{self.timestamp}",
            "ownerID": self.owner_id,
            "plan": "free",
            "databaseName": "docx_converter",
            "databaseUser": "converter_user",
            "region": "oregon",
            "version": "15"
        }
        
        try:
            # Use the correct endpoint for PostgreSQL databases
            result = self.make_request("POST", "postgres", postgres_config)
            service_id = result["id"]
            self.services["database"] = {
                "id": service_id,
                "connection_info": result
            }
            
            self.log(f"PostgreSQL database created with ID: {service_id}")
            
            # Wait for database to be ready
            service_info = self.wait_for_postgres_service(service_id)
            if service_info:
                return service_id
            else:
                raise Exception("Failed to create PostgreSQL database")
                
        except Exception as e:
            self.log(f"Failed to create PostgreSQL database: {e}", "ERROR")
            raise
    
    def create_redis_database(self) -> str:
        """Create Redis database"""
        self.log("Creating Redis database...")
        
        if not self.owner_id:
            raise Exception("Owner ID not set. Call get_owner_id() first.")
        
        redis_config = {
            "name": f"docx-converter-redis-{self.timestamp}",
            "ownerID": self.owner_id,
            "plan": "free",
            "region": "oregon"
        }
        
        try:
            # Use the correct endpoint for Redis databases  
            result = self.make_request("POST", "redis", redis_config)
            service_id = result["id"]
            self.services["redis"] = {
                "id": service_id,
                "connection_string": result.get("connectionString")
            }
            
            self.log(f"Redis database created with ID: {service_id}")
            
            # Wait for Redis to be ready
            service_info = self.wait_for_redis_service(service_id)
            if service_info:
                return service_id
            else:
                raise Exception("Failed to create Redis database")
                
        except Exception as e:
            self.log(f"Failed to create Redis database: {e}", "ERROR")
            raise
    
    def create_web_service(self) -> str:
        """Create FastAPI web service"""
        self.log("Creating FastAPI web service...")
        
        # Get database connection string
        db_info = self.services.get("database", {}).get("connection_info", {})
        redis_connection = self.services.get("redis", {}).get("connection_string")
        
        self.log(f"DEBUG: db_info keys: {list(db_info.keys()) if db_info else 'None'}")
        self.log(f"DEBUG: redis_connection: {redis_connection or 'None'}")
        
        if not db_info or not redis_connection:
            raise Exception(f"Database services not ready. DB: {bool(db_info)}, Redis: {bool(redis_connection)}")
        
        # Use the connection string directly from PostgreSQL service
        database_url = db_info.get("connectionString")
        if not database_url:
            raise Exception("PostgreSQL connection string not available")
        
        if not self.owner_id:
            raise Exception("Owner ID not set. Call get_owner_id() first.")
        
        web_config = {
            "type": "web_service",
            "name": f"docx-converter-api-{self.timestamp}",
            "ownerID": self.owner_id,
            "repo": self.repo_url,
            "plan": "free",
            "region": "oregon",
            "buildCommand": "./build.sh",
            "startCommand": "python -m app.main",
            "envVars": [
                {"key": "DATABASE_URL", "value": database_url},
                {"key": "REDIS_URL", "value": redis_connection},
                {"key": "CELERY_BROKER_URL", "value": redis_connection},
                {"key": "CELERY_RESULT_BACKEND", "value": redis_connection},
                {"key": "API_HOST", "value": "0.0.0.0"},
                {"key": "STORAGE_PATH", "value": "/tmp/storage"},
                {"key": "PYTHONPATH", "value": "/opt/render/project/src"}
            ]
        }
        
        try:
            result = self.make_request("POST", "services", web_config)
            service_id = result["service"]["id"]
            self.services["web"] = {"id": service_id}
            
            self.log(f"Web service created with ID: {service_id}")
            return service_id
            
        except Exception as e:
            self.log(f"Failed to create web service: {e}", "ERROR")
            raise
    
    def create_worker_service(self) -> str:
        """Create Celery worker service"""
        self.log("Creating Celery worker service...")
        
        # Get database connection string
        db_info = self.services.get("database", {}).get("connection_info", {})
        redis_connection = self.services.get("redis", {}).get("connection_string")
        
        if not db_info or not redis_connection:
            raise Exception("Database services not ready")
        
        # Use the connection string directly from PostgreSQL service
        database_url = db_info.get("connectionString")
        if not database_url:
            raise Exception("PostgreSQL connection string not available")
        
        if not self.owner_id:
            raise Exception("Owner ID not set. Call get_owner_id() first.")
        
        worker_config = {
            "type": "background_worker",
            "name": f"docx-converter-worker-{self.timestamp}",
            "ownerID": self.owner_id,
            "repo": self.repo_url,
            "plan": "free",
            "region": "oregon",
            "buildCommand": "./build.sh",
            "startCommand": "celery -A app.workers.celery_app worker --loglevel=info --concurrency=2",
            "envVars": [
                {"key": "DATABASE_URL", "value": database_url},
                {"key": "REDIS_URL", "value": redis_connection},
                {"key": "CELERY_BROKER_URL", "value": redis_connection},
                {"key": "CELERY_RESULT_BACKEND", "value": redis_connection},
                {"key": "STORAGE_PATH", "value": "/tmp/storage"},
                {"key": "PYTHONPATH", "value": "/opt/render/project/src"}
            ]
        }
        
        try:
            result = self.make_request("POST", "services", worker_config)
            service_id = result["service"]["id"]
            self.services["worker"] = {"id": service_id}
            
            self.log(f"Worker service created with ID: {service_id}")
            return service_id
            
        except Exception as e:
            self.log(f"Failed to create worker service: {e}", "ERROR")
            raise
    
    def get_service_url(self, service_id: str) -> str:
        """Get the public URL for a web service"""
        try:
            service_info = self.make_request("GET", f"services/{service_id}")
            service_url = service_info["service"].get("serviceDetails", {}).get("url")
            return service_url
        except Exception as e:
            self.log(f"Failed to get service URL: {e}", "ERROR")
            return None
    
    def deploy_all(self):
        """Deploy all services"""
        try:
            self.log("Starting deployment of bulk DOCX to PDF converter...")
            
            # Step 0: Get owner ID
            self.log("Step 0: Getting account information...")
            self.get_owner_id()
            
            # Step 1: Create PostgreSQL database
            self.log("Step 1: Creating PostgreSQL database...")
            db_id = self.create_postgresql_database()
            
            # Step 2: Create Redis database
            self.log("Step 2: Creating Redis database...")
            redis_id = self.create_redis_database()
            
            # Step 3: Create web service
            self.log("Step 3: Creating FastAPI web service...")
            web_id = self.create_web_service()
            
            # Step 4: Create worker service
            self.log("Step 4: Creating Celery worker service...")
            worker_id = self.create_worker_service()
            
            # Step 5: Wait for web service to be ready and get URL
            self.log("Step 5: Waiting for web service to be ready...")
            web_service = self.wait_for_service(web_id, "Web Service")
            
            if web_service:
                service_url = self.get_service_url(web_id)
                
                self.log("=" * 60, "SUCCESS")
                self.log("DEPLOYMENT COMPLETED SUCCESSFULLY!", "SUCCESS")
                self.log("=" * 60, "SUCCESS")
                self.log(f"PostgreSQL Database ID: {db_id}", "SUCCESS")
                self.log(f"Redis Database ID: {redis_id}", "SUCCESS")
                self.log(f"Web Service ID: {web_id}", "SUCCESS")
                self.log(f"Worker Service ID: {worker_id}", "SUCCESS")
                
                if service_url:
                    self.log(f"API URL: {service_url}", "SUCCESS")
                    self.log(f"API Docs: {service_url}/docs", "SUCCESS")
                    self.log("", "SUCCESS")
                    self.log("Test your deployment with:", "SUCCESS")
                    self.log(f"python test_production.py {service_url}", "SUCCESS")
                
                self.log("", "SUCCESS")
                self.log("Note: Services may take a few minutes to fully initialize", "SUCCESS")
                self.log("Free tier services will sleep after 15 minutes of inactivity", "SUCCESS")
                
                return True
            else:
                self.log("Web service failed to deploy", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Deployment failed: {e}", "ERROR")
            return False


def main():
    parser = argparse.ArgumentParser(description="Deploy bulk DOCX to PDF converter to Render.com")
    parser.add_argument("--api-key", required=True, help="Your Render API key")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL (e.g., https://github.com/username/repo)")
    parser.add_argument("--timeout", type=int, default=600, help="Deployment timeout in seconds (default: 600)")
    
    args = parser.parse_args()
    
    print("Bulk DOCX to PDF Converter - Render.com Deployment")
    print("=" * 60)
    print(f"Repository: {args.repo_url}")
    print(f"Timeout: {args.timeout} seconds")
    print("")
    
    deployer = RenderDeployer(args.api_key, args.repo_url)
    
    success = deployer.deploy_all()
    
    if success:
        print("\nDeployment completed successfully!")
        sys.exit(0)
    else:
        print("\nDeployment failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
