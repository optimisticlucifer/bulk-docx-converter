# Bulk DOCX to PDF Converter

A robust, scalable, and asynchronous web service that converts DOCX files into PDF format. The service handles bulk uploads and provides real-time status updates through a clean RESTful API.

## Features

- **Bulk Processing**: Upload ZIP files containing multiple DOCX files (up to 1000 files per job)
- **Asynchronous Processing**: Non-blocking conversion using Celery workers
- **Real-time Status Tracking**: Monitor conversion progress with detailed status updates
- **Robust Error Handling**: Individual file failures don't stop the entire job
- **Scalable Architecture**: Designed for horizontal scaling with message queues
- **Docker Support**: Fully containerized with docker-compose for easy deployment
- **RESTful API**: Clean, well-documented API endpoints
- **File Validation**: Comprehensive validation of DOCX files and ZIP archives

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │     Redis       │    │  PostgreSQL     │
│   Web Server    │◄──►│ Message Queue   │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       ▲
         │                       │
         ▼                       │
┌─────────────────┐    ┌─────────────────┐
│  File Storage   │    │ Celery Workers  │
│   (Docker Vol)  │◄──►│  (LibreOffice)  │
└─────────────────┘    └─────────────────┘
```

### Components

- **FastAPI Application**: REST API server handling job submission and status queries
- **Celery Workers**: Background workers performing DOCX to PDF conversion using LibreOffice
- **Redis**: Message broker for Celery task queue
- **PostgreSQL**: Database for job and file status tracking
- **Docker Volumes**: Shared storage for file processing between containers

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 2GB of free disk space
- Port 8000 available on your machine

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd bulk-docx-converter
   ```

2. **Create environment configuration:**
   ```bash
   cp .env.example .env
   # Edit .env file if needed (default values should work for development)
   ```

3. **Build and start the services:**
   ```bash
   docker compose up --build
   ```

4. **Wait for services to be ready:**
   - The API will be available at http://localhost:8000
   - Database migrations will run automatically
   - Workers will start processing jobs

## API Documentation

Once the service is running, you can access:

- **Interactive API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Documentation**: http://localhost:8000/redoc (ReDoc)

### API Endpoints

#### 1. Submit Conversion Job
```http
POST /api/v1/jobs
```

Upload a ZIP file containing DOCX files for conversion.

**Request:**
- Content-Type: `multipart/form-data`
- Body: ZIP file containing DOCX files

**Response (202 Accepted):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "file_count": 3
}
```

#### 2. Get Job Status
```http
GET /api/v1/jobs/{job_id}
```

Check the status of a conversion job.

**Response (200 OK):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "COMPLETED",
  "created_at": "2023-10-27T10:00:00Z",
  "download_url": "http://localhost:8000/api/v1/jobs/a1b2c3d4.../download",
  "files": [
    {
      "filename": "document1.docx",
      "status": "COMPLETED",
      "error_message": null
    },
    {
      "filename": "document2.docx", 
      "status": "FAILED",
      "error_message": "Invalid DOCX format"
    }
  ]
}
```

#### 3. Download Results
```http
GET /api/v1/jobs/{job_id}/download
```

Download the converted PDF files as a ZIP archive.

**Response:** ZIP file containing converted PDFs

## Usage Examples

### Using curl

1. **Submit a job:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/jobs" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@documents.zip"
   ```

2. **Check job status:**
   ```bash
   curl "http://localhost:8000/api/v1/jobs/YOUR_JOB_ID"
   ```

3. **Download results:**
   ```bash
   curl -o converted_files.zip \
        "http://localhost:8000/api/v1/jobs/YOUR_JOB_ID/download"
   ```

### Using Python requests

```python
import requests
import time

# Submit job
with open('documents.zip', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/jobs',
        files={'file': f}
    )
    job_data = response.json()
    job_id = job_data['job_id']

# Poll for completion
while True:
    response = requests.get(f'http://localhost:8000/api/v1/jobs/{job_id}')
    status_data = response.json()
    
    if status_data['status'] == 'COMPLETED':
        # Download results
        response = requests.get(f'http://localhost:8000/api/v1/jobs/{job_id}/download')
        with open('converted_files.zip', 'wb') as f:
            f.write(response.content)
        break
    elif status_data['status'] == 'FAILED':
        print("Job failed!")
        break
    
    time.sleep(5)  # Wait 5 seconds before checking again
```

## Development

### Project Structure

```
bulk-docx-converter/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # FastAPI route handlers
│   │   └── schemas.py         # Pydantic models
│   ├── config/
│   │   ├── __init__.py
│   │   ├── database.py        # Database configuration
│   │   └── settings.py        # Application settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py          # SQLAlchemy models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── converter.py       # DOCX to PDF conversion
│   │   ├── file_utils.py      # File handling utilities
│   │   └── logging_config.py  # Logging configuration
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py      # Celery configuration
│   │   └── tasks.py           # Celery tasks
│   ├── __init__.py
│   └── main.py                # FastAPI application
├── alembic/                   # Database migrations
├── storage/                   # File storage (created by Docker)
├── tests/                     # Test files
├── .env.example               # Environment variables template
├── docker-compose.yml         # Docker services configuration
├── Dockerfile                 # Docker image definition
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

### Running in Development Mode

1. **Start the services:**
   ```bash
   docker compose up --build
   ```

2. **View logs:**
   ```bash
   # All services
   docker compose logs -f
   
   # Specific service
   docker compose logs -f api
   docker compose logs -f worker
   ```

3. **Access service containers:**
   ```bash
   # API container
   docker compose exec api bash
   
   # Worker container
   docker compose exec worker bash
   ```

### Database Migrations

The application uses Alembic for database migrations:

```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec api alembic upgrade head

# View migration history
docker-compose exec api alembic history
```

### Monitoring

- **Celery Flower**: http://localhost:5555 (Task monitoring)
- **Application Logs**: Available in container logs and `/app/storage/app.log`
- **Error Logs**: Available in `/app/storage/error.log`

## Configuration

### Environment Variables

Key configuration options (see `.env.example` for complete list):

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_FILE_SIZE` | 52428800 | Maximum file size in bytes (50MB) |
| `MAX_FILES_PER_JOB` | 1000 | Maximum files per conversion job |
| `LIBREOFFICE_TIMEOUT` | 300 | Conversion timeout in seconds |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection string |
| `REDIS_URL` | redis://... | Redis connection string |

### Scaling Workers

To handle more concurrent conversions, scale the worker service:

```bash
docker-compose up --scale worker=4
```

## Production Deployment

### Security Considerations

1. **Change default passwords** in `docker-compose.yml`
2. **Set strong SECRET_KEY** in environment variables
3. **Configure CORS origins** in `app/main.py`
4. **Use HTTPS** with a reverse proxy (nginx, traefik)
5. **Implement rate limiting**
6. **Regular security updates**

### Performance Tuning

1. **Worker Scaling**: Scale workers based on CPU cores
2. **Database Connection Pool**: Tune PostgreSQL connections
3. **Redis Configuration**: Optimize Redis for your workload
4. **File Cleanup**: Implement automated cleanup of old files
5. **Monitoring**: Add proper monitoring (Prometheus, Grafana)

### Example Production docker-compose.yml

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:secure_pass@db:5432/docx_converter
      - SECRET_KEY=your-very-secure-secret-key
    # Remove port exposure (nginx will proxy)
    depends_on:
      - db
      - redis

  worker:
    build: .
    scale: 4  # Multiple workers for better performance
    # ... other configuration
```

## Troubleshooting

### Common Issues

1. **"Connection refused" errors**
   - Wait for all services to fully start
   - Check `docker-compose logs` for service status

2. **LibreOffice conversion failures**
   - Ensure DOCX files are valid
   - Check worker logs for specific errors
   - Verify sufficient disk space

3. **File upload errors**
   - Check file size limits
   - Verify ZIP file format
   - Ensure files are valid DOCX documents

4. **Database connection errors**
   - Wait for PostgreSQL to fully initialize
   - Check database credentials in environment

### Performance Issues

1. **Slow conversions**
   - Scale worker processes: `docker-compose up --scale worker=N`
   - Check available system resources
   - Monitor worker logs for bottlenecks

2. **High memory usage**
   - LibreOffice can be memory-intensive
   - Consider reducing worker concurrency
   - Monitor system resources

### Logs and Debugging

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f db
docker-compose logs -f redis

# Enter container for debugging
docker-compose exec api bash
docker-compose exec worker bash

# Check database
docker-compose exec db psql -U converter_user -d docx_converter

# Check Redis
docker-compose exec redis redis-cli
```

## API Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 202 | Job accepted and queued |
| 400 | Bad request (invalid file format, etc.) |
| 404 | Job not found |
| 413 | File too large |
| 422 | Validation error |
| 500 | Internal server error |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation at `/docs`
