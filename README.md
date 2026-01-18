#  Document Search System - Complete Setup Guide

## Demo Video

<div style="padding:75% 0 0 0;position:relative;"><iframe src="https://player.vimeo.com/video/1155751169?title=0&amp;byline=0&amp;portrait=0&amp;badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479" frameborder="0" allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share" referrerpolicy="strict-origin-when-cross-origin" style="position:absolute;top:0;left:0;width:100%;height:100%;" title="demo_video"></iframe></div><script src="https://player.vimeo.com/api/player.js"></script>

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup (experienced users)  
> **Verify Setup**: Run `python tests/setup_test.py` to validate all services and configuration

---

## Documentation Index

| Document | Description | When to Use |
|----------|-------------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | 5-minute quick start | For experienced users |
| [pre-requisite/README.md](pre-requisite/README.md) | Build Docker services from source | For offline/custom builds |
| [tests/setup_test.py](tests/setup_test.py) | Validate system configuration | Before running ingestion |

---

## Typical Workflow

### First Time (Do Once)
1. **Read**: [docs/FIRST_TIME_SETUP.md](docs/FIRST_TIME_SETUP.md) - Complete setup guide
2. **Setup**: Start all Docker infrastructure services
3. **Configure**: Create and configure `.env` file
4. **Validate**: Run `python tests/setup_test.py`
5. **Ingest**: Run first ingestion with `FIRST_RUN_FULL_INGEST=true`
6. **Switch**: Set `FIRST_RUN_FULL_INGEST=false` and enable SQS/sync

### Daily Operations (Continuous)
1. **Ingestion Service** (keep running): `python src/ingestion/run_ingestion.py`
   - Monitors SQS for new files → auto-indexes
   - Monitors SQS for deleted files → auto-removes from Elasticsearch
   - Runs background sync every 6 hours (safety net)

2. **Search API** (keep running): `python src/api/run_query_api.py`
   - Serves search requests at http://localhost:8000
   - Returns results from Elasticsearch

---

## New Features

### File Deletion Synchronization
Automatically removes documents from Elasticsearch when files are deleted from S3.

**Features:**
- Real-time deletion via SQS (< 1 second)
- Background sync every 6 hours (100% reliability)
- Simple 2-line configuration
- Zero performance impact on search

**Setup:** See [docs/DELETION_SYNC.md](docs/DELETION_SYNC.md)

**Quick config:**
```bash
# Add to .env
ENABLE_BACKGROUND_SYNC=true
SYNC_INTERVAL_HOURS=6
```

---

## System Requirements

- **OS**: Ubuntu 20.04 or 22.04
- **RAM**: 16GB
- **CPU**: 4-8 cores
- **Storage**: 50GB+ free space
- **Python**: 3.12 or above
- **Docker**: Latest version

---

## Part 1: Docker Installation

```bash
# Install Docker and plugins
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Check Docker status
sudo systemctl status docker

# Start Docker if not running
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Test Docker installation
sudo docker run hello-world

# (Optional) Add user to docker group to avoid sudo
sudo usermod -aG docker $USER
# Log out and log back in for this to take effect
```

---

## Part 2: Infrastructure Setup

> ** For offline infrastructure setup or building services from source**, refer to the comprehensive guide in [pre-requisite/README.md](pre-requisite/README.md)

The following sections show how to quickly pull and run pre-built Docker images. For building images yourself or detailed documentation on each service, see the pre-requisite folder.

### 1. Elasticsearch (Vector & Full-Text Search Engine)

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

**For HTTPS with authentication** (Optional):
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

**Verify Elasticsearch:**
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

**Configure in `.env`:**
```bash
ELASTICSEARCH_INDEX=documents_v1
```

---

### 2. PaddleOCR (Fast OCR Engine) - Recommended

```bash
# Pull PaddleOCR image
docker pull nasim0086/paddleocr:latest

# Run PaddleOCR service
docker run -d -p 8088:8088 \
  --name paddle-ocr \
  nasim0086/paddleocr:latest


# Check logs
docker logs -f paddle-ocr
```

**Test PaddleOCR:**
```bash
# Using Postman
POST http://localhost:8088/ocr
Body: form-data
  file: @"/home/nasim-pc/Desktop/Document_Search/dummy_data/images/ocr_kangaroo.png"

# Expected response:
{
    "status": "success",
    "content": "The kangaroo is a marsupial from...",
    "total_pages": 1
}
```

---

### 3. IBM Granite Vision LM (Optional - LLM-based OCR)

**Only enable if you want higher accuracy LLM-based OCR**

```bash
# Pull Vision LM image
docker pull nasim0086/vision-lm-ocr:latest

# Run with 6GB memory
docker run -d -p 8087:8087 \
  --name ocr_engine \
  --memory=6g \
  nasim0086/vision-lm-ocr:latest

# Monitor logs (model loading may take 1-2 minutes)
docker logs -f ocr_engine
```

**Configure in `.env` to enable LLM:**
```bash
USE_LLM_FOR_OCR=true
LLM_MODEL_NAME=granite-docling-258M-f16
LLM_ENDPOINT=http://localhost:8087/v1/chat/completions
```

---

### 4. Embedding Service (Text → Vector Embeddings)

```bash
# Pull embedding service
docker pull nasim0086/embedding-service:v0.1

# Run embedding service
docker run -d -p 8001:8001 --name embedding-service nasim0086/embedding-service:v0.1
```

**Test Embedding Service:**
```bash
# Using Postman
POST http://localhost:8001/embed
Content-Type: application/json

{
    "model": "bge-small-en-v1.5",
    "text": "The quick brown fox jumps over the lazy dog."
}

# Expected: Array of 384 float values
```

---

## Part 3: AWS Configuration

### Setup S3 Bucket

1. Create S3 bucket: `document-search-proj`
2. Region: `eu-north-1` (or your region)
3. Create folders:
   - `docx_data/`
   - `pdf_images/`
   - `xls_data/`

### Get AWS Credentials
- IAM → Users → Security Credentials → Create Access Key

### SQS Real-time Alert (Optional)

**Only enable if you want automatic ingestion on S3 uploads**

Set `SQS_ENABLED=true` in `.env` after configuring SNS/SQS

See AWS documentation for SNS/SQS setup with S3 event notifications.

---

## Part 4: Python Setup

```bash
# Navigate to project
cd /home/nasim-pc/Desktop/Document_Search

# Create conda environment (recommended)
conda create -n doc_search_env python=3.13
conda activate doc_search_env

# OR use venv
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r src/ingestion/requirements.txt

# Verify installation
python verify_requirements.py
```

---

##  Part 5: Configuration

**Single Configuration File**: `.env` (root directory)

Edit `.env` in the project root:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=eu-north-1
S3_BUCKET_NAME=document-search-proj

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=documents_v1

# OCR Configuration - Choose ONE:

## Option 1: PaddleOCR (Fast, CPU-friendly)
USE_LLM_FOR_OCR=false
OCR_ENDPOINT=http://localhost
OCR_PORT=8088

## Option 2: LLM-based (Higher accuracy, needs more RAM)
# USE_LLM_FOR_OCR=true
# LLM_MODEL_NAME=granite-docling-258M-f16
# LLM_ENDPOINT=http://localhost:8087/v1/chat/completions

# Embedding Service
EMBEDDING_MODEL_NAME=bge-small-en-v1.5
EMBEDDING_ENDPOINT=http://localhost:8001/embed

# SQS Configuration (Optional - for real-time ingestion on S3 uploads)
# Option A: Disable SQS (run ingestion only from S3 once)
SQS_ENABLED=false
SQS_QUEUE_URL=

# Option B: Enable SQS (continuous monitoring for new S3 uploads)
# SQS_ENABLED=true
# SQS_QUEUE_URL=https://sqs.eu-north-1.amazonaws.com/175167948868/document-ingestion-queue
```

---

##  Part 6: Running the System

### Verify All Services

Before running ingestion, validate your complete setup:

```bash
# Run comprehensive setup validation
python tests/setup_test.py

# This will check:
#  Python packages installation
#  Environment variables (.env configuration)
#  AWS S3 connection and bucket access
#  Elasticsearch connection and index
#  OCR service (PaddleOCR or Vision LM)
#  Embedding service
#  File parsers initialization
```

**Expected Output:**
```
======================================================================
INGESTION PIPELINE SETUP VALIDATION
======================================================================

Passed: 41/41
Failed: 0/41
Warnings: 0

======================================================================
VALIDATION PASSED - All systems ready for ingestion!
======================================================================

To start ingestion, run:
   python src/ingestion/run_ingestion.py
```

### Check Docker Containers

```bash
# Verify all required containers are running
docker ps

# Expected: 3-4 containers running
# - es01 (Elasticsearch) - Port 9200
# - paddle-ocr - Port 8088
# - embedding-service - Port 8001
# - ocr_engine (optional, if using Vision LM) - Port 8087
```

### Run Document Ingestion

```bash
# Activate environment
conda activate doc_search

# Run ingestion
cd src/ingestion
python run_ingestion.py
```

**Expected Output:**
```
============================================================
Starting Document Ingestion Service
============================================================
Validating configuration...
=== Ingestion Pipeline Configuration ===
AWS Region: eu-north-1
S3 Bucket: document-search-proj
Elasticsearch: localhost:9200
Elasticsearch Index: documents_v1
Use LLM for OCR: False
OCR Endpoint: http://localhost:8088
...
All services initialized successfully
First-run mode: ingesting entire bucket contents
 Ingesting prefix: docx_data/
Processing: document001.docx
Successfully parsed and indexed
...
Starting SQS queue listener...
```

---

##  Ingestion Modes

### Mode 1: S3-Only Ingestion (No SQS)

**Use when**: You want to ingest all documents from S3 once, without continuous monitoring.

**Configuration**:
```bash
# Edit src/ingestion/.env
SQS_ENABLED=false
SQS_QUEUE_URL=
```

**Behavior**:
1. Scans entire S3 bucket (`docx_data/`, `pdf_images/`, `xls_data/`)
2. Processes all documents
3. Exits when complete
4. Re-run manually when you upload new documents

**Run**:
```bash
python src/ingestion/run_ingestion.py
```

---

### Mode 2: Continuous SQS Monitoring (Real-time)

**Use when**: You want automatic ingestion whenever new documents are uploaded to S3.

**Prerequisites**:
1. AWS SNS topic configured
2. AWS SQS queue subscribed to SNS
3. S3 bucket event notifications enabled (upload → SNS)

**Configuration**:
```bash
# Edit src/ingestion/.env
SQS_ENABLED=true
SQS_QUEUE_URL=https://sqs.eu-north-1.amazonaws.com/YOUR_ACCOUNT_ID/YOUR_QUEUE_NAME
```

**Behavior**:
1. First run: Ingests all existing documents from S3
2. Then: Continuously monitors SQS queue
3. Auto-processes new documents uploaded to S3
4. Runs indefinitely until stopped (Ctrl+C)

**Run**:
```bash
python src/ingestion/run_ingestion.py
# Service will keep running...
```

---

##  Switching Between PaddleOCR and LLM

| Feature | PaddleOCR | Granite Vision LM |
|---------|-----------|-------------------|
| Speed | Fast | Slower |
| Accuracy | Good | Higher |
| Memory | ~2GB | ~6GB |
| CPU-only | Yes | Yes (slower) |
| Cost | Lower | Higher |

### Use PaddleOCR (Default):
```bash
# Edit src/ingestion/.env
USE_LLM_FOR_OCR=false
OCR_ENDPOINT=http://localhost
OCR_PORT=8088
```

### Use LLM OCR:
```bash
# Ensure Vision LM is running
docker ps | grep ocr_engine

# Edit src/ingestion/.env
USE_LLM_FOR_OCR=true
LLM_ENDPOINT=http://localhost:8087/v1/chat/completions

# Restart ingestion
python src/ingestion/run_ingestion.py
```

**No code changes needed - just update `.env` and restart!**

---

##  Testing

### Comprehensive Setup Validation

```bash
# Run complete system validation (recommended before first run)
python tests/setup_test.py

# This validates:
# - All Python packages
# - Environment configuration
# - AWS S3 connection
# - Elasticsearch connection and indexing
# - OCR service (PaddleOCR or Vision LM)
# - Embedding service
# - File parser initialization
```

### Individual Service Tests

```bash
# Test Elasticsearch
curl http://localhost:9200

# Test PaddleOCR
curl -X POST http://localhost:8088/ocr -F "file=@dummy_data/images/test.jpg"

# Test Embedding Service
curl -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{"model": "bge-small-en-v1.5", "text": "test", "normalize": true}'

# Check indexed documents
curl http://localhost:9200/documents_v1/_count
```

---

##  Troubleshooting

### Elasticsearch won't start
```bash
# Increase vm.max_map_count
sudo sysctl -w vm.max_map_count=262144
```

### PaddleOCR connection failed
```bash
docker restart paddle-ocr
docker logs -f paddle-ocr
```

### Python module errors
```bash
pip install --upgrade -r requirements.txt
```

---

## Documentation

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start for experienced users
- **[tests/setup_test.py](tests/setup_test.py)** - Validate system configuration

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system architecture, data flow, and components

### Features & Configuration
- **[DELETION_SYNC.md](docs/DELETION_SYNC.md)** - Complete file deletion synchronization guide
- **[DELETION_SYNC_QUICKSTART.md](docs/DELETION_SYNC_QUICKSTART.md)** - Quick deletion sync setup
- **[DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)** - Production deployment checklist

### Advanced Setup
- **[pre-requisite/README.md](pre-requisite/README.md)** - Build Docker services from source

---

## Quick Reference

### Essential Commands

```bash
# Validate setup before starting
python tests/setup_test.py

# Start all Docker services
docker start es01 paddle-ocr embedding-service

# Stop all services
docker stop es01 paddle-ocr embedding-service

# Ingestion service (keep running)
python src/ingestion/run_ingestion.py

# Search API service (keep running)
python src/api/run_query_api.py

# View service logs
docker logs -f paddle-ocr
tail -f ingestion.log

# Test deletion sync
python tests/test_deletion_sync.py
```

### Configuration Quick Switch

```bash
# Switch OCR method
# Edit .env: USE_LLM_FOR_OCR=true/false

# Enable/disable SQS
# Edit .env: SQS_ENABLED=true/false

# Enable background sync (recommended)
# Edit .env: ENABLE_BACKGROUND_SYNC=true
```

### Search API Examples

```bash
# Simple search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "lion habitat", "size": 5}'

# Fuzzy search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "renewable enrgy", "size": 5, "fuzziness": "AUTO"}'

# Field-specific search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "report", "size": 5, "fields": ["file_name"]}'
```

---

## Features Summary

### Core Features
- **Multi-format Support**: PDF, DOCX, Excel, CSV, Images (PNG, JPG, TIFF)
- **Dual OCR Options**: PaddleOCR (fast) or IBM Granite Vision LM (accurate)
- **Smart Text Processing**: OCR error correction, deduplication, intelligent chunking
- **Hybrid Search**: Vector semantic + BM25 keyword search
- **Real-time Ingestion**: SQS-based automatic processing of new files
- **File Deletion Sync**: Automatic removal from search when deleted from S3

### Latest Features
- **Hybrid Deletion Synchronization**
  - Real-time via SQS (< 1 second)
  - Background sync every 6 hours (100% reliability)
  - Zero performance impact on search
  
- **Content Deduplication**
  - SHA256-based duplicate detection
  - Automatic skip during ingestion
  - 20-40% storage savings

---

## System Overview

```
S3 Bucket → [SQS Queue] → Ingestion Pipeline → Elasticsearch
                            ↓
                    [PaddleOCR/Vision LM]
                            ↓
                    [Embedding Service]
                            ↓
                    [Background Sync] ← Cleanup orphans
                            
Elasticsearch ← Search API ← User Queries
```

**Key Components:**
- **Elasticsearch 8.11.3**: Vector + full-text search
- **PaddleOCR**: Fast CPU-based OCR (~2s/page)
- **IBM Granite Vision LM**: LLM-based OCR (~4s/page)
- **BGE Embeddings**: Semantic search (384 dimensions)
- **FastAPI**: RESTful search API
- **Background Sync**: Ensures 100% consistency

---

## License

MIT License

