"""
DOCX parser using MarkItDown
"""
import os
import tempfile
from typing import Dict, Any
import logging

from markitdown import MarkItDown

from .base_parser import BaseParser
from ..models.schemas import ParserConfig, DocumentMetadata, ExtractionMethod
from ..exceptions import ParserException


logger = logging.getLogger(__name__)


class DOCXParser(BaseParser):
    """Parser for DOCX documents using MarkItDown"""
    
    def __init__(self, config: ParserConfig):
        """
        Initialize DOCX parser
        
        Args:
            config: Parser configuration
        """
        super().__init__(config)
        self.markitdown = MarkItDown()
    
    def parse(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse DOCX document using MarkItDown
        
        Args:
            file_content: DOCX file bytes
            file_name: Name of the DOCX file
            
        Returns:
            dict: Extracted content and metadata
            
        Raises:
            ParserException: If parsing fails
        """
        temp_path = None
        try:
            self.logger.info(f"Parsing DOCX: {file_name}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode='wb',
                suffix='.docx',
                delete=False
            ) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
            
            # Convert with MarkItDown
            result = self.markitdown.convert(temp_path)
            content = result.text_content
            
            if not self._validate_content(content):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.MARKITDOWN,
                format="docx"
            )
            
            self.logger.info(
                f"Successfully parsed DOCX: {file_name} "
                f"({len(content)} chars)"
            )
            
            return self._create_result(content, metadata)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing DOCX {file_name}",
                original_error=e
            )
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp file: {e}")
