"""
Pydantic models for data validation and serialization
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class FileType(str, Enum):
    """Supported file types"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIFF = "tiff"
    CSV = "csv"
    XLSX = "xlsx"
    XLS = "xls"


class ExtractionMethod(str, Enum):
    """Text extraction methods"""
    LLM_VISION = "llm_vision"
    LLM_OCR = "llm_ocr"
    PADDLE_OCR = "paddle_ocr"
    MARKITDOWN = "markitdown"
    PANDAS = "pandas"


class S3FileInfo(BaseModel):
    """Information about a file in S3"""
    s3_key: str
    file_name: str
    file_size: int
    content_type: str
    last_modified: datetime
    presigned_url: Optional[str] = None
    bucket_name: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DocumentMetadata(BaseModel):
    """Document metadata"""
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extraction_method: Optional[ExtractionMethod] = None
    model_used: Optional[str] = None
    page_count: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    column_names: Optional[List[str]] = None
    sheets: Optional[List[str]] = None
    
    class Config:
        use_enum_values = True


class DocumentChunk(BaseModel):
    """A text chunk with embedding"""
    text: str
    position: int
    char_count: int
    embedding: List[float] = Field(default_factory=list)
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Chunk text cannot be empty')
        return v
    
    @validator('embedding')
    def embedding_dimensions(cls, v):
        if v and len(v) not in [0, 384]:  # Allow empty or 384-dim
            raise ValueError('Embedding must be 384 dimensions or empty')
        return v


class ProcessedDocument(BaseModel):
    """Fully processed document ready for indexing"""
    doc_id: str
    file_name: str
    file_path: str
    presigned_url: Optional[str] = None
    file_type: FileType
    file_size: int
    upload_date: datetime
    content: str
    content_hash: Optional[str] = None  # SHA256 hash for deduplication
    chunks: List[DocumentChunk]
    metadata: DocumentMetadata
    structured_data: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IngestionResult(BaseModel):
    """Result of document ingestion"""
    success: bool
    doc_id: Optional[str] = None
    file_name: str
    file_path: str
    message: str
    processing_time: Optional[float] = None
    error: Optional[str] = None
    chunks_created: int = 0
    embeddings_generated: int = 0
    # Detailed timing breakdown
    timing: Dict[str, float] = Field(default_factory=dict)
    is_duplicate: bool = False


class ParserConfig(BaseModel):
    """Configuration for document parsers"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 50
    enable_embeddings: bool = True
    llm_timeout: int = 60
    embedding_timeout: int = 30


class PipelineConfig(BaseModel):
    """Configuration for the ingestion pipeline"""
    batch_size: int = 10
    max_workers: int = 4
    enable_queue: bool = True
    queue_poll_interval: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    presigned_url_expiration: int = 3600
    enable_deduplication: bool = True
