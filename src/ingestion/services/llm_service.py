"""
LLM Service for document OCR and extraction using qwen2.5-vl-3b-instruct
"""
import base64
import requests
import logging
from typing import Dict, Any, Optional
from ..config import IngestionConfig


logger = logging.getLogger(__name__)


class LLMService:
    """Service to interact with qwen2.5-vl-3b-instruct for OCR and text extraction"""
    
    def __init__(self, endpoint: str = None, model_name: str = None, api_key: str = None):
        """Initialize LLM service with configuration"""
        self.endpoint = endpoint or IngestionConfig.LLM_ENDPOINT
        self.model_name = model_name or IngestionConfig.LLM_MODEL_NAME
        self.api_key = api_key or IngestionConfig.LLM_API_KEY
        logger.info(f" LLMService initialized: {self.model_name} at {self.endpoint}")
    
    def extract_text_from_pdf(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        Extract text from PDF using vision LLM
        
        Args:
            file_content: PDF file bytes
            file_name: Name of the PDF file
            
        Returns:
            dict: Extracted text and metadata
        """
        try:
            # Convert PDF pages to images and extract text
            # For simplicity, we'll send the file data directly
            # In production, you might want to convert PDF to images first
            
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            prompt = """Please extract all text content from this document. 
Maintain the structure and formatting as much as possible. 
Include any tables, lists, and structured content."""
            
            response = self._call_llm_api(
                prompt=prompt,
                image_data=base64_content,
                file_type="pdf"
            )
            
            if response and response.get("success"):
                extracted_text = response.get("text", "")
                return {
                    "content": extracted_text,
                    "success": True,
                    "metadata": {
                        "extraction_method": "llm_vision",
                        "model": self.model_name
                    }
                }
            else:
                return {
                    "content": "",
                    "success": False,
                    "error": response.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_name}: {e}")
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    def extract_text_from_image(self, file_content, file_name: str) -> Dict[str, Any]:
        """
        Extract text from image using vision LLM (OCR)
        
        Args:
            file_content: Image file bytes OR base64 string
            file_name: Name of the image file
            
        Returns:
            dict: Extracted text and metadata
        """
        try:
            # Handle both bytes and base64 string input
            if isinstance(file_content, str):
                base64_content = file_content
            else:
                base64_content = base64.b64encode(file_content).decode('utf-8')
            
            prompt = """Please perform OCR on this image and extract all text content. 
Maintain the reading order and structure. 
If there are tables or structured layouts, preserve them."""
            
            response = self._call_llm_api(
                prompt=prompt,
                image_data=base64_content,
                file_type="image"
            )
            
            if response and response.get("success"):
                extracted_text = response.get("text", "")
                return {
                    "content": extracted_text,
                    "success": True,
                    "metadata": {
                        "extraction_method": "llm_ocr",
                        "model": self.model_name
                    }
                }
            else:
                return {
                    "content": "",
                    "success": False,
                    "error": response.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Error extracting text from image {file_name}: {e}")
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }
    
    def _call_llm_api(
        self,
        prompt: str,
        image_data: str,
        file_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Call the LLM API endpoint
        
        Args:
            prompt: The text prompt
            image_data: Base64 encoded image/document data
            file_type: Type of file being processed
            
        Returns:
            dict: API response
        """
        try:
            # Prepare the request payload for OpenAI-compatible API
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add API key if provided
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.1
            }
            
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=300  # 5 minutes - LLM vision processing can be very slow
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract text from OpenAI-compatible response
                extracted_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return {
                    "success": True,
                    "text": extracted_text
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection error - ensure LLM service is running"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
