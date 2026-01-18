"""
Text chunking processor using RecursiveCharacterTextSplitter
"""
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..models.schemas import DocumentChunk, ParserConfig
from ..exceptions import ChunkingException


logger = logging.getLogger(__name__)


class TextChunker:
    """Processor for chunking text into smaller pieces"""
    
    def __init__(self, config: ParserConfig):
        """
        Initialize text chunker
        
        Args:
            config: Parser configuration with chunk settings
        """
        self.config = config
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
            is_separator_regex=False
        )
        logger.info(
            f"TextChunker initialized: size={config.chunk_size}, "
            f"overlap={config.chunk_overlap}"
        )
    
    def chunk_text(self, text: str) -> List[DocumentChunk]:
        """
        Chunk text into smaller pieces
        
        Args:
            text: Input text to chunk
            
        Returns:
            list: List of DocumentChunk objects
            
        Raises:
            ChunkingException: If chunking fails
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for chunking")
                return []
            
            # Split text
            text_chunks = self.splitter.split_text(text)
            
            # Create chunk objects
            chunks = []
            for idx, chunk_text in enumerate(text_chunks):
                if len(chunk_text.strip()) < self.config.min_chunk_size:
                    logger.debug(
                        f"Skipping short chunk {idx}: {len(chunk_text)} chars"
                    )
                    continue
                
                try:
                    chunk = DocumentChunk(
                        text=chunk_text,
                        position=idx,
                        char_count=len(chunk_text)
                    )
                    chunks.append(chunk)
                except Exception as e:
                    logger.warning(f"Failed to create chunk {idx}: {e}")
                    continue
            
            logger.info(f"Created {len(chunks)} chunks from text")
            return chunks
            
        except Exception as e:
            raise ChunkingException(
                "Failed to chunk text",
                original_error=e
            )
