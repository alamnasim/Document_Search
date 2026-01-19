"""
Embedding Service for generating vector embeddings
"""
import requests
import logging
from typing import List, Dict, Any, Union
from ..config import IngestionConfig


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service to generate embeddings using the configured embedding model"""
    
    def __init__(self, endpoint: str = None, model_name: str = None):
        """Initialize embedding service with configuration"""
        self.endpoint = endpoint or IngestionConfig.EMBEDDING_ENDPOINT
        self.model_name = model_name or IngestionConfig.EMBEDDING_MODEL_NAME
        logger.info(f" EmbeddingService initialized: {self.model_name} at {self.endpoint}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            list: Embedding vector
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return []
            
            payload = {
                "model": self.model_name,
                "text": text.strip(),
                "normalize": True
            }
            
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                vector = result.get("vector", [])
                return vector
            else:
                logger.error(f"Embedding API error: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("Embedding request timeout")
            return []
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to embedding service - ensure it's running")
            return []
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (calls single endpoint for each)
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            list: List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            # Filter out empty texts
            valid_texts = [t.strip() for t in texts if t and t.strip()]
            
            if not valid_texts:
                return []
            
            # Generate embeddings one by one (no batch endpoint available)
            embeddings = []
            for text in valid_texts:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
            
            return embeddings
                
        except Exception as e:
            logger.error(f"Error in batch embedding: {e}")
            return []
    
    def generate_chunk_embeddings(
        self,
        chunks: List[Any]
    ) -> List[Any]:
        """
        Generate embeddings for text chunks and add them to chunk objects
        
        Args:
            chunks: List of DocumentChunk Pydantic models
            
        Returns:
            list: Chunks with updated embedding field
        """
        try:
            # Extract texts from chunks (handle both dicts and Pydantic models)
            texts = []
            for chunk in chunks:
                if hasattr(chunk, 'text'):
                    texts.append(chunk.text)
                elif isinstance(chunk, dict):
                    texts.append(chunk.get("text", ""))
                else:
                    texts.append("")
            
            # Generate embeddings
            embeddings = self.generate_embeddings_batch(texts)
            
            # Add embeddings to chunks
            updated_chunks = []
            for i, chunk in enumerate(chunks):
                if i < len(embeddings) and embeddings[i]:
                    # For Pydantic models, create new instance with updated embedding
                    if hasattr(chunk, 'copy'):
                        updated_chunk = chunk.copy(update={"embedding": embeddings[i]})
                        updated_chunks.append(updated_chunk)
                    elif isinstance(chunk, dict):
                        chunk["embedding"] = embeddings[i]
                        updated_chunks.append(chunk)
                    else:
                        updated_chunks.append(chunk)
                else:
                    # Empty embedding
                    if hasattr(chunk, 'copy'):
                        updated_chunk = chunk.copy(update={"embedding": []})
                        updated_chunks.append(updated_chunk)
                    elif isinstance(chunk, dict):
                        chunk["embedding"] = []
                        updated_chunks.append(chunk)
                    else:
                        updated_chunks.append(chunk)
            
            return updated_chunks
            
        except Exception as e:
            logger.error(f"Error generating chunk embeddings: {e}")
            # Return chunks without embeddings
            updated_chunks = []
            for chunk in chunks:
                if hasattr(chunk, 'copy'):
                    updated_chunk = chunk.copy(update={"embedding": []})
                    updated_chunks.append(updated_chunk)
                elif isinstance(chunk, dict):
                    chunk["embedding"] = []
                    updated_chunks.append(chunk)
                else:
                    updated_chunks.append(chunk)
            return updated_chunks
