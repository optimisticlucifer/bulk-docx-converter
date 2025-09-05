# Deploying Bulk DOCX to PDF Converter on Render.com

This guide will help you deploy the bulk DOCX to PDF conversion service on Render.com with all required components.

## 📋 Prerequisites

1. GitHub/GitLab account with your code repository
2. Render.com account (free tier available)
3. Basic understanding of environment variables

## 🏗️ Architecture on Render

Since Render doesn't support Docker Compose, we'll deploy individual services:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Service   │    │   Worker Service│    │  PostgreSQL     │
│   (FastAPI)     │◄──►│   (Celery)      │    │  (Managed DB)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │  (Managed DB)   │
                    └─────────────────┘
```

##  Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Push your code to GitHub/GitLab** (if not already done):
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

### Step 2: Create Database Services

First, we'll create the required databases:

#### 2.1 Create PostgreSQL Database
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "PostgreSQL"
3. Configure:
   - Name: `docx-converter-db`
   - Database Name: `docx_converter`
   - User: `converter_user`
   - Plan: Free
4. Click "Create Database"
5. Wait for the database to be ready and note the connection string

#### 2.2 Create Redis Database
1. Click "New" → "Redis"
2. Configure:
   - Name: `docx-converter-redis`
   - Plan: Free
3. Click "Create Redis"
4. Wait for Redis to be ready and note the connection string

### Step 3: Deploy the Web Service (FastAPI API)

1. Click "New" → "Web Service"
2. Connect your GitHub/GitLab repository
3. Configure:
   - Name: `docx-converter-api`
   - Environment: `Python 3`
   - Build Command: `./build.sh`
   - Start Command: `python -m app.main`
   - Plan: Free

4. Add Environment Variables:
   ```
   DATABASE_URL = [Copy from your PostgreSQL service]
   REDIS_URL = [Copy from your Redis service]
   CELERY_BROKER_URL = [Same as REDIS_URL]
   CELERY_RESULT_BACKEND = [Same as REDIS_URL]
   API_HOST = 0.0.0.0
   STORAGE_PATH = /tmp/storage
   ```

5. Click "Create Web Service"

### Step 4: Deploy the Worker Service (Celery)

1. Click "New" → "Background Worker"
2. Connect the same repository
3. Configure:
   - Name: `docx-converter-worker`
   - Environment: `Python 3`
   - Build Command: `./build.sh`
   - Start Command: `celery -A app.workers.celery_app worker --loglevel=info --concurrency=2`
   - Plan: Free

4. Add the same Environment Variables as the web service
5. Click "Create Background Worker"

### Step 5: Test Your Deployment

Once all services are deployed:

1. Your API will be available at: `https://docx-converter-api.onrender.com`
2. Test the service:
   ```bash
   curl https://docx-converter-api.onrender.com/
   ```

3. Access API documentation at: `https://docx-converter-api.onrender.com/docs`

## Environment Variables Reference

Here are all the environment variables you need to set:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | From PostgreSQL service | Database connection string |
| `REDIS_URL` | From Redis service | Redis connection string |
| `CELERY_BROKER_URL` | Same as REDIS_URL | Celery message broker |
| `CELERY_RESULT_BACKEND` | Same as REDIS_URL | Celery result backend |
| `API_HOST` | `0.0.0.0` | Host to bind the API server |
| `STORAGE_PATH` | `/tmp/storage` | File storage path |

## Important Notes

### Free Tier Limitations
- Web services sleep after 15 minutes of inactivity
- 750 hours per month of runtime
- Limited CPU and memory
- No persistent disk storage (files stored in `/tmp`)

### Production Considerations

1. **Persistent Storage**: Render's free tier doesn't provide persistent storage. Consider:
   - Upgrading to a paid plan with persistent disks
   - Using external storage (AWS S3, Google Cloud Storage)

2. **Scaling**: For production:
   - Use paid plans for better performance
   - Scale workers based on load
   - Consider using separate Redis instances for different purposes

3. **Monitoring**: Set up monitoring for:
   - Service health
   - Queue length
   - Conversion success rates

## Manual Deployment Steps

If you prefer manual setup over the `render.yaml` file:

### Step A: Prepare Repository
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### Step B: Create Services One by One

1. **PostgreSQL**: New → PostgreSQL → Configure as above
2. **Redis**: New → Redis → Configure as above  
3. **Web Service**: New → Web Service → Configure as above
4. **Worker**: New → Background Worker → Configure as above

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check build logs for missing dependencies
   - Ensure `build.sh` has execute permissions
   - Verify all Python packages are in `requirements.txt`

2. **Database Connection Errors**:
   - Verify `DATABASE_URL` is correctly set
   - Check if database is ready and accessible
   - Ensure database tables are created

3. **Worker Not Processing Jobs**:
   - Check worker logs for Redis connection issues
   - Verify `CELERY_BROKER_URL` matches `REDIS_URL`
   - Ensure worker service is running

4. **LibreOffice Issues**:
   - Verify LibreOffice is installed in build script
   - Check conversion logs for specific errors
   - Ensure sufficient memory allocation

### Monitoring Commands

Check service status:
```bash
# View logs
render logs --service docx-converter-api
render logs --service docx-converter-worker

# Check service health
curl https://docx-converter-api.onrender.com/
```

## Cost Optimization

### Free Tier Usage
- API + Worker + Database + Redis = Still within free limits
- Monitor your usage in Render dashboard
- Services auto-sleep when inactive

### Upgrade Path
- Start with free tier for testing
- Upgrade API service first for better performance
- Add persistent storage when needed
- Scale workers based on actual usage

## Security Considerations

1. **Environment Variables**: Never commit secrets to your repository
2. **Access Control**: Configure IP restrictions if needed
3. **HTTPS**: Render provides HTTPS by default
4. **Database**: Use strong passwords (auto-generated by Render)

## Support and Resources

- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)
- [FastAPI on Render Guide](https://render.com/docs/deploy-fastapi)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)

Your bulk DOCX to PDF converter should now be successfully deployed on Render!
