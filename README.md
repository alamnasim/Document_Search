# Document_Search
Production-ready document search engine: ingests files from aws S3, performs OCR (PaddleOCR/Vision LM), generates embeddings (BGE), indexes to Elasticsearch for semantic search. Features: hybrid deletion sync (real-time SQS + background), auto-deduplication, multi-format support (PDF/DOCX/Excel/CSV/Images).
