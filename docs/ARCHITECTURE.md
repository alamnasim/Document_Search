# Document Search System - Advanced Architecture

## System Overview

### Ingestion Modes

The system supports **two ingestion modes** that can be configured via `.env` file:

**Mode 1: SQS-Triggered (Real-time)**
- Continuous monitoring of SQS queue
- Automatic processing when files uploaded to S3
- Requires AWS SNS/SQS infrastructure
- Best for production with real-time requirements

**Mode 2: S3-Only (Batch)**
- One-time scan of S3 bucket
- Manual execution for batch processing
- No SQS/SNS setup required
- Best for development or scheduled ingestion

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT SEARCH SYSTEM                               │
│                         Production Architecture                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐
│   Data Sources (AWS)    │
│  ┌──────────────────┐   │     ┌──────────────────────────────────────────┐
│  │   S3 Bucket      │   │     │      INGESTION PIPELINE                  │
│  │ document-search- │◄──┼─────┤    (Two Modes: SQS or S3-only)          │
│  │      proj        │   │     │  ┌────────────────────────────────────-┐ │
│  ├──────────────────┤   │     │  │  Document Processors                │ │
│  │ • docx_data/     │   │     │  ├────────────────────────────────────-┤ │
│  │ • pdf_images/    │   │     │  │ Parser Layer:                       │ │
│  │ • xls_data/      │   │     │  │  • PDF Parser (PyMuPDF + OCR)       │ │
│  └──────────────────┘   │     │  │  • Image Parser (PIL + OCR)         │ │
│                          │    │  | • DOCX Parser (MarkItDown)          │ │
│         │                │    │  │  • Excel Parser (Pandas)            │ │
│         │ S3 Event       │    │  │  • CSV Parser (Pandas)              │ │
│         ▼                │    │  └────────────────────────────────────-┘ │
│  ┌──────────────────┐   │     │                 │                        │
│  │   SNS Topic      │   │     │                 ▼                        │
│  └──────────────────┘   │     │  ┌────────────────────────────────────-┐ │
│         │                │    │  │  OCR Layer (Configurable)           │ │
│         │ Subscribe      │    │  ├────────────────────────────────────-┤ │
│         ▼                │    │  │ Option 1: PaddleOCR (Port 8088)     │ │
│  ┌──────────────────┐   │     │  │  • Fast CPU-based                   │ │
│  │   SQS Queue      │   │     │  │  • ~2GB memory                      │ │
│  │  (Real-time)     │   │     │  │  • Good accuracy                    │ │
│  └──────────────────┘   │     │  │                                     │ │
└───────────┬──────────────┘     │  │ Option 2: IBM Granite Vision LM    │ │
            │                     │  │           (Port 8087)             │ │
            │                     │  │  • LLM-based OCR                  │ │
            └─────────────────────┼─►│  • granite-docling-258M-f16       │ │
                                  │  │  • ~6GB memory                    │ │
                                  │  │  • Higher accuracy                │ │
                                  │  └────────────────────────────────────┘ │
                                  │                 │                        │
                                  │                 ▼                        │
                                  │  ┌────────────────────────────────────┐ │
                                  │  │  Text Processing Layer             │ │
                                  │  ├────────────────────────────────────┤ │
                                  │  │ • Text Cleaner                     │ │
                                  │  │   - Normalize whitespace           │ │
                                  │  │   - Fix OCR errors (isa→is a)      │ │
                                  │  │   - Remove artifacts               │ │
                                  │  │ • Metadata Extractor               │ │
                                  │  │   - File metadata                  │ │
                                  │  │   - Content statistics             │ │
                                  │  │ • Smart Chunker                    │ │
                                  │  │   - 512 token chunks               │ │
                                  │  │   - 50 token overlap               │ │
                                  │  │   - Sentence boundary aware        │ │
                                  │  └────────────────────────────────────┘ │
                                  │                 │                        │
                                  │                 ▼                        │
                                  │  ┌────────────────────────────────────┐ │
                                  │  │  Embedding Service (Port 8001)     │ │
                                  │  ├────────────────────────────────────┤ │
                                  │  │ Model: bge-small-en-v1.5           │ │
                                  │  │ Embedding Dimension: 384           │ │
                                  │  │ Input: Text chunks                 │ │
                                  │  │ Output: Dense vectors              │ │
                                  │  └────────────────────────────────────┘ │
                                  │                 │                        │
                                  └─────────────────┼────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STORAGE & INDEXING LAYER                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Elasticsearch 8.11.3 (Port 9200)                                      │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │  Index: documents_v1                                                   │ │
│  │                                                                         │ │
│  │  Schema:                                                                │ │
│  │  • doc_id (keyword)                                                     │ │
│  │  • filename (text)                                                      │ │
│  │  • content (text) ◄── Full-text search                                 │ │
│  │  • embeddings (dense_vector[384]) ◄── Semantic search                  │ │
│  │  • chunk_id, chunk_index                                                │ │
│  │  • metadata (object)                                                    │ │
│  │  • timestamp                                                            │ │
│  │                                                                         │ │
│  │  Capabilities:                                                          │ │
│  │  - Dense vector search (cosine similarity)                             │ │
│  │  - Keyword search (BM25)                                                │ │
│  │  - Hybrid search (combined)                                             │ │
│  │  - Metadata filtering                                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUERY & RETRIEVAL API                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  FastAPI Service (src/api/)                                            │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                         │ │
│  │  Endpoints:                                                             │ │
│  │  • POST /search/semantic                                                │ │
│  │    - Semantic search using embeddings                                   │ │
│  │    - Input: User query text                                             │ │
│  │    - Process:                                                           │ │
│  │      1. Generate query embedding via embedding service                  │ │
│  │      2. kNN search in Elasticsearch                                     │ │
│  │      3. Return top-k results                                            │ │
│  │                                                                         │ │
│  │  • POST /search/keyword                                                 │ │
│  │    - Full-text search using BM25                                        │ │
│  │    - Supports wildcards, fuzzy matching                                 │ │
│  │                                                                         │ │
│  │  • POST /search/hybrid                                                  │ │
│  │    - Combines semantic + keyword                                        │ │
│  │    - Reranking with score fusion                                        │ │
│  │                                                                         │ │
│  │  • GET /documents/{doc_id}                                              │ │
│  │    - Retrieve specific document                                         │ │
│  │                                                                         │ │
│  │  • GET /health                                                          │ │
│  │    - Service health check                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │   Client      │
                            │ Applications  │
                            └───────────────┘
```

---

## Data Flow Diagram

```
┌─────────┐
│ User    │
│ Uploads │
│ File    │
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION FLOW                                  │
└─────────────────────────────────────────────────────────────────────┘

Step 1: S3 Upload
    │
    ├──► S3: document-search-proj/pdf_images/report.pdf
    │
    └──► Trigger: 
         • SQS Mode: S3 Event → SNS → SQS (Real-time)
         • S3 Mode: Manual run scans bucket (Batch)

Step 2: File Retrieval
    │
    ├──► SQS Mode: Queue Listener detects message
    │    └──► Download file from S3
    │
    └──► S3 Mode: Iterate through S3 prefixes
         └──► Download each file from S3

Step 3: Parsing
    │
    ├──► Route to PDFParser
    │
    └──► Extract text/images

Step 4: OCR (if needed)
    │
    ├──► If USE_LLM_FOR_OCR=false:
    │    └──► POST http://localhost:8088/ocr
    │         └──► Returns: {"content": "extracted text..."}
    │
    └──► If USE_LLM_FOR_OCR=true:
         └──► POST http://localhost:8087/v1/chat/completions
              └──► Returns: LLM response with extracted text

Step 5: Text Cleaning
    │
    ├──► Fix OCR errors:
    │    • "isa" → "is a"
    │    • "catof" → "cat of"
    │    • "India.It" → "India. It"
    │
    └──► Remove extra newlines, normalize whitespace

Step 5.5: Content Deduplication (SHA256 Hash)
    │
    ├──► Calculate SHA256 hash of cleaned content
    │
    ├──► Query Elasticsearch for existing content_hash
    │
    └──► If duplicate found:
         • Log: "Duplicate content detected - SKIPPED"
         • Skip to next document
         Otherwise: Continue to Step 6

Step 6: Chunking
    │
    ├──► Split into 512-token chunks
    │
    └──► 50-token overlap for context continuity

Step 7: Embedding Generation
    │
    └──► For each chunk:
         POST http://localhost:8001/embed
         {
             "model": "bge-small-en-v1.5",
             "text": "chunk content..."
         }
         Returns: [0.123, -0.456, ...] (384 dimensions)

Step 8: Indexing
    │
    └──► POST http://localhost:9200/documents_v1/_doc
         {
             "doc_id": "report_chunk_0",
             "filename": "report.pdf",
             "content": "chunk text...",
             "embeddings": [0.123, -0.456, ...],
             "metadata": {...}
         }

┌─────────────────────────────────────────────────────────────────────┐
│                     QUERY FLOW                                      │
└─────────────────────────────────────────────────────────────────────┘

Step 1: User Query
    │
    └──► "What are the benefits of renewable energy?"

Step 2: Query Embedding
    │
    └──► POST http://localhost:8001/embed
         Returns: query_vector[384]

Step 3: Hybrid Search
    │
    ├──► Semantic Search:
    │    Elasticsearch kNN query with query_vector
    │    Returns: Top 10 most similar chunks
    │
    └──► Keyword Search:
         Elasticsearch match query with BM25
         Returns: Top 10 keyword matches

Step 4: Reranking
    │
    ├──► Combine results with score fusion
    │
    └──► Deduplicate by doc_id

Step 5: Response
    │
    └──► Return:
         [
             {
                 "doc_id": "report_chunk_5",
                 "filename": "energy_report.pdf",
                 "content": "Renewable energy benefits include...",
                 "score": 0.89,
                 "metadata": {...}
             },
             ...
         ]
```

---

## Component Details

### 1. Document Parsers

| Parser | File Types | Method | OCR Support |
|--------|-----------|---------|-------------|
| **PDFParser** | `.pdf` | PyMuPDF | Yes - Configurable (PaddleOCR/LLM) |
| **ImageParser** | `.jpg`, `.png`, `.jpeg` | PIL + OCR | Yes - Configurable (PaddleOCR/LLM) |
| **DOCXParser** | `.docx` | MarkItDown |  Direct text extraction |
| **ExcelParser** | `.xlsx`, `.xls` | Pandas |  Direct text extraction |
| **CSVParser** | `.csv` | Pandas |  Direct text extraction |

### 2. OCR Services Comparison

| Feature | PaddleOCR | Granite Vision LM |
|---------|-----------|-------------------|
| **Endpoint** | `http://localhost:8088/ocr` | `http://localhost:8087/v1/chat/completions` |
| **Method** | POST with multipart form-data | POST with base64 image in JSON |
| **Memory** | ~2GB | ~6GB |
| **Speed** | Fast (< 1s/page) | Slower (~3-5s/page) |
| **Accuracy** | Good for clean text | Better for handwriting/complex layouts |
| **API Format** | File upload | OpenAI-compatible chat |
| **Response** | `{"status": "success", "content": "text"}` | Chat completion with extracted text |
| **Configuration** | `USE_LLM_FOR_OCR=false` | `USE_LLM_FOR_OCR=true` |

### 3. Text Cleaning Pipeline

```python
# PaddleOCR Output Example
raw_text = """
The lion (Panthera leo) isa large catof the genus Panthera
native to Africa and India.It hasa muscular, deep-chested body...
"""

# After clean_paddleocr_output()
cleaned_text = """
The lion (Panthera leo) is a large cat of the genus Panthera native to Africa and India. It has a muscular, deep-chested body...
"""

# Fixes Applied:
# 1. \bisa\b → "is a"
# 2. \bhasa\b → "has a"
# 3. catof → "cat of"
# 4. India.It → "India. It" (space after period)
# 5. Mid-sentence newlines removed
# 6. Paragraph breaks preserved
```

### 4. Content-Based Deduplication

**Algorithm**: SHA256 hashing of cleaned text content

```python
import hashlib

# After text cleaning, calculate content hash
content_hash = hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()

# Check if hash exists in Elasticsearch
query = {
    "query": {
        "term": {
            "content_hash": content_hash
        }
    },
    "size": 1
}

is_duplicate = elasticsearch.check_duplicate(content_hash)

if is_duplicate:
    logger.info(f"Duplicate content detected - SKIPPED")
    return  # Skip indexing
```

**Benefits**:
- **Content-based**: Detects duplicates even if filename changes
- **Fast lookup**: O(1) hash table lookup in Elasticsearch
- **Storage savings**: Avoids indexing duplicate content
- **Cost reduction**: Skips embedding generation for duplicates

**How it works**:
1. Clean text content after parsing
2. Calculate SHA256 hash (64-character hex string)
3. Query Elasticsearch for existing `content_hash`
4. If found: Skip processing and log duplicate
5. If not found: Continue with chunking and indexing

**Example**:
```
Document 1: "report_2024.pdf" → Hash: "a1b2c3..."
Document 2: "report_copy.pdf" → Hash: "a1b2c3..." (same content)

Result: Document 2 detected as duplicate and skipped
```

### 5. Chunking Strategy

```python
# Configuration
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens

# Example Document (1500 tokens)
Document: "Introduction to AI... [1500 tokens]"

# Chunks Created:
Chunk 0: tokens[0:512]
Chunk 1: tokens[462:974]    # 50 token overlap with Chunk 0
Chunk 2: tokens[924:1436]   # 50 token overlap with Chunk 1
Chunk 3: tokens[1386:1500]  # Remaining tokens

# Benefits:
- Maintains context across chunks
- Prevents information loss at boundaries
- Optimal for retrieval (not too small/large)
```

### 6. Elasticsearch Schema

```json
{
  "mappings": {
    "properties": {
      "doc_id": {
        "type": "keyword"
      },
      "filename": {
        "type": "text",
        "fields": {
          "keyword": {
            "type": "keyword"
          }
        }
      },
      "file_path": {
        "type": "text",
        "fields": {
          "keyword": {
            "type": "keyword"
          }
        }
      },
      "content": {
        "type": "text",
        "analyzer": "standard"
      },
      "content_hash": {
        "type": "keyword",
        "index": true
      },
      "embeddings": {
        "type": "dense_vector",
        "dims": 384,
        "index": true,
        "similarity": "cosine"
      },
      "chunk_id": {
        "type": "keyword"
      },
      "chunk_index": {
        "type": "integer"
      },
      "metadata": {
        "type": "object",
        "properties": {
          "file_size": {"type": "long"},
          "file_type": {"type": "keyword"},
          "num_pages": {"type": "integer"},
          "extraction_method": {"type": "keyword"},
          "s3_key": {"type": "keyword"},
          "upload_timestamp": {"type": "date"}
        }
      },
      "timestamp": {
        "type": "date"
      }
    }
  }
}
```

---

## File Deletion Synchronization

### Overview

The system automatically removes documents from Elasticsearch when files are deleted from S3, using a **hybrid approach** that combines real-time and periodic cleanup.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  HYBRID DELETION SYNCHRONIZATION                    │
│                                                                     │
│  ┌──────────────────────────┐      ┌──────────────────────────┐     │
│  │   PRIMARY: SQS Events    │      │  SAFETY NET: Background  │     │
│  │   (Real-time, 99.9%)     │      │   Sync (Periodic, 100%)  │     │
│  └──────────────────────────┘      └──────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Method 1: Real-Time SQS Deletion (Primary)

**Flow:**
```
User deletes file from S3
    ↓
S3 ObjectRemoved:* event
    ↓
SQS Queue receives message
    ↓
Ingestion service polls queue
    ↓
Detects event_type='delete'
    ↓
elasticsearch_service.delete_document_by_s3_key()
    ↓
Document removed from index (< 1 second)
```

**Implementation:**
- **S3 Event Handler**: Detects `ObjectRemoved:*` events and sets `event_type='delete'`
- **Queue Processor**: Passes event_type to callback function
- **Ingestion Pipeline**: Routes deletion events to Elasticsearch
- **Elasticsearch Service**: Uses wildcard query to match `file_path` field

**Configuration:**
```bash
# .env file
SQS_ENABLED=true
SQS_QUEUE_URL=https://sqs.REGION.amazonaws.com/ACCOUNT/QUEUE
```

**S3 Event Configuration:**
```bash
aws s3api put-bucket-notification-configuration \
  --bucket YOUR_BUCKET \
  --notification-configuration '{
    "QueueConfigurations": [{
      "QueueArn": "arn:aws:sqs:REGION:ACCOUNT:QUEUE_NAME",
      "Events": [
        "s3:ObjectCreated:*",
        "s3:ObjectRemoved:*"
      ]
    }]
  }'
```

### Method 2: Background Sync (Safety Net)

**Flow:**
```
Every N hours (configurable):
    ↓
Fetch all S3 keys
    ↓
Fetch all Elasticsearch file_paths
    ↓
Find orphans: (ES keys) - (S3 keys)
    ↓
Delete orphaned documents
    ↓
Log statistics
```

**Implementation:**
- **SyncService**: Runs in background daemon thread
- **Comparison**: Compares S3 bucket contents with Elasticsearch index
- **Cleanup**: Removes documents that no longer exist in S3
- **Scheduling**: Configurable interval (default: 6 hours)

**Configuration:**
```bash
# .env file
ENABLE_BACKGROUND_SYNC=true
SYNC_INTERVAL_HOURS=6
```

### Monitoring

**Logs to watch:**
```
Deleting document: pdf_images/file.pdf
Deleted 1 document(s) for S3 key: pdf_images/file.pdf
Processed and deleted queue message: pdf_images/file.pdf
```

**Background sync logs:**
```
Running background sync check...
Fetching S3 file list...
   Found 15 files in S3
Fetching Elasticsearch document list...
   Found 12 documents in Elasticsearch
No orphaned documents found. Sync complete in 0.28s
```

---

---

## Ingestion Configuration

### Mode Selection

**Configure in `.env`:**

#### Option A: S3-Only Mode (Batch Processing)
```bash
SQS_ENABLED=false
SQS_QUEUE_URL=
FIRST_RUN_FULL_INGEST=true  # Set to true for first run only
```

**Behavior**:
- Scans entire S3 bucket on startup
- Processes all files in `docx_data/`, `pdf_images/`, `xls_data/`
- Shows summary statistics
- Exits when complete (unless background sync enabled)

**Use when**:
- No SQS/SNS infrastructure
- First-time ingestion
- Development/testing

---

#### Option B: SQS Mode (Real-time Processing)
```bash
SQS_ENABLED=true
SQS_QUEUE_URL=https://sqs.REGION.amazonaws.com/ACCOUNT_ID/QUEUE_NAME
FIRST_RUN_FULL_INGEST=false  # Set to false after first ingestion
```

**Behavior**:
- Continuously monitors SQS queue
- Auto-processes new S3 uploads via event notifications
- Auto-removes deleted files from Elasticsearch
- Runs until stopped (Ctrl+C)

**Use when**:
- Production environment
- Real-time ingestion required
- AWS infrastructure available

**Prerequisites**:
1. AWS SQS queue created
2. S3 bucket event notifications configured (ObjectCreated:* and ObjectRemoved:*)

---

#### Option C: Background Sync Only
```bash
SQS_ENABLED=false
ENABLE_BACKGROUND_SYNC=true
SYNC_INTERVAL_HOURS=6
```

**Behavior**:
- Service stays running (doesn't exit)
- Runs periodic sync every N hours
- Cleans up orphaned documents
- No real-time processing

**Use when**:
- SQS not available but need cleanup
- Want eventual consistency
- Lower cost option

---

### Deduplication Configuration

```python
# In pipeline configuration
pipeline_config = PipelineConfig(
    enable_deduplication=True,  # Set False to disable
    ...
)
```

**Statistics tracked**:
- Total files processed
- Successfully indexed
- Duplicates skipped
- Failed

---

## Performance Optimization

### 1. OCR Performance Tuning

**PaddleOCR (Recommended for Production)**
- **Throughput**: ~10-15 pages/second
- **Memory**: 2GB per container
- **Scaling**: Run multiple containers with load balancer

```bash
# Run PaddleOCR instances
docker run -d -p 8088:8088 --name paddle-ocr-1 nasim0086/paddleocr:latest

```

**Granite Vision LM (For High Accuracy)**
- **Throughput**: ~3-5 pages/second
- **Memory**: 6GB per container
- **Scaling**: Limited by GPU/memory

### 2. Elasticsearch Optimization

```bash
# Increase heap size for better performance
docker run -d \
  -e "ES_JAVA_OPTS=-Xms4g -Xmx4g" \
  -m 8GB \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.3
```

**Index Settings**:
```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "5s"
  }
}
```

### 3. Embedding Service Scaling

```bash
# Run multiple embedding service instances
docker run -d -p 8001:8001 --name embed-1 nasim0086/embedding-service:v0.1
docker run -d -p 8002:8001 --name embed-2 nasim0086/embedding-service:v0.1
```

---

## API Endpoints Reference

### Ingestion Pipeline (Internal)

Not exposed externally - runs via `run_ingestion.py`

### Query API

**Base URL**: `http://localhost:8000` (when running FastAPI service)

#### 1. Semantic Search
```bash
POST /search/semantic
Content-Type: application/json

{
  "query": "renewable energy benefits",
  "top_k": 10,
  "filters": {
    "file_type": "pdf"
  }
}

Response:
{
  "results": [
    {
      "doc_id": "energy_report_chunk_5",
      "filename": "energy_report.pdf",
      "content": "Renewable energy benefits...",
      "score": 0.89,
      "metadata": {...}
    }
  ],
  "total": 10,
  "query_time_ms": 45
}
```

#### 2. Keyword Search
```bash
POST /search/keyword
Content-Type: application/json

{
  "query": "solar panel installation",
  "top_k": 10
}
```

#### 3. Hybrid Search
```bash
POST /search/hybrid
Content-Type: application/json

{
  "query": "climate change mitigation",
  "top_k": 10,
  "semantic_weight": 0.6,
  "keyword_weight": 0.4
}
```

---

## Security Considerations

### Production Deployment

1. **Elasticsearch Authentication**
   ```bash
   # Enable xpack security
   -e "xpack.security.enabled=true"
   
   # Generate passwords
   docker exec -it es01 /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic
   ```

2. **API Authentication**
   - Add JWT/API key authentication to FastAPI endpoints
   - Use environment variables for secrets

3. **Network Security**
   - Run services in private Docker network
   - Use reverse proxy (nginx) for external access
   - Enable TLS/SSL certificates

4. **AWS IAM**
   - Use IAM roles instead of access keys
   - Restrict S3 bucket permissions
   - Enable S3 bucket encryption

---

## Monitoring & Logging

### Elasticsearch Monitoring
```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# Index statistics
curl http://localhost:9200/documents_v1/_stats?pretty
```

### Docker Logs
```bash
# PaddleOCR logs
docker logs -f paddle-ocr

# Elasticsearch logs
docker logs -f es01

# All logs
docker logs -f $(docker ps -q)
```

### Application Logs
- Location: `logs/` directory
- Format: JSON structured logging
- Rotation: Daily

---

## Deployment Architecture

### Development Setup
```
┌─────────────────┐
│  Local Machine  │
├─────────────────┤
│ • All Docker    │
│   containers    │
│ • Python env    │
│ • Single node   │
└─────────────────┘
```

### Production Setup (Recommended)
```
┌──────────────────────────────────────────┐
│           Load Balancer (nginx)          │
└─────────────┬────────────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
┌────▼─────┐    ┌─────▼────┐
│  API     │    │  API     │
│  Server  │    │  Server  │
│  Node 1  │    │  Node 2  │
└────┬─────┘    └─────┬────┘
     │                │
     └────────┬───────┘
              │
     ┌────────▼────────┐
     │ Elasticsearch   │
     │   Cluster       │
     │  (3 nodes)      │
     └────────┬────────┘
              │
     ┌────────▼────────┐
     │  S3 + SQS       │
     │  (AWS)          │
     └─────────────────┘
```

---