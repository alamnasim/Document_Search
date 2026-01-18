"""
Document Ingestion Pipeline Module

This module provides a modular, OOP-based ingestion pipeline for processing
documents from S3, extracting text, generating embeddings, and indexing in Elasticsearch.
"""

from .pipeline.ingestion_pipeline import IngestionPipeline
from .models.schemas import (
    DocumentMetadata,
    DocumentChunk,
    ProcessedDocument,
    IngestionResult
)

__all__ = [
    "IngestionPipeline",
    "DocumentMetadata",
    "DocumentChunk",
    "ProcessedDocument",
    "IngestionResult"
]
