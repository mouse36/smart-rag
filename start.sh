#!/bin/bash
set -e

echo "🚀 Starting SunnyMentor Backend on Render..."

# Change to backend directory
cd backend

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Set default environment variables for Render
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-10000}
export DEBUG=${DEBUG:-False}

echo "🌐 Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Debug: $DEBUG"

# Start the Flask application
echo "🎯 Starting Flask application..."
python run.py
