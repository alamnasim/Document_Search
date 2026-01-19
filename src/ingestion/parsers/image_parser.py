"""
Image parser using LLM vision OCR or PaddleOCR
"""
import io
from typing import Dict, Any, Optional
import logging
from PIL import Image

from .base_parser import BaseParser
from ..models.schemas import ParserConfig, DocumentMetadata, ExtractionMethod
from ..exceptions import ParserException
from ..services.llm_service import LLMService
from ..services.ocr_service import OCRService
from ..processors.text_cleaner import TextCleaner


logger = logging.getLogger(__name__)


class ImageParser(BaseParser):
    """Parser for images using LLM vision OCR or PaddleOCR"""
    
    def __init__(
        self, 
        config: ParserConfig, 
        llm_service: Optional[LLMService] = None,
        ocr_service: Optional[OCRService] = None,
        use_llm: bool = True
    ):
        """
        Initialize image parser
        
        Args:
            config: Parser configuration
            llm_service: LLM service instance (if use_llm=True)
            ocr_service: OCR service instance (if use_llm=False)
            use_llm: If True, use LLM for OCR; if False, use PaddleOCR
        """
        super().__init__(config)
        self.use_llm = use_llm
        self.llm_service = llm_service
        self.ocr_service = ocr_service
        self.text_cleaner = TextCleaner()
        
        if use_llm and not llm_service:
            raise ValueError("LLM service required when use_llm=True")
        
        if not use_llm and not ocr_service:
            raise ValueError("OCR service required when use_llm=False")
    
    def parse(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse image using LLM vision OCR or PaddleOCR
        
        Args:
            file_content: Image file bytes
            file_name: Name of the image file
            
        Returns:
            dict: Extracted content and metadata
            
        Raises:
            ParserException: If parsing fails
        """
        if self.use_llm:
            return self._parse_with_llm(file_content, file_name)
        else:
            return self._parse_with_ocr(file_content, file_name)
    
    def _parse_with_ocr(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse image using PaddleOCR service
        
        Args:
            file_content: Image file bytes
            file_name: Name of the image file
            
        Returns:
            dict: Extracted content and metadata
        """
        try:
            self.logger.info(f"Parsing image with PaddleOCR: {file_name}")
            
            # Extract image metadata
            try:
                image = Image.open(io.BytesIO(file_content))
                image_metadata = {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                }
            except Exception as e:
                self.logger.warning(f"Failed to extract image metadata: {e}")
                image_metadata = {}
            
            # Extract text using PaddleOCR
            result = self.ocr_service.extract_text_from_file(file_content, file_name)
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                raise ParserException(f"PaddleOCR failed: {error_msg}")
            
            content = result.get("content", "")
            
            # Clean the PaddleOCR output (handle newlines and spacing)
            content = self.text_cleaner.clean_paddleocr_output(content)
            
            if not self._validate_content(content):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.PADDLE_OCR,
                **image_metadata
            )
            
            self.logger.info(
                f"Successfully parsed image with PaddleOCR: {file_name} "
                f"({len(content)} chars)"
            )
            
            return self._create_result(content, metadata)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing image with OCR: {file_name}",
                original_error=e
            )
    
    def _parse_with_llm(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse image using LLM vision model
        
        Args:
            file_content: Image file bytes
            file_name: Name of the image file
            
        Returns:
            dict: Extracted content and metadata
        """
        try:
            self.logger.info(f"Parsing image with LLM: {file_name}")
            
            # Extract image metadata
            try:
                image = Image.open(io.BytesIO(file_content))
                image_metadata = {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                }
            except Exception as e:
                self.logger.warning(f"Failed to extract image metadata: {e}")
                image_metadata = {}
            
            # Extract text using LLM
            result = self.llm_service.extract_text_from_image(
                file_content,
                file_name
            )
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                raise ParserException(
                    f"LLM OCR failed: {error_msg}"
                )
            
            content = result.get("content", "")
            
            # Clean the docling output (remove location markers and HTML tags)
            content = self.text_cleaner.clean_docling_output(content)
            
            if not self._validate_content(content):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.LLM_OCR,
                model_used=self.llm_service.model_name,
                **image_metadata
            )
            
            self.logger.info(
                f"Successfully parsed image with LLM: {file_name} "
                f"({len(content)} chars)"
            )
            
            return self._create_result(content, metadata)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing image with LLM: {file_name}",
                original_error=e
            )
