"""
PaddleOCR service for document OCR
Connects to PaddleOCR API running in Docker container
"""
import requests
import os
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OCRService:
    """
    Client for PaddleOCR service
    Sends PDF and image files to OCR engine for text extraction
    """
    
    def __init__(self, host: str = "http://localhost", port: int = 8088):
        """
        Initialize OCR service client
        
        Args:
            host: OCR service host (default: http://localhost)
            port: OCR service port (default: 8088)
        """
        self.url = f"{host}:{port}/ocr"
        self.host = host
        self.port = port
        logger.info(f"Initialized OCR service client: {self.url}")
    
    def extract_text_from_file(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Sends a PDF or Image to the OCR service
        
        Args:
            file_content: File bytes (PDF or image)
            file_name: Name of the file for logging
            
        Returns:
            dict: {
                'success': bool,
                'content': str (extracted text),
                'total_pages': int (for PDFs),
                'processing_time': float,
                'error': str (if failed)
            }
        """
        start_time = time.time()
        
        try:
            logger.info(f"Sending {file_name} to OCR engine at {self.url}")
            
            # Prepare file for upload
            files = {
                "file": (file_name, file_content, "application/octet-stream")
            }
            
            # Send to OCR service
            response = requests.post(
                self.url,
                files=files,
                timeout=120  # 2 minutes timeout
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                total_pages = data.get('total_pages', 1)
                content = data.get("content", "")
                
                logger.info(
                    f"OCR Success: {file_name} - "
                    f"{total_pages} page(s), "
                    f"{len(content)} chars, "
                    f"{elapsed:.2f}s"
                )
                
                return {
                    "success": True,
                    "content": content,
                    "total_pages": total_pages,
                    "processing_time": elapsed
                }
            else:
                error_msg = f"Server error ({response.status_code}): {response.text}"
                logger.error(f"OCR failed for {file_name}: {error_msg}")
                
                return {
                    "success": False,
                    "content": "",
                    "error": error_msg,
                    "processing_time": elapsed
                }
                
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed: Is PaddleOCR service running at {self.url}?"
            logger.error(f"OCR connection error for {file_name}: {error_msg}")
            
            return {
                "success": False,
                "content": "",
                "error": error_msg,
                "processing_time": time.time() - start_time
            }
            
        except requests.exceptions.Timeout as e:
            error_msg = f"OCR request timed out after {time.time() - start_time:.1f}s"
            logger.error(f"OCR timeout for {file_name}: {error_msg}")
            
            return {
                "success": False,
                "content": "",
                "error": error_msg,
                "processing_time": time.time() - start_time
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"OCR error for {file_name}: {error_msg}", exc_info=True)
            
            return {
                "success": False,
                "content": "",
                "error": error_msg,
                "processing_time": time.time() - start_time
            }
    
    def test_connection(self) -> bool:
        """
        Test if OCR service is available
        
        Returns:
            bool: True if service is reachable, False otherwise
        """
        try:
            # Try to reach the service (assuming a health endpoint exists)
            response = requests.get(
                f"{self.host}:{self.port}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            logger.warning(f"OCR service not available at {self.url}")
            return False


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize client
    ocr_client = OCRService(host="http://localhost", port=8088)
    
    # Test with a PDF
    pdf_path = "/home/nasim-pc/Desktop/document.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        result = ocr_client.extract_text_from_file(pdf_content, "document.pdf")
        if result["success"]:
            print("\n--- Extracted Text Preview ---")
            print(result["content"][:500] + "...")
    
    # Test with an image
    image_path = "/home/nasim-pc/Desktop/photo.jpg"
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            image_content = f.read()
        
        result = ocr_client.extract_text_from_file(image_content, "photo.jpg")
        if result["success"]:
            print("\n--- Image Text ---")
            print(result["content"])
