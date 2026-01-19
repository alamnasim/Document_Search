"""
Abstract base parser for document extraction
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

from ..models.schemas import ParserConfig, DocumentMetadata
from ..exceptions import ParserException


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for document parsers"""
    
    def __init__(self, config: ParserConfig):
        """
        Initialize parser with configuration
        
        Args:
            config: Parser configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def parse(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse document and extract content
        
        Args:
            file_content: Raw file bytes
            file_name: Name of the file
            
        Returns:
            dict: Extracted content with metadata
            
        Raises:
            ParserException: If parsing fails
        """
        pass
    
    def _validate_content(self, content: str) -> bool:
        """
        Validate extracted content
        
        Args:
            content: Extracted text content
            
        Returns:
            bool: True if valid
        """
        if not content:
            return False
        
        if not content.strip():
            return False
        
        if len(content.strip()) < self.config.min_chunk_size:
            self.logger.warning(f"Content too short: {len(content)} chars")
            return False
        
        return True
    
    def _create_result(
        self,
        content: str,
        metadata: DocumentMetadata,
        structured_data: Any = None
    ) -> Dict[str, Any]:
        """
        Create standardized parser result
        
        Args:
            content: Extracted text
            metadata: Document metadata
            structured_data: Optional structured data
            
        Returns:
            dict: Standardized result
        """
        result = {
            "content": content,
            "metadata": metadata,
            "success": True
        }
        
        if structured_data is not None:
            result["structured_data"] = structured_data
        
        return result
    
    def _handle_error(self, error: Exception, file_name: str) -> Dict[str, Any]:
        """
        Handle parsing errors
        
        Args:
            error: The exception that occurred
            file_name: Name of the file being parsed
            
        Returns:
            dict: Error result
        """
        error_msg = f"Failed to parse {file_name}: {str(error)}"
        self.logger.error(error_msg, exc_info=True)
        
        return {
            "content": "",
            "metadata": DocumentMetadata(),
            "success": False,
            "error": error_msg
        }
