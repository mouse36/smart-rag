# SunnyMentor Frontend-Backend Setup Guide

This guide will help you set up the frontend (deployed on Siteground) to connect to the backend (deployed on Railway).

## Overview

- **Frontend**: Deployed on Siteground (static files)
- **Backend**: Deployed on Railway (Python Flask API)
- **Connection**: Cross-origin HTTP requests between the two platforms

## Step 1: Deploy Backend to Railway

### 1.1 Prepare Your Repository

1. Ensure your backend code is in the `backend/` directory
2. Make sure `requirements.txt` is in the backend directory
3. Verify `run.py` is the main entry point

### 1.2 Deploy to Railway

1. Go to [Railway Dashboard](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Set the root directory to `backend/` (if your backend is in a subdirectory)
5. Railway will automatically detect it's a Python project

### 1.3 Configure Environment Variables

In Railway dashboard, go to Variables tab and set:

```bash
HOST=0.0.0.0
PORT=5000
DEBUG=False
API_CALLS_ENABLED=True
DEEPSEEK_API_KEY=your_actual_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_CONTEXT_LENGTH=4000
MAX_RESPONSE_LENGTH=1000
TEMPERATURE=0.7
TOP_P=0.9
FIREBASE_SERVICE_ACCOUNT_KEY=your_firebase_service_account_json
FIREBASE_PROJECT_ID=your_firebase_project_id
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
JWT_SECRET_KEY=your_jwt_secret_key
```

### 1.4 Get Your Railway URL

After deployment, Railway will provide a URL like:
`https://your-app-name.railway.app`

**Note this URL - you'll need it for the frontend configuration.**

## Step 2: Configure Frontend

### 2.1 Update Configuration

1. Open `frontend/js/config.js`
2. Replace the production baseUrl with your Railway URL:

```javascript
// In the getApiConfig() method, update this line:
baseUrl: 'https://your-app-name.railway.app', // Your actual Railway URL
```

### 2.2 Test Configuration Locally

1. Open `frontend/railway-setup.html` in your browser
2. Enter your Railway URL
3. Click "Test Connection" to verify the backend is accessible
4. Click "Test All Endpoints" to verify all API endpoints work

### 2.3 Deploy Frontend to Siteground

1. Upload all frontend files to your Siteground hosting
2. Ensure the `config.js` file has the correct Railway URL
3. Test the connection from your live site

## Step 3: Verify Connection

### 3.1 Health Check

Test the health endpoint:
```bash
curl https://your-app-name.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 3.2 Test from Frontend

1. Open your deployed frontend on Siteground
2. Open browser developer tools (F12)
3. Go to the Network tab
4. Try to log in or use the chat feature
5. Verify requests are going to your Railway URL

### 3.3 Common Issues

#### CORS Errors
- The backend already has CORS enabled
- If you see CORS errors, check that your Railway URL is correct
- Ensure both frontend and backend are using HTTPS

#### Connection Timeout
- Check Railway logs for any errors
- Verify environment variables are set correctly
- Ensure the backend is actually running

#### Authentication Issues
- Verify Firebase configuration
- Check JWT secret key is set
- Ensure all authentication endpoints are working

## Step 4: Production Considerations

### 4.1 SSL/HTTPS
- Railway automatically provides SSL certificates
- Ensure your Siteground hosting also uses HTTPS
- Mixed content (HTTP/HTTPS) can cause issues

### 4.2 Performance
- Monitor Railway logs for performance issues
- Consider enabling lazy loading for the vector search engine
- Set appropriate timeouts in the frontend configuration

### 4.3 Security
- Use strong JWT secrets
- Keep API keys secure
- Consider restricting CORS to your specific domain

## Step 5: Monitoring

### 5.1 Railway Monitoring
- Check Railway dashboard for uptime
- Monitor logs for errors
- Set up alerts for downtime

### 5.2 Frontend Monitoring
- Use browser developer tools to monitor network requests
- Check for JavaScript errors in the console
- Monitor user experience and performance

## Troubleshooting

### Backend Won't Start
1. Check Railway logs
2. Verify all environment variables are set
3. Ensure `requirements.txt` is in the correct location
4. Check that `run.py` exists and is executable

### Frontend Can't Connect
1. Verify Railway URL is correct
2. Check CORS configuration
3. Ensure both services are using HTTPS
4. Test the health endpoint directly

### Authentication Fails
1. Check Firebase configuration
2. Verify JWT secret is set
3. Test authentication endpoints directly
4. Check browser console for errors

### Chat Not Working
1. Verify DeepSeek API key is set
2. Check vector search engine initialization
3. Monitor backend logs for errors
4. Test chat endpoint directly

## Quick Commands

### Test Railway Backend
```bash
# Health check
curl https://your-app-name.railway.app/health

# Test authentication
curl -X POST https://your-app-name.railway.app/auth/validate-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890"}'
```

### Update Frontend Configuration
```javascript
// In browser console on your deployed site:
railwaySetup.updateUrl('https://your-app-name.railway.app');
railwaySetup.testConnection();
```

## Support

If you encounter issues:

1. Check Railway logs first
2. Verify all environment variables are set
3. Test endpoints directly with curl
4. Check browser console for frontend errors
5. Ensure both services are using HTTPS

## Files Modified

The following files were created/modified for this setup:

- `frontend/js/config.js` - New configuration system
- `frontend/js/railway-setup.js` - Railway connection utility
- `frontend/railway-setup.html` - Setup page
- `backend/railway.json` - Railway deployment configuration
- `backend/deploy-railway.md` - Detailed deployment guide
- Updated all frontend files to use the new configuration system
