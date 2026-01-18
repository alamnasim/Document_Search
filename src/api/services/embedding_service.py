"""
Embedding Service for generating vector embeddings
"""
import requests
from typing import List, Dict, Any, Union
from src.api.config import Config


class EmbeddingService:
    """Service to generate embeddings using the configured embedding model"""
    
    def __init__(self):
        """Initialize embedding service with configuration"""
        self.endpoint = Config.EMBEDDING_ENDPOINT
        self.model_name = Config.EMBEDDING_MODEL_NAME
        print(f" EmbeddingService initialized: {self.model_name} at {self.endpoint}")
    
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
                print("  Empty text provided for embedding")
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
                print(f" Embedding API error: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            print(" Embedding request timeout")
            return []
        except requests.exceptions.ConnectionError:
            print(" Cannot connect to embedding service - ensure it's running")
            return []
        except Exception as e:
            print(f" Error generating embedding: {e}")
            return []
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
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
            
            payload = {
                "model": self.model_name,
                "texts": valid_texts,
                "normalize": True
            }
            
            response = requests.post(
                self.endpoint + "/batch" if not self.endpoint.endswith("/batch") else self.endpoint,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                vectors = result.get("vectors", [])
                return vectors
            else:
                print(f" Batch embedding API error: {response.status_code}")
                # Fall back to individual embeddings
                return [self.generate_embedding(text) for text in valid_texts]
                
        except Exception as e:
            print(f" Error in batch embedding: {e}")
            # Fall back to individual embeddings
            return [self.generate_embedding(text) for text in texts]
    
    def generate_chunk_embeddings(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for text chunks and add them to chunk objects
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
            
        Returns:
            list: Chunks with added 'embedding' field
        """
        try:
            # Extract texts from chunks
            texts = [chunk.get("text", "") for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.generate_embeddings_batch(texts)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                if i < len(embeddings) and embeddings[i]:
                    chunk["embedding"] = embeddings[i]
                else:
                    chunk["embedding"] = []
            
            return chunks
            
        except Exception as e:
            print(f" Error generating chunk embeddings: {e}")
            # Return chunks without embeddings
            for chunk in chunks:
                chunk["embedding"] = []
            return chunks
