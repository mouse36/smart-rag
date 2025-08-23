# Railway Deployment Guide

## Backend Deployment on Railway

### 1. Prerequisites
- Railway account (https://railway.app)
- GitHub repository with your code
- Environment variables configured

### 2. Deploy Backend

1. **Connect to Railway:**
   - Go to Railway dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Configure the Service:**
   - Railway will automatically detect it's a Python project
   - Set the root directory to `backend/` (if your backend is in a subdirectory)
   - The start command should be: `python run.py`

3. **Set Environment Variables:**
   In Railway dashboard, go to Variables tab and set:
   ```
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

4. **Deploy:**
   - Railway will automatically build and deploy your application
   - Monitor the logs for any errors

### 3. Get Railway URL

After deployment, Railway will provide a URL like:
`https://your-app-name.railway.app`

### 4. Update Frontend Configuration

1. **Update config.js:**
   In `frontend/js/config.js`, replace the production baseUrl:
   ```javascript
   baseUrl: 'https://your-app-name.railway.app', // Your actual Railway URL
   ```

2. **Test the Connection:**
   - Deploy your frontend to Siteground
   - Test the health check endpoint: `https://your-app-name.railway.app/health`
   - Test authentication endpoints

### 5. CORS Configuration

The backend already has CORS enabled with:
```python
CORS(app)  # Enable CORS for frontend integration
```

This allows requests from any origin. For production, you might want to restrict it to your specific domain.

### 6. Health Check

Railway will automatically check the `/health` endpoint. Make sure it returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 7. Monitoring

- Check Railway logs for any errors
- Monitor the health check endpoint
- Set up alerts for downtime

### 8. Troubleshooting

**Common Issues:**

1. **Port Issues:**
   - Ensure `HOST=0.0.0.0` and `PORT=5000` are set
   - Railway will automatically assign a port if needed

2. **Environment Variables:**
   - Make sure all required environment variables are set
   - Check that API keys are valid

3. **Dependencies:**
   - Ensure `requirements.txt` is in the backend directory
   - Railway will automatically install dependencies

4. **Start Command:**
   - Verify the start command is `python run.py`
   - Check that `run.py` exists and is executable

### 9. Frontend Deployment on Siteground

1. Upload all frontend files to your Siteground hosting
2. Ensure the `config.js` file has the correct Railway URL
3. Test all functionality:
   - Health checks
   - Authentication
   - Chat functionality
   - Payment processing

### 10. SSL/HTTPS

Railway automatically provides SSL certificates. Make sure your frontend is also served over HTTPS to avoid mixed content issues.

### 11. Performance Optimization

- Enable lazy loading for the vector search engine
- Use lightweight embeddings model
- Monitor memory usage
- Set appropriate timeouts

### 12. Security

- Use strong JWT secrets
- Keep API keys secure
- Enable Firebase authentication
- Use HTTPS for all communications
