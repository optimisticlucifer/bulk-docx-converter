# Render.com Docker Deployment Guide

This guide will walk you through deploying the Bulk DOCX to PDF Converter on Render.com using Docker.

## Prerequisites

1. A Render.com account
2. Your code pushed to a GitHub repository
3. The existing PostgreSQL and Redis databases we created earlier:
   - PostgreSQL: `dpg-d2tcequuk2gs73co9mk0-a` (docx-converter-db)
   - Redis: `red-d2tcg1ur433s73d9fung` (docx-converter-redis)

## Docker Files

We have prepared optimized Docker files for Render deployment:
- `Dockerfile.web` - FastAPI web service
- `Dockerfile.worker` - Celery worker service

## Deployment Steps

### Step 1: Deploy the FastAPI Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository: `https://github.com/optimisticlucifer/bulk-docx-converter`
4. Configure the service:

   **Basic Settings:**
   - Name: `docx-converter-api`
   - Region: `Oregon (US West)`
   - Branch: `main` (or `master`)
   - Runtime: `Docker`
   - Dockerfile Path: `Dockerfile.web`

   **Environment Variables:**
   ```
   DATABASE_URL=postgresql://converter_user@dpg-d2tcequuk2gs73co9mk0-a-oregon-postgres.render.com:5432/docx_converter
   REDIS_URL=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
   CELERY_BROKER_URL=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
   CELERY_RESULT_BACKEND=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
   UPLOAD_DIR=/tmp/uploads
   CONVERTED_DIR=/tmp/converted
   MAX_FILE_SIZE_MB=50
   MAX_FILES_PER_BATCH=20
   CORS_ORIGINS=*
   ENVIRONMENT=production
   ```

   **Advanced Settings:**
   - Build Plan: Free
   - Auto-Deploy: Yes
   - Health Check Path: `/api/v1/health`

5. Click "Create Web Service"

### Step 2: Deploy the Celery Worker Service

1. In Render Dashboard, click "New +" → "Private Service"
2. Connect the same GitHub repository
3. Configure the service:

   **Basic Settings:**
   - Name: `docx-converter-worker`
   - Region: `Oregon (US West)`
   - Branch: `main` (or `master`)
   - Runtime: `Docker`
   - Dockerfile Path: `Dockerfile.worker`

   **Environment Variables:** (Same as web service)
   ```
   DATABASE_URL=postgresql://converter_user@dpg-d2tcequuk2gs73co9mk0-a-oregon-postgres.render.com:5432/docx_converter
   REDIS_URL=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
   CELERY_BROKER_URL=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
   CELERY_RESULT_BACKEND=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
   UPLOAD_DIR=/tmp/uploads
   CONVERTED_DIR=/tmp/converted
   MAX_FILE_SIZE_MB=50
   MAX_FILES_PER_BATCH=20
   ENVIRONMENT=production
   ```

   **Advanced Settings:**
   - Build Plan: Free
   - Auto-Deploy: Yes

4. Click "Create Private Service"

### Step 3: Verify Deployment

1. Wait for both services to deploy (this may take 5-10 minutes)
2. Check the web service logs for any errors
3. Test the API endpoints:

   **Health Check:**
   ```bash
   curl https://your-service-url.onrender.com/api/v1/health
   ```

   **API Documentation:**
   Visit: `https://your-service-url.onrender.com/docs`

### Step 4: Test the Complete Workflow

1. **Create a test ZIP file** with a few DOCX files
2. **Upload the ZIP file:**
   ```bash
   curl -X POST "https://your-service-url.onrender.com/api/v1/jobs" \
        -H "accept: application/json" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@test.zip"
   ```
3. **Check job status:**
   ```bash
   curl "https://your-service-url.onrender.com/api/v1/jobs/{job_id}"
   ```
4. **Download converted files when ready:**
   ```bash
   curl "https://your-service-url.onrender.com/api/v1/jobs/{job_id}/download" -o converted.zip
   ```

## Important Notes

### File Storage Limitations
- Render's free tier doesn't support persistent storage
- Files are stored in `/tmp` and may be lost on container restarts
- For production use, consider integrating cloud storage (AWS S3, etc.)

### Performance Considerations
- Free tier has limited CPU and memory
- Services may sleep after 15 minutes of inactivity
- Consider upgrading to paid plans for production workloads

### Monitoring
- Use Render's built-in logs and metrics
- Both services should show healthy status in the dashboard
- Monitor the worker service for task processing

### Database Passwords
The connection strings above use the internal Render hostnames. Render will automatically inject the actual passwords at runtime.

## Troubleshooting

### Common Issues:
1. **Build Failures:** Check the build logs for missing dependencies
2. **Database Connection:** Verify the database URLs and ensure databases are running
3. **Worker Not Processing:** Check Redis connection and worker service logs
4. **File Upload Errors:** Verify file size limits and directory permissions

### Useful Commands:
```bash
# Check service status
curl https://your-service-url.onrender.com/api/v1/health

# View service logs in Render Dashboard
# Navigate to your service → Logs tab

# Manual restart if needed
# Go to service → Settings → Manual Deploy
```

## Next Steps

After successful deployment:
1. Test with various file types and sizes
2. Monitor performance and error rates
3. Consider upgrading to paid plans for better performance
4. Implement cloud storage for file persistence
5. Set up monitoring and alerting
6. Configure custom domain if needed

Your bulk DOCX to PDF converter is now live on Render! 🎉

## Quick Summary for Manual Deployment

**Services to create:**
1. **Web Service** (`docx-converter-api`)
   - Repository: `https://github.com/optimisticlucifer/bulk-docx-converter`
   - Runtime: Docker
   - Dockerfile: `Dockerfile.web`
   - Health Check: `/api/v1/health`

2. **Private Service** (`docx-converter-worker`)
   - Same repository
   - Runtime: Docker
   - Dockerfile: `Dockerfile.worker`

**Environment Variables for both services:**
```
DATABASE_URL=postgresql://converter_user@dpg-d2tcequuk2gs73co9mk0-a-oregon-postgres.render.com:5432/docx_converter
REDIS_URL=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
CELERY_BROKER_URL=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
CELERY_RESULT_BACKEND=redis://red-d2tcg1ur433s73d9fung-oregon-redis.render.com:6379
UPLOAD_DIR=/tmp/uploads
CONVERTED_DIR=/tmp/converted
MAX_FILE_SIZE_MB=50
MAX_FILES_PER_BATCH=20
CORS_ORIGINS=*
ENVIRONMENT=production
```
