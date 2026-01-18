# Docker Services Setup Guide

This directory contains all the prerequisite services needed for the Document Search System. Follow the instructions below to build and run each service.

---

## Table of Contents

1. [Elasticsearch](#1-elasticsearch-vector--full-text-search-engine)
2. [Embedding Service](#2-embedding-service)
3. [PaddleOCR](#3-paddleocr)
4. [Vision LM OCR](#4-vision-lm-ocr-ibm-granite)

---

## 1. Elasticsearch (Vector & Full-Text Search Engine)

### Pull and Run (Recommended - Using Official Image)

```bash
# Create Docker network
docker network create elastic

# Pull Elasticsearch image
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.11.3

# Run Elasticsearch (HTTP mode - no authentication)
docker run -d \
   --name es01 \
   --net elastic \
   -p 9200:9200 \
   -m 4GB \
   -e "discovery.type=single-node" \
   -e "xpack.security.enabled=false" \
   -e "ES_JAVA_OPTS=-Xms2g -Xmx2g" \
   -v es_data:/usr/share/elasticsearch/data \
   docker.elastic.co/elasticsearch/elasticsearch:8.11.3
```

### For HTTPS with authentication (Optional):

```bash
# Set xpack.security.enabled=true for HTTPS
docker run -d \
   --name es01 \
   --net elastic \
   -p 9200:9200 \
   -m 4GB \
   -e "discovery.type=single-node" \
   -e "xpack.security.enabled=true" \
   -e "ES_JAVA_OPTS=-Xms2g -Xmx2g" \
   -v es_data:/usr/share/elasticsearch/data \
   docker.elastic.co/elasticsearch/elasticsearch:8.11.3

# Create Certificate Authority
docker exec -it es01 /usr/share/elasticsearch/bin/elasticsearch-certutil ca \
  --out /usr/share/elasticsearch/config/certs/elastic-stack-ca.p12 --pass ""

# Reset/Generate password
docker exec -it es01 /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic
```

### Verify Elasticsearch:

```bash
# Test HTTP endpoint
curl http://localhost:9200

# Expected output:
{
    "name": "59b794dee0d3",
    "cluster_name": "docker-cluster",
    "cluster_uuid": "-jlyAhqNSai8fVRkybkpUQ",
    "version": {
        "number": "8.11.3",
        "build_flavor": "default",
        "build_type": "docker",
        ...
    },
    "tagline": "You Know, for Search"
}
```

### Configure in `.env`:

```bash
ELASTICSEARCH_INDEX=documents_v1
```

---

## 2. Embedding Service

Converts text into 384-dimensional vector embeddings using BGE-small-en-v1.5 model.

### Build the Docker Image

```bash
# Navigate to embedding_service directory
cd embedding_service

# Build the image
docker build -t embedding-service:v0.1 .
```

### Run the Container

```bash
# Run embedding service
docker run -d \
  --name embedding-service \
  -p 8001:8001 \
  embedding-service:v0.1

# Check logs
docker logs -f embedding-service
```

### Alternative: Pull from Docker Hub

```bash
# Pull pre-built image
docker pull nasim0086/embedding-service:v0.1

# Run the container
docker run -d \
  --name embedding-service \
  -p 8001:8001 \
  nasim0086/embedding-service:v0.1
```

### Test the Service

```bash
# Using curl
curl -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-small-en-v1.5",
    "text": "The quick brown fox jumps over the lazy dog."
  }'

# Expected: Array of 384 float values
```

### Configuration

```bash
EMBEDDING_MODEL_NAME=bge-small-en-v1.5
EMBEDDING_ENDPOINT=http://localhost:8001/embed
```

---

## 3. PaddleOCR

Fast CPU-based OCR engine for extracting text from images.

### Build the Docker Image

```bash
# Navigate to paddle_ocr directory
cd paddle_ocr

# Build the image (this will take some time as it installs models)
docker build -t paddleocr:latest .
```

### Run the Container

```bash
# Run PaddleOCR service
docker run -d \
  --name paddle-ocr \
  -p 8088:8088 \
  paddleocr:latest

# Check logs
docker logs -f paddle-ocr
```

### Alternative: Pull from Docker Hub

```bash
# Pull pre-built image
docker pull nasim0086/paddleocr:latest

# Run the container
docker run -d \
  --name paddle-ocr \
  -p 8088:8088 \
  nasim0086/paddleocr:latest
```

### Test the Service

```bash
# Using curl with an image file
curl -X POST http://localhost:8088/ocr \
  -F "file=@/path/to/your/image.png"

# Expected response:
{
    "status": "success",
    "content": "Extracted text from the image...",
    "total_pages": 1
}
```

### Configuration

```bash
USE_LLM_FOR_OCR=false
OCR_ENDPOINT=http://localhost
OCR_PORT=8088
```

---

## 4. Vision LM OCR (IBM Granite)

LLM-based OCR engine using IBM Granite Vision model for higher accuracy text extraction.

### Build the Docker Image

```bash
# Navigate to vision_lm_ocr directory
cd vision_lm_ocr

# Build the image (requires models to be present in models/ directory)
docker build -t vision-lm-ocr:latest .
```

### Run the Container

```bash
# Run Vision LM OCR service (requires 6GB memory)
docker run -d \
  --name ocr_engine \
  --memory=6g \
  -p 8087:8087 \
  vision-lm-ocr:latest

# Monitor logs (model loading may take 1-2 minutes)
docker logs -f ocr_engine
```

### Alternative: Pull from Docker Hub

```bash
# Pull pre-built image
docker pull nasim0086/vision-lm-ocr:latest

# Run the container
docker run -d \
  --name ocr_engine \
  --memory=6g \
  -p 8087:8087 \
  nasim0086/vision-lm-ocr:latest
```

### Test the Service

```bash
# Using curl (OpenAI-compatible API)
curl -X POST http://localhost:8087/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite-docling-258M-f16",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "Extract all text from this image."},
          {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
      }
    ]
  }'
```

### Configuration

```bash
USE_LLM_FOR_OCR=true
LLM_MODEL_NAME=granite-docling-258M-f16
LLM_ENDPOINT=http://localhost:8087/v1/chat/completions
```

---

## Quick Start: Run All Services

### Start All Services

```bash
# Navigate to project root
cd /home/nasim-pc/Desktop/Document_Search/pre-requisite

# Start Elasticsearch
docker start es01

# Start Embedding Service
docker start embedding-service

# Start PaddleOCR (recommended)
docker start paddle-ocr

# Optional: Start Vision LM OCR
docker start ocr_engine
```

### Stop All Services

```bash
docker stop es01 embedding-service paddle-ocr ocr_engine
```

### Check Running Services

```bash
docker ps

# Expected output:
# CONTAINER ID   IMAGE                      PORTS                    STATUS
# xxxxxxxxxxxx   embedding-service:v0.1     0.0.0.0:8001->8001/tcp   Up
# xxxxxxxxxxxx   paddleocr:latest           0.0.0.0:8088->8088/tcp   Up
# xxxxxxxxxxxx   elasticsearch:8.11.3       0.0.0.0:9200->9200/tcp   Up
# xxxxxxxxxxxx   vision-lm-ocr:latest       0.0.0.0:8087->8087/tcp   Up (optional)
```

---

## Service Comparison

| Service | Port | Memory | CPU | Purpose |
|---------|------|--------|-----|---------|
| **Elasticsearch** | 9200 | 4GB | Medium | Vector & full-text search |
| **Embedding Service** | 8001 | 2GB | Low | Text → Vector embeddings |
| **PaddleOCR** | 8088 | 2GB | Low-Medium | Fast OCR extraction |
| **Vision LM OCR** | 8087 | 6GB | Medium-High | High-accuracy LLM OCR |

---

## Choosing Between OCR Engines

### Use PaddleOCR (Default) when:
- You need fast processing
- Limited memory/CPU available
- Good accuracy is sufficient
- Processing large volumes of documents

### Use Vision LM OCR when:
- You need highest accuracy
- Complex document layouts
- 6GB+ memory available
- Quality over speed

**Note**: You only need ONE OCR engine running at a time. Choose based on your requirements.

---

## Troubleshooting

### Elasticsearch won't start

```bash
# Increase vm.max_map_count
sudo sysctl -w vm.max_map_count=262144

# Make it permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

### Port already in use

```bash
# Check which process is using the port
sudo lsof -i :8088

# Kill the process or stop conflicting container
docker stop <container_name>
```

### Out of memory

```bash
# Check Docker resource usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
# Or run containers with lower memory:
docker run -d --memory=2g ...
```

### Service not responding

```bash
# Check container logs
docker logs -f <container_name>

# Restart the container
docker restart <container_name>

# Remove and recreate if needed
docker rm -f <container_name>
# Then run the docker run command again
```

---

## Docker Hub Images

All images are available on Docker Hub:

- `docker pull nasim0086/embedding-service:v0.1`
- `docker pull nasim0086/paddleocr:latest`
- `docker pull nasim0086/vision-lm-ocr:latest`

---
