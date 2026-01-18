# Embedding API Docker Service

## 📁 Directory Structure

```
embedding_service/
├── app.py                 # FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Multi-stage Docker build
├── entrypoint.sh         # Container startup script
├── docker-compose.yml    # Docker Compose configuration
├── .dockerignore         # Files to ignore in build
└── README.md            # This file
```

## 🚀 Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
cd embedding_service

# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Option 2: Using Docker Commands

```bash
cd embedding_service

# Build the image
docker build -t embedding-api:latest .

# Run the container
docker run -d \
  --name embedding_service \
  -p 8001:8001 \
  -e WORKERS=1 \
  -e LOG_LEVEL=info \
  embedding-api:latest

# View logs
docker logs -f embedding_service

# Stop and remove
docker stop embedding_service
docker rm embedding_service
```

## 🧪 Testing the Service

```bash
# Wait for service to be ready (takes ~10-15 seconds)
sleep 15

# Health check
curl http://localhost:8001/health

# Test embedding
curl -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test document",
    "normalize": true
  }'

# Batch embedding
curl -X POST http://localhost:8001/batch-embed \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Document 1", "Document 2", "Document 3"],
    "normalize": true
  }'

# Similarity test
curl -X POST "http://localhost:8001/similarity?text1=machine%20learning&text2=AI"
```

## 📊 Container Details

### Image Size
- **Without optimization**: ~2.5 GB (with CUDA)
- **With CPU optimization**: ~800 MB - 1 GB
- **Multi-stage build**: Further reduces size

### Resource Usage
- **Memory**: ~500 MB idle, ~1 GB under load
- **CPU**: Minimal when idle
- **Startup time**: ~10-15 seconds (includes model loading)

### Ports
- **8001**: FastAPI service

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKERS` | 1 | Number of uvicorn workers |
| `LOG_LEVEL` | info | Log level (debug, info, warning, error) |

### Docker Compose Options

Edit `docker-compose.yml` to customize:

```yaml
environment:
  - WORKERS=2              # Increase for production
  - LOG_LEVEL=debug       # More verbose logging

deploy:
  resources:
    limits:
      cpus: '4.0'          # Increase CPU limit
      memory: 4G           # Increase memory limit
```

## 🏗️ Build Optimization

The Dockerfile uses **multi-stage build** for optimization:

1. **Builder Stage**: 
   - Installs dependencies
   - Pre-downloads model
   - Compiles Python packages

2. **Runtime Stage**:
   - Only copies necessary files
   - Minimal base image
   - Non-root user for security

### Key Features:
-  CPU-only PyTorch (no CUDA)
-  Pre-downloaded model in image
-  Multi-stage build
-  Non-root user
-  Health checks
-  Resource limits

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/embed` | POST | Single text embedding |
| `/batch-embed` | POST | Batch embeddings |
| `/similarity` | POST | Compare similarity |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc documentation |

## 🔍 Monitoring

### Check Container Status
```bash
docker-compose ps
```

### View Logs
```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Check Resource Usage
```bash
docker stats embedding_service
```

### Execute Commands Inside Container
```bash
docker-compose exec embedding-api bash
```

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs embedding-api

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Health check failing
```bash
# Check if model is loaded
docker-compose logs embedding-api | grep "Model loaded"

# Wait longer (model loading takes time)
sleep 30
curl http://localhost:8001/health
```

### Port already in use
```bash
# Change port in docker-compose.yml
ports:
  - "8002:8001"  # Use 8002 instead
```

### Out of memory
```bash
# Increase memory limit in docker-compose.yml
memory: 4G  # Increase from 2G
```

## 🚀 Production Deployment

### Increase Workers
```yaml
environment:
  - WORKERS=4  # Match CPU cores
```

### Add Reverse Proxy (nginx)
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - embedding-api
```

### Enable HTTPS
```bash
# Use Traefik or nginx with Let's Encrypt
# See: https://doc.traefik.io/traefik/
```

### Monitoring with Prometheus
```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

## 📦 Pushing to Docker Registry

```bash
# Tag the image
docker tag embedding-api:latest your-registry/embedding-api:latest

# Push to registry
docker push your-registry/embedding-api:latest

# Pull and run on another machine
docker pull your-registry/embedding-api:latest
docker run -d -p 8001:8001 your-registry/embedding-api:latest
```

## 🔄 Update and Restart

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build

# Or without downtime (with multiple workers)
docker-compose up -d --no-deps --build embedding-api
```

## 🧹 Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove images
docker rmi embedding-api:latest

# Clean up everything
docker system prune -a
```

## 📝 Notes

1. **First startup takes longer** (~15-30s) as the model loads
2. **Model is cached** in the image, so subsequent starts are faster
3. **Memory usage** increases during processing, plan accordingly
4. **CPU-only** build ensures compatibility across different hardware
5. **Non-root user** improves security

##  Next Steps

- [ ] Add authentication (JWT, API keys)
- [ ] Implement rate limiting
- [ ] Add metrics endpoint (Prometheus)
- [ ] Set up CI/CD pipeline
- [ ] Configure auto-scaling (Kubernetes)
- [ ] Add caching layer (Redis)

## 📄 License
MIT
