# 🚀 Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Clone & Navigate
```bash
cd /home/nasim-pc/Desktop/Document_Search
```

### Step 2: Create Environment
```bash
# Option A: Conda (Recommended)
conda create -n doc_search_env python=3.11
conda activate doc_search_env

# Option B: venv
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation
```bash
python verify_requirements.py
```

**Expected output:**
```
 All required packages are installed and working!
 System is ready to run
```

### Step 5: Start Docker Services
```bash
# Elasticsearch
docker start es01

# PaddleOCR
docker start paddle-ocr

# Embedding Service
docker start embedding-service
```

**Verify services:**
```bash
# Check Elasticsearch
curl http://localhost:9200

# Check PaddleOCR
curl http://localhost:8088/health

# Check Embedding Service
curl http://localhost:8001/health
```

### Step 6: Configure Environment
```bash
# Edit .env file with your settings
nano .env

# Minimum required:
# - AWS credentials
# - S3 bucket name
# - Elasticsearch index name
```

### Step 7: Run Ingestion
```bash
python src/ingestion/run_ingestion.py
```

---

##  Common Tasks

### Run S3-Only Ingestion (No SQS)
```bash
# Edit .env
SQS_ENABLED=false
SQS_QUEUE_URL=

# Run
python src/ingestion/run_ingestion.py
```

### Run with SQS Monitoring
```bash
# Edit .env
SQS_ENABLED=true
SQS_QUEUE_URL=https://sqs.REGION.amazonaws.com/ACCOUNT_ID/QUEUE_NAME

# Run (keeps running)
python src/ingestion/run_ingestion.py
```

### Switch OCR Method

**Use PaddleOCR (Fast):**
```bash
# Edit .env
USE_LLM_FOR_OCR=false
OCR_ENDPOINT=http://localhost
OCR_PORT=8088
```

**Use LLM OCR (Higher Accuracy):**
```bash
# Edit .env
USE_LLM_FOR_OCR=true
LLM_ENDPOINT=http://localhost:8087/v1/chat/completions
```

### Check System Status
```bash
# Verify Python packages
python verify_requirements.py

# Check Docker containers
docker ps

# View logs
docker logs -f paddle-ocr
docker logs -f es01

# Check Elasticsearch index
curl http://localhost:9200/documents_v1/_count
```

---

## 🛠️ Troubleshooting

### Problem: Missing packages
```bash
# Solution: Reinstall
pip install -r requirements.txt --upgrade
```

### Problem: Docker services not running
```bash
# Solution: Restart services
docker restart es01 paddle-ocr embedding-service

# Check status
docker ps
```

### Problem: Elasticsearch won't start
```bash
# Solution: Increase vm.max_map_count
sudo sysctl -w vm.max_map_count=262144
```

### Problem: Configuration not loading
```bash
# Solution: Check .env location (must be in root)
ls -la .env

# Verify content
cat .env | grep -E "AWS_|ELASTICSEARCH_|OCR_|SQS_"
```

---

## 📚 Full Documentation

For detailed setup and configuration:
- **Full Setup**: [README.md](README.md)
- **Configuration**: [docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **SQS Setup**: [docs/SQS_CONFIGURATION.md](docs/SQS_CONFIGURATION.md)

---

##  Pre-flight Checklist

Before running ingestion:

- [ ] Python 3.11+ installed
- [ ] Dependencies installed (`python verify_requirements.py`)
- [ ] Docker services running (`docker ps`)
- [ ] Elasticsearch accessible (`curl http://localhost:9200`)
- [ ] PaddleOCR or Vision LM running
- [ ] Embedding service running
- [ ] `.env` configured with AWS credentials
- [ ] S3 bucket accessible
- [ ] Elasticsearch index configured

---

## 🎉 You're Ready!

```bash
python src/ingestion/run_ingestion.py
```

Watch the logs for:
-  Services initialized
- 📂 Processing files
-  Successfully indexed
- 📊 Summary statistics
