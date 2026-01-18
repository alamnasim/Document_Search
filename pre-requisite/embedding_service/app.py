"""
Optimized Embedding API Service
High-performance sentence embedding endpoint using sentence-transformers
CPU-optimized for Docker deployment
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
import logging
import time
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global model instance
embed_model = None
MODEL_NAME = 'BAAI/bge-small-en-v1.5'
MODEL_DIMS = 384


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    Loads model once at startup
    """
    global embed_model
    
    # Startup
    logger.info(f"Loading embedding model: {MODEL_NAME}...")
    start_time = time.time()
    
    try:
        embed_model = SentenceTransformer(MODEL_NAME)
        load_time = time.time() - start_time
        logger.info(f" Model loaded successfully in {load_time:.2f}s")
        logger.info(f"Model dimensions: {MODEL_DIMS}")
    except Exception as e:
        logger.error(f" Failed to load model: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down embedding service...")
    embed_model = None


# Initialize FastAPI with lifespan
app = FastAPI(
    title="Embedding API Service",
    description="High-performance sentence embedding API using BGE-small-en-v1.5",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class EmbedRequest(BaseModel):
    """Request model for single text embedding"""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to embed")
    normalize: bool = Field(True, description="Whether to normalize embeddings")
    
    model_config = {"protected_namespaces": ()}
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty or only whitespace")
        return v.strip()


class BatchEmbedRequest(BaseModel):
    """Request model for batch text embedding"""
    texts: List[str] = Field(..., min_items=1, max_items=100, description="List of texts to embed")
    normalize: bool = Field(True, description="Whether to normalize embeddings")
    batch_size: int = Field(32, ge=1, le=128, description="Batch size for processing")
    
    model_config = {"protected_namespaces": ()}
    
    @field_validator('texts')
    @classmethod
    def validate_texts(cls, v):
        cleaned = [text.strip() for text in v if text.strip()]
        if not cleaned:
            raise ValueError("All texts are empty")
        return cleaned


class EmbedResponse(BaseModel):
    """Response model for single embedding"""
    vector: List[float] = Field(..., description="Embedding vector")
    dims: int = Field(..., description="Vector dimensions")
    text_length: int = Field(..., description="Original text length")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class BatchEmbedResponse(BaseModel):
    """Response model for batch embeddings"""
    vectors: List[List[float]] = Field(..., description="List of embedding vectors")
    dims: int = Field(..., description="Vector dimensions")
    count: int = Field(..., description="Number of embeddings")
    processing_time_ms: float = Field(..., description="Total processing time")
    avg_time_per_item_ms: float = Field(..., description="Average time per embedding")


class HealthResponse(BaseModel):
    """Health check response"""
    model_config = {"protected_namespaces": ()}
    
    status: str
    model: str
    dimensions: int
    model_loaded: bool


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Embedding API",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "dimensions": MODEL_DIMS,
        "endpoints": {
            "health": "/health",
            "embed": "/embed",
            "batch_embed": "/batch-embed",
            "similarity": "/similarity",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if embed_model is not None else "unhealthy",
        model=MODEL_NAME,
        dimensions=MODEL_DIMS,
        model_loaded=embed_model is not None
    )


@app.post("/embed", response_model=EmbedResponse)
async def create_embedding(request: EmbedRequest):
    """Generate embedding for a single text"""
    if embed_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model not loaded"
        )
    
    try:
        start_time = time.time()
        
        vector = embed_model.encode(
            request.text,
            normalize_embeddings=request.normalize,
            show_progress_bar=False
        )
        
        processing_time = (time.time() - start_time) * 1000
        vector_list = vector.tolist()
        
        logger.info(f"Generated embedding for text of length {len(request.text)} in {processing_time:.2f}ms")
        
        return EmbedResponse(
            vector=vector_list,
            dims=len(vector_list),
            text_length=len(request.text),
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding: {str(e)}"
        )


@app.post("/batch-embed", response_model=BatchEmbedResponse)
async def create_batch_embeddings(request: BatchEmbedRequest):
    """Generate embeddings for multiple texts in batch"""
    if embed_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model not loaded"
        )
    
    try:
        start_time = time.time()
        
        vectors = embed_model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            batch_size=request.batch_size,
            show_progress_bar=False
        )
        
        processing_time = (time.time() - start_time) * 1000
        vectors_list = vectors.tolist()
        
        count = len(vectors_list)
        avg_time = processing_time / count if count > 0 else 0
        
        logger.info(f"Generated {count} embeddings in {processing_time:.2f}ms (avg: {avg_time:.2f}ms per item)")
        
        return BatchEmbedResponse(
            vectors=vectors_list,
            dims=MODEL_DIMS,
            count=count,
            processing_time_ms=round(processing_time, 2),
            avg_time_per_item_ms=round(avg_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate batch embeddings: {str(e)}"
        )


@app.post("/similarity")
async def compute_similarity(text1: str, text2: str):
    """Compute cosine similarity between two texts"""
    if embed_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model not loaded"
        )
    
    try:
        vectors = embed_model.encode(
            [text1, text2],
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        similarity = np.dot(vectors[0], vectors[1])
        
        return {
            "text1": text1[:100] + "..." if len(text1) > 100 else text1,
            "text2": text2[:100] + "..." if len(text2) > 100 else text2,
            "similarity": float(similarity),
            "interpretation": (
                "Very similar" if similarity > 0.8 else
                "Similar" if similarity > 0.6 else
                "Somewhat similar" if similarity > 0.4 else
                "Different"
            )
        }
        
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute similarity: {str(e)}"
        )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
