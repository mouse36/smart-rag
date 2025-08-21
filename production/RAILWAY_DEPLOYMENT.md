# Railway Deployment Guide for SunnyMentor

## 🚀 Quick Start

### 1. Prerequisites
- [Railway account](https://railway.app/) (sign up for free)
- [GitHub account](https://github.com/) (to connect your repository)
- DeepSeek API key (get from [DeepSeek](https://platform.deepseek.com/))

### 2. Deploy to Railway

#### Option A: Deploy from GitHub (Recommended)
1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Add Railway deployment configuration"
   git push origin main
   ```

2. **Connect to Railway**:
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your SunnyMentor repository
   - Railway will automatically detect the configuration

#### Option B: Deploy from CLI
1. **Install Railway CLI**:
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and deploy**:
   ```bash
   railway login
   railway init
   railway up
   ```

### 3. Configure Environment Variables

In Railway Dashboard → Your Project → Variables tab, add:

```bash
# Required
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Optional (Railway sets these automatically)
PORT=5000
HOST=0.0.0.0

# Memory Optimization (already set in run_railway.py)
DEBUG=False
API_CALLS_ENABLED=True
LAZY_LOAD_MODEL=True
MAX_MEMORY_MB=400
USE_SMALLER_MODEL=True
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
CHUNK_SIZE=300
CHUNK_OVERLAP=30
```

### 4. Deploy and Monitor

1. **Deploy**: Railway will automatically deploy when you push to GitHub
2. **Monitor**: Check the "Deployments" tab for build logs
3. **Access**: Your app will be available at the generated Railway URL

## 📁 Configuration Files

### `railway.json`
- Specifies deployment settings
- Sets health check endpoint
- Configures restart policy

### `nixpacks.toml`
- Defines Python environment
- Specifies build process
- Sets startup command

### `backend/run_railway.py`
- Railway-optimized startup script
- Memory management settings
- Production-ready configuration

### `backend/requirements-railway.txt`
- Railway-specific dependencies
- Memory-optimized AI/ML libraries
- Production server (gunicorn)

## 🔧 Memory Optimization

Your deployment is optimized for Railway's 1GB RAM limit:

- **Lazy Loading**: AI models only load when needed
- **Smaller Models**: Uses `all-MiniLM-L6-v2` (384 dimensions)
- **CPU-Only**: PyTorch CPU version for smaller footprint
- **Memory Monitoring**: Automatic fallback to keyword search
- **Chunked Processing**: Processes knowledge base in small batches

## 📊 Expected Performance

- **Startup Time**: 30-60 seconds
- **Memory Usage**: 300-400MB peak
- **Response Time**: 2-5 seconds for AI responses
- **Uptime**: 99.9% (Railway's SLA)

## 🚨 Troubleshooting

### Build Failures
1. **Check logs** in Railway Dashboard
2. **Verify requirements**: Ensure all dependencies are in `requirements-railway.txt`
3. **Check Python version**: Railway uses Python 3.9

### Runtime Errors
1. **Memory issues**: Check if `MAX_MEMORY_MB=400` is set
2. **API errors**: Verify `DEEPSEEK_API_KEY` is correct
3. **Import errors**: Check if all packages are installed

### Health Check Failures
1. **Verify endpoint**: `/health` should return 200 OK
2. **Check startup**: Look for "All components ready" in logs
3. **Port binding**: Ensure app binds to `0.0.0.0:PORT`

## 🔄 Updates and Maintenance

### Automatic Deployments
- Push to `main` branch triggers automatic deployment
- Railway builds and deploys in ~2-3 minutes

### Manual Deployments
```bash
railway up
```

### Environment Variable Updates
- Update in Railway Dashboard → Variables
- Redeploy automatically or manually

## 💰 Cost Optimization

### Railway Pricing
- **Free Tier**: 512MB RAM, 1GB disk (may be tight)
- **Hobby Plan**: $5/month - 1GB RAM, 3GB disk (recommended)
- **Pro Plan**: $20/month - 2GB RAM, 10GB disk (if needed)

### Cost-Saving Tips
1. **Use Hobby Plan**: Sufficient for your optimized app
2. **Monitor usage**: Check Railway dashboard for resource usage
3. **Optimize code**: Your app is already memory-optimized

## 🎯 Next Steps

1. **Deploy**: Follow the quick start guide above
2. **Test**: Verify all endpoints work correctly
3. **Monitor**: Check logs and performance
4. **Scale**: Upgrade to Pro plan if needed

## 📞 Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app/)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Project Issues**: Create GitHub issue for project-specific problems
