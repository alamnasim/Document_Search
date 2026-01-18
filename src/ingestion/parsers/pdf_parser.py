"""
PDF parser using PyMuPDF + LLM vision model or PaddleOCR
Converts PDF pages to images then sends to LLM or OCR engine
"""
from typing import Dict, Any, Optional
import logging
import io
import base64

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from .base_parser import BaseParser
from ..models.schemas import ParserConfig, DocumentMetadata, ExtractionMethod
from ..exceptions import ParserException
from ..services.llm_service import LLMService
from ..services.ocr_service import OCRService
from ..processors.text_cleaner import TextCleaner


logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """Parser for PDF documents using PyMuPDF + LLM vision or PaddleOCR"""
    
    def __init__(
        self, 
        config: ParserConfig, 
        llm_service: Optional[LLMService] = None,
        ocr_service: Optional[OCRService] = None,
        use_llm: bool = True
    ):
        """
        Initialize PDF parser
        
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
        
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available, PDF parsing may fail")
        
        if use_llm and not llm_service:
            raise ValueError("LLM service required when use_llm=True")
        
        if not use_llm and not ocr_service:
            raise ValueError("OCR service required when use_llm=False")
    
    def parse(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse PDF document using LLM vision or PaddleOCR
        
        Args:
            file_content: PDF file bytes
            file_name: Name of the PDF file
            
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
        Parse PDF using PaddleOCR service
        
        Args:
            file_content: PDF file bytes
            file_name: Name of the PDF file
            
        Returns:
            dict: Extracted content and metadata
        """
        try:
            self.logger.info(f"Parsing PDF with PaddleOCR: {file_name}")
            
            # Send entire PDF to OCR service
            result = self.ocr_service.extract_text_from_file(file_content, file_name)
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                raise ParserException(f"PaddleOCR failed: {error_msg}")
            
            content = result.get("content", "")
            page_count = result.get("total_pages", 1)
            
            # Clean the PaddleOCR output (handle newlines and spacing)
            content = self.text_cleaner.clean_paddleocr_output(content)
            
            if not self._validate_content(content):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.PADDLE_OCR,
                page_count=page_count
            )
            
            self.logger.info(
                f"Successfully parsed PDF with PaddleOCR: {file_name} "
                f"({page_count} pages, {len(content)} chars)"
            )
            
            return self._create_result(content, metadata)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing PDF with OCR: {file_name}",
                original_error=e
            )
    
    def _parse_with_llm(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Parse PDF using LLM vision model
        
        Args:
            file_content: PDF file bytes
            file_name: Name of the PDF file
            
        Returns:
            dict: Extracted content and metadata
        """
        try:
            self.logger.info(f"Parsing PDF: {file_name}")
            
            if not PYMUPDF_AVAILABLE:
                raise ParserException("PyMuPDF is not installed. Install with: pip install PyMuPDF")
            
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=file_content, filetype="pdf")
            page_count = len(pdf_doc)
            
            self.logger.info(f"PDF has {page_count} pages")
            
            # Extract text from each page
            full_text = ""
            
            for page_index in range(page_count):
                page = pdf_doc[page_index]
                
                # Convert page to image
                # Matrix(1.5, 1.5) means 1.5x zoom = 108 DPI (default is 72 DPI)
                # Lower DPI to reduce image size and processing time
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_bytes = pix.tobytes("png")
                
                # Encode to base64
                base64_image = base64.b64encode(img_bytes).decode('utf-8')
                
                self.logger.info(f"Processing page {page_index + 1}/{page_count} ({len(img_bytes)} bytes, {len(base64_image)} base64 chars)")
                
                # Send to LLM
                result = self.llm_service.extract_text_from_image(
                    base64_image,
                    f"{file_name} - Page {page_index + 1}"
                )
                
                if not result.get("success"):
                    error_msg = result.get("error", "Unknown error")
                    self.logger.warning(
                        f"Failed to extract text from page {page_index + 1}: {error_msg}"
                    )
                    continue
                
                page_text = result.get("content", "")
                if page_text:
                    full_text += f"\n--- Page {page_index + 1} ---\n{page_text}\n"
            
            pdf_doc.close()
            
            # Clean the docling output (remove location markers and HTML tags)
            full_text = self.text_cleaner.clean_docling_output(full_text)
            
            if not self._validate_content(full_text):
                raise ParserException("Extracted content is empty or invalid")
            
            # Create metadata
            metadata = DocumentMetadata(
                extraction_method=ExtractionMethod.LLM_VISION,
                model_used=self.llm_service.model_name,
                page_count=page_count
            )
            
            self.logger.info(
                f"Successfully parsed PDF: {file_name} "
                f"({page_count} pages, {len(full_text)} chars)"
            )
            
            return self._create_result(full_text, metadata)
            
        except ParserException:
            raise
        except Exception as e:
            raise ParserException(
                f"Unexpected error parsing PDF {file_name}",
                original_error=e
            )
