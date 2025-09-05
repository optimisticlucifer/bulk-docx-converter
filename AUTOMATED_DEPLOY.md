# Automated Deployment to Render.com

This guide shows you how to deploy your bulk DOCX to PDF converter to Render.com with a single command.

## Prerequisites

1. **GitHub Repository**: Your code must be in a GitHub repository
2. **Render Account**: Free account at [render.com](https://render.com)
3. **Render API Key**: Required for automated deployment

## Step 1: Get Your Render API Key

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on your profile (top right)
3. Select "Account Settings"
4. Go to "API Keys" tab
5. Click "Create API Key"
6. Give it a name (e.g., "Deployment Key")
7. Copy the generated API key (keep it secure!)

## Step 2: Push Your Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit for Render deployment"

# Add your GitHub repository as origin
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

## Step 3: Run the Automated Deployment

```bash
python deploy.py --api-key YOUR_RENDER_API_KEY --repo-url https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
```

### Example:
```bash
python deploy.py --api-key rnd_abc123def456 --repo-url https://github.com/johndoe/bulk-docx-converter
```

## What the Script Does

The deployment script automatically:

1. **Creates PostgreSQL Database** (`docx-converter-db`)
   - Free tier (512MB)
   - Creates database and user

2. **Creates Redis Database** (`docx-converter-redis`)
   - Free tier (25MB)
   - For message queue

3. **Deploys Web Service** (`docx-converter-api`)
   - FastAPI application
   - Automatic HTTPS
   - Custom domain available

4. **Deploys Worker Service** (`docx-converter-worker`)
   - Celery background workers
   - Handles document conversion

5. **Configures All Environment Variables**
   - Database connections
   - Redis connections
   - Storage paths

## Expected Output

```
Bulk DOCX to PDF Converter - Render.com Deployment
============================================================
Repository: https://github.com/username/repo
Timeout: 600 seconds

[2025-01-05 12:00:00] INFO: Starting deployment of bulk DOCX to PDF converter...
[2025-01-05 12:00:01] INFO: Step 1: Creating PostgreSQL database...
[2025-01-05 12:00:02] INFO: PostgreSQL database created with ID: pserv-abc123
[2025-01-05 12:01:30] INFO: PostgreSQL is ready!
[2025-01-05 12:01:31] INFO: Step 2: Creating Redis database...
[2025-01-05 12:01:32] INFO: Redis database created with ID: redis-def456
[2025-01-05 12:02:15] INFO: Redis is ready!
[2025-01-05 12:02:16] INFO: Step 3: Creating FastAPI web service...
[2025-01-05 12:02:17] INFO: Web service created with ID: srv-ghi789
[2025-01-05 12:02:18] INFO: Step 4: Creating Celery worker service...
[2025-01-05 12:02:19] INFO: Worker service created with ID: srv-jkl012
[2025-01-05 12:02:20] INFO: Step 5: Waiting for web service to be ready...
[2025-01-05 12:05:45] INFO: Web Service is ready!

============================================================
SUCCESS: DEPLOYMENT COMPLETED SUCCESSFULLY!
============================================================
SUCCESS: PostgreSQL Database ID: pserv-abc123
SUCCESS: Redis Database ID: redis-def456
SUCCESS: Web Service ID: srv-ghi789
SUCCESS: Worker Service ID: srv-jkl012
SUCCESS: API URL: https://docx-converter-api.onrender.com
SUCCESS: API Docs: https://docx-converter-api.onrender.com/docs
SUCCESS: 
SUCCESS: Test your deployment with:
SUCCESS: python test_production.py https://docx-converter-api.onrender.com
SUCCESS: 
SUCCESS: Note: Services may take a few minutes to fully initialize
SUCCESS: Free tier services will sleep after 15 minutes of inactivity

Deployment completed successfully!
```

## Test Your Deployment

Once deployment completes, test it:

```bash
python test_production.py https://docx-converter-api.onrender.com
```

## Deployment Time

- **Total Time**: 5-10 minutes
- **Database Setup**: 1-2 minutes each
- **Service Deployment**: 3-5 minutes
- **First Build**: May take longer due to LibreOffice installation

## Troubleshooting

### Common Issues:

1. **Invalid API Key**:
   ```
   ERROR: API request failed: 401 Client Error: Unauthorized
   ```
   - Check your API key is correct
   - Ensure it's not expired

2. **Repository Access**:
   ```
   ERROR: Failed to create web service: Repository not found
   ```
   - Ensure repository is public or Render has access
   - Check the repository URL is correct

3. **Build Failures**:
   - Check build logs in Render dashboard
   - Ensure `build.sh` has execute permissions
   - Verify all dependencies are in `requirements.txt`

### Check Service Status:

```bash
# View deployment logs
curl -H "Authorization: Bearer YOUR_API_KEY" \
     "https://api.render.com/v1/services/srv-YOUR_SERVICE_ID"
```

## Cost

**Total Cost: FREE** (using free tier for all services)

- PostgreSQL: Free (512MB)
- Redis: Free (25MB)
- Web Service: Free (750 hours/month)
- Worker: Free (750 hours/month)

## Post-Deployment

After successful deployment:

1. **Save Service IDs**: Keep track of your service IDs for future management
2. **Monitor Usage**: Check Render dashboard for resource usage
3. **Set Up Monitoring**: Consider upgrading for better monitoring
4. **Custom Domain**: Add your own domain if needed

## Advanced Options

### Customize Deployment:

```bash
# Use different timeout
python deploy.py --api-key YOUR_KEY --repo-url YOUR_REPO --timeout 900

# Deploy to specific region (oregon, frankfurt, singapore)
# (This requires modifying the script)
```

### Environment Variables:

The script automatically sets these variables:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection  
- `CELERY_BROKER_URL`: Celery message broker
- `CELERY_RESULT_BACKEND`: Celery result backend
- `API_HOST`: Server host (0.0.0.0)
- `STORAGE_PATH`: File storage path (/tmp/storage)

## Support

If you encounter issues:
1. Check the Render dashboard for service logs
2. Verify your repository is accessible
3. Ensure your API key has proper permissions
4. Review the build logs for any errors

Your bulk DOCX to PDF converter will be live and ready to handle document conversions!
