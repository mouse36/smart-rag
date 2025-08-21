# Railway Deployment Guide

This guide covers deploying the SunnyMentor application to Railway using Nixpacks.

## Project Structure

The project has been restructured to have all backend files in the root directory:

```
sunnymentor/
├── app.py              # Main Flask application
├── run.py              # Startup script
├── main.py             # Nixpacks entry point
├── config.py           # Configuration
├── vector_search.py    # Vector search engine
├── deepseek_client.py  # DeepSeek API client
├── cache_manager.py    # Cache management
├── jsonbin_client.py   # JSONBin client
├── knowledge_base/     # Knowledge base files
├── cache/              # Cache directory
├── requirements.txt    # Python dependencies
├── nixpacks.toml       # Nixpacks configuration
├── Procfile            # Railway process file
├── runtime.txt         # Python runtime version
└── README.md           # Project documentation
```

## Deployment Files

### nixpacks.toml
- **Purpose**: Nixpacks configuration for Railway deployment
- **Key Changes**: 
  - Removed references to `backend/` directory
  - Updated start command to use `python run.py`
  - Simplified installation to only use `requirements.txt`

### Procfile
- **Purpose**: Tells Railway how to start the application
- **Key Changes**: 
  - Removed `cd backend` command
  - Updated to use `python run.py`

### main.py
- **Purpose**: Entry point for Nixpacks detection
- **Key Changes**: 
  - Removed backend directory path manipulation
  - Simplified to directly import and run from `run.py`

### run.py
- **Purpose**: Main startup script
- **Key Changes**: 
  - Updated knowledge base path to use root directory
  - Removed backend directory references
  - Updated import paths

## Environment Variables

Set these environment variables in Railway:

### Required
- `DEEPSEEK_API_KEY`: Your DeepSeek API key
- `JWT_SECRET_KEY`: Secret key for JWT tokens

### Optional (with defaults)
- `HOST`: `0.0.0.0` (for Railway)
- `PORT`: `5000` (Railway will override this)
- `DEBUG`: `False` (for production)
- `API_CALLS_ENABLED`: `True` (to enable AI features)

## Deployment Steps

1. **Push to Railway**:
   ```bash
   # Connect your repository to Railway
   # Railway will automatically detect the Python app
   ```

2. **Set Environment Variables**:
   - Go to your Railway project dashboard
   - Navigate to Variables tab
   - Add the required environment variables

3. **Deploy**:
   - Railway will automatically build and deploy using Nixpacks
   - The build process will:
     - Install Python 3.11
     - Install dependencies from `requirements.txt`
     - Start the application using `python run.py`

## Build Process

1. **Setup Phase**: Installs Python 3.11 and pip
2. **Install Phase**: Installs dependencies from `requirements.txt`
3. **Build Phase**: Runs build commands (currently just echo)
4. **Start Phase**: Runs `python run.py`

## Troubleshooting

### Build Failures
- Check that all dependencies are in `requirements.txt`
- Ensure Python version compatibility (3.11)
- Verify file paths are correct for root directory structure

### Runtime Errors
- Check environment variables are set correctly
- Verify `DEEPSEEK_API_KEY` is valid
- Check logs for import errors or missing files

### Memory Issues
- The app is optimized for Railway's 1GB RAM limit
- Uses memory-efficient vector search
- Implements lazy loading for large models

## Monitoring

- Check Railway logs for startup messages
- Monitor memory usage in Railway dashboard
- Verify health endpoint: `https://your-app.railway.app/health`

## Local Testing

To test the deployment configuration locally:

```bash
# Test imports
python3 -c "import app; print('✅ App imports successfully')"

# Test startup script
python3 -c "from run import check_requirements; print('✅ Requirements check passed')"

# Test full startup (will start server)
python3 run.py
```

## Notes

- The application is configured for Railway's environment
- All file paths have been updated for root directory structure
- Memory optimizations are in place for Railway's constraints
- CORS is enabled for frontend integration
- Health check endpoint available at `/health`
