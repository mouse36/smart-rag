# SunnyMentor Backend - Production Deployment

This is the production deployment version of the SunnyMentor backend, optimized for deployment on Railway with Nixpacks.

## Structure

- `app.py` - Main Flask application
- `config.py` - Configuration settings
- `deepseek_client.py` - DeepSeek API client
- `jsonbin_client.py` - JSONBin API client for data storage
- `vector_search.py` - Vector search functionality
- `run.py` - Application runner
- `setup_check.py` - Setup verification
- `knowledge_base/` - Knowledge base documents
- `tone-context-*.txt` - Tone context files
- `main.py` - Railway entry point
- `nixpacks.toml` - Nixpacks configuration
- `Procfile` - Railway process file
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python runtime specification

## Deployment

This folder is designed to be deployed directly to Railway. The `main.py` file serves as the entry point for the Railway deployment.

## Environment Variables

Make sure to set the following environment variables in your Railway project:
- `DEEPSEEK_API_KEY`
- `JSONBIN_API_KEY`
- `JSONBIN_BIN_ID`
- `JWT_SECRET_KEY`

## Local Development

For local development, use the `development` folder which contains both frontend and backend components.
