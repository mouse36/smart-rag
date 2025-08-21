# Memory Optimization Guide

## Problem
The application was running out of memory (over 512MB) during deployment on Render due to the sentence transformer model and vector search initialization.

## Solution
We've implemented several memory optimization strategies:

### 1. Memory-Optimized Vector Search
- Uses a smaller sentence transformer model (`all-MiniLM-L6-v2`)
- Implements lazy loading (model only loaded when first needed)
- Processes knowledge base in smaller batches
- Monitors memory usage and falls back to keyword search if needed
- Uses CPU-only PyTorch for smaller memory footprint

### 2. Environment Variables for Memory Optimization
Set these environment variables in your deployment:

```bash
USE_SMALLER_MODEL=True
MAX_MEMORY_MB=400
LAZY_LOAD_MODEL=True
CHUNK_SIZE=300
CHUNK_OVERLAP=30
EMBEDDINGS_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=384
```

### 3. Requirements Optimization
- Uses CPU-only PyTorch (`torch==2.8.0+cpu`)
- Added `psutil` for memory monitoring
- Separated core requirements from AI/ML requirements

### 4. Fallback Strategy
If vector search fails due to memory constraints:
- Falls back to keyword-based search
- Still provides relevant results from knowledge base
- Maintains RAG functionality

## Deployment Options

### Option 1: Use Memory-Optimized Script
```bash
python deploy_memory_optimized.py
```

### Option 2: Set Environment Variables
Set the memory optimization environment variables in your deployment platform and run:
```bash
python run.py
```

### Option 3: Use Core Requirements Only (No Vector Search)
If memory is still insufficient:
```bash
pip install -r requirements-core.txt
API_CALLS_ENABLED=false python run.py
```

## Monitoring
The application will log memory usage and automatically fall back to keyword search if needed. Check logs for:
- Available memory
- Model loading status
- Search type being used (vector vs keyword)

## Expected Memory Usage
- **Startup**: ~100-200MB (without model loaded)
- **First search**: +90MB (model loading)
- **Total peak**: ~300-400MB (well under 512MB limit)
