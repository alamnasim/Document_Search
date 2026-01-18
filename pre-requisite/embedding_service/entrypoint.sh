#!/bin/bash
set -e

echo "=========================================="
echo "  Embedding API Service - Starting"
echo "=========================================="

# Display environment information
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo ""

# Check if model cache exists
if [ -d "/root/.cache/torch/sentence_transformers" ]; then
    echo " Model cache found"
else
    echo "  Model cache not found, will download on first request"
fi

echo ""
echo "🚀 Starting FastAPI server..."
echo "📡 API will be available at: http://0.0.0.0:8001"
echo "📚 Swagger docs at: http://0.0.0.0:8001/docs"
echo ""

# Start the FastAPI application with uvicorn
exec uvicorn app:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers "${WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}" \
    --access-log \
    --no-use-colors
