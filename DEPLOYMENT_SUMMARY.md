# Quick Deployment Summary for Render.com

## Prerequisites
- GitHub repository with this code
- Render.com account (free)

## Quick Deploy Commands

### 1. Push to GitHub
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### 2. Create Services on Render Dashboard

#### PostgreSQL Database
- Name: `docx-converter-db`
- Database: `docx_converter`
- Plan: Free

#### Redis Database
- Name: `docx-converter-redis`
- Plan: Free

#### Web Service (API)
- Name: `docx-converter-api`
- Build Command: `./build.sh`
- Start Command: `python -m app.main`
- Environment Variables:
  ```
  DATABASE_URL = [from PostgreSQL service]
  REDIS_URL = [from Redis service]
  CELERY_BROKER_URL = [same as REDIS_URL]
  CELERY_RESULT_BACKEND = [same as REDIS_URL]
  API_HOST = 0.0.0.0
  STORAGE_PATH = /tmp/storage
  ```

#### Background Worker
- Name: `docx-converter-worker`
- Build Command: `./build.sh`
- Start Command: `celery -A app.workers.celery_app worker --loglevel=info --concurrency=2`
- Same environment variables as API

## Test Deployment
```bash
python test_production.py https://your-app-name.onrender.com
```

## Expected URLs
- API: `https://docx-converter-api.onrender.com`
- Docs: `https://docx-converter-api.onrender.com/docs`

## Notes
- Free tier services sleep after 15 minutes
- First request may take 30+ seconds to wake up
- Files are stored in `/tmp` (not persistent)

For detailed instructions, see [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
