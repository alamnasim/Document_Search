#!/usr/bin/env python3
"""
Setup validation script for the ingestion pipeline
Tests all components before running actual ingestion
"""
import os
import sys
import logging
import importlib.util
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class SetupValidator:
    """Validates all setup requirements"""
    
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def print_header(self):
        """Print test header"""
        print("\n" + "=" * 70)
        print("🔍 INGESTION PIPELINE SETUP VALIDATION")
        print("=" * 70)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")
    
    def test_section(self, title):
        """Print section header"""
        print(f"\n{'─' * 70}")
        print(f"📋 {title}")
        print('─' * 70)
    
    def test_pass(self, message):
        """Record passed test"""
        print(f" {message}")
        self.passed.append(message)
    
    def test_fail(self, message, error=None):
        """Record failed test"""
        msg = f" {message}"
        if error:
            msg += f"\n   Error: {error}"
        print(msg)
        self.failed.append(message)
    
    def test_warning(self, message):
        """Record warning"""
        print(f"  {message}")
        self.warnings.append(message)
    
    def test_python_packages(self):
        """Test if all required packages are installed"""
        self.test_section("1. Python Packages")
        
        required_packages = [
            ('dotenv', 'python-dotenv'),
            ('boto3', 'boto3'),
            ('botocore', 'botocore'),
            ('elasticsearch', 'elasticsearch'),
            ('requests', 'requests'),
            ('fitz', 'PyMuPDF'),
            ('markitdown', 'markitdown'),
            ('pandas', 'pandas'),
            ('openpyxl', 'openpyxl'),
            ('PIL', 'Pillow'),
            ('langchain_text_splitters', 'langchain-text-splitters'),
            ('pydantic', 'pydantic')
        ]
        
        for module_name, package_name in required_packages:
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                self.test_pass(f"{package_name} is installed")
            else:
                self.test_fail(f"{package_name} is NOT installed", 
                              f"Install with: pip install {package_name}")
    
    def test_environment_variables(self):
        """Test if .env file exists and required variables are set"""
        self.test_section("2. Environment Configuration")
        
        from src.ingestion.config import IngestionConfig
        
        # Check .env file in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, '.env')
        if os.path.exists(env_path):
            self.test_pass(f".env file exists at {env_path}")
        else:
            self.test_fail(".env file NOT found", f"Expected at: {env_path}")
        
        # Check required variables
        required_vars = {
            'AWS_ACCESS_KEY_ID': IngestionConfig.AWS_ACCESS_KEY_ID,
            'AWS_SECRET_ACCESS_KEY': IngestionConfig.AWS_SECRET_ACCESS_KEY,
            'AWS_REGION': IngestionConfig.AWS_REGION,
            'S3_BUCKET_NAME': IngestionConfig.S3_BUCKET_NAME,
            'ELASTICSEARCH_HOST': IngestionConfig.ELASTICSEARCH_HOST,
            'ELASTICSEARCH_PORT': IngestionConfig.ELASTICSEARCH_PORT,
            'ELASTICSEARCH_INDEX': IngestionConfig.ELASTICSEARCH_INDEX,
            'EMBEDDING_ENDPOINT': IngestionConfig.EMBEDDING_ENDPOINT,
            'EMBEDDING_MODEL_NAME': IngestionConfig.EMBEDDING_MODEL_NAME,
        }
        
        # Check OCR-related variables based on USE_LLM_FOR_OCR
        if IngestionConfig.USE_LLM_FOR_OCR:
            required_vars['LLM_ENDPOINT'] = IngestionConfig.LLM_ENDPOINT
            required_vars['LLM_MODEL_NAME'] = IngestionConfig.LLM_MODEL_NAME
        else:
            required_vars['OCR_ENDPOINT'] = IngestionConfig.OCR_ENDPOINT
            required_vars['OCR_PORT'] = IngestionConfig.OCR_PORT
        
        for var_name, var_value in required_vars.items():
            if var_value:
                self.test_pass(f"{var_name} is set")
            else:
                self.test_fail(f"{var_name} is NOT set")
    
    def test_s3_connection(self):
        """Test S3 bucket access"""
        self.test_section("3. AWS S3 Connection")
        
        try:
            from src.ingestion.services import S3Service
            from src.ingestion.config import IngestionConfig
            
            s3_service = S3Service()
            self.test_pass(f"S3Service initialized")
            
            # Try to list files
            files = s3_service.list_files(max_keys=1)
            self.test_pass(f"Successfully connected to bucket: {IngestionConfig.S3_BUCKET_NAME}")
            
            # Count total files
            all_files = s3_service.list_files()
            file_count = len(all_files)
            if file_count > 0:
                self.test_pass(f"Found {file_count} files in bucket")
            else:
                self.test_warning("No files found in bucket")
            
        except Exception as e:
            # Include underlying error when available
            detail = str(e)
            original = getattr(e, 'original_error', None)
            if original:
                detail += f" | original: {repr(original)}"
            self.test_fail("S3 connection failed", detail)
    
    def test_elasticsearch_connection(self):
        """Test Elasticsearch connection"""
        self.test_section("4. Elasticsearch Connection")
        
        try:
            from src.ingestion.services import ElasticsearchService
            from src.ingestion.config import IngestionConfig
            
            es_service = ElasticsearchService()
            self.test_pass("ElasticsearchService initialized")
            
            # Check if index exists via service wrapper (robust to errors)
            index_name = IngestionConfig.ELASTICSEARCH_INDEX
            if es_service.index_exists():
                self.test_pass(f"Index '{index_name}' exists")
                
                # Index a small test document and search it
                test_id = f"setup-test-{int(datetime.now().timestamp())}"
                test_doc = {
                    "doc_id": test_id,
                    "file_name": "setup_test.txt",
                    "content": "hello world test document",
                    "upload_date": datetime.utcnow().isoformat()
                }
                if es_service.index_raw(test_doc, doc_id=test_id):
                    self.test_pass("Indexed test document")
                    es_service.refresh_index()
                    # Search for the word 'hello'
                    results = es_service.search({"query": {"match": {"content": "hello"}}}, size=1)
                    hits = results.get("hits", {}).get("total", {}).get("value", 0)
                    if hits > 0:
                        self.test_pass("Search returned results (Elasticsearch working)")
                    else:
                        self.test_fail("Search returned 0 results after indexing test document")
                else:
                    self.test_fail("Failed to index test document")
            else:
                self.test_warning(f"Index '{index_name}' does NOT exist. Please create it before ingestion.")
            
        except Exception as e:
            detail = str(e)
            original = getattr(e, 'original_error', None)
            if original:
                detail += f" | original: {repr(original)}"
            self.test_fail("Elasticsearch connection failed", detail)
    
    def test_ocr_endpoint(self):
        """Test OCR service endpoint (PaddleOCR or Vision LM)"""
        self.test_section("5. OCR Service Endpoint")
        
        try:
            import requests
            from src.ingestion.config import IngestionConfig
            
            use_llm = IngestionConfig.USE_LLM_FOR_OCR
            
            if use_llm:
                # Test Vision LM OCR
                endpoint = IngestionConfig.LLM_ENDPOINT
                self.test_pass(f"Using Vision LM OCR (LLM-based)")
                self.test_pass(f"LLM model configured: {IngestionConfig.LLM_MODEL_NAME}")
                
                try:
                    base_url = endpoint.rsplit('/', 1)[0]
                    response = requests.get(base_url, timeout=5)
                    self.test_pass(f"Vision LM endpoint is reachable: {endpoint}")
                except requests.exceptions.Timeout:
                    self.test_warning(f"Vision LM endpoint timeout (may still work): {endpoint}")
                except requests.exceptions.ConnectionError:
                    self.test_fail(f"Cannot connect to Vision LM endpoint: {endpoint}", 
                                  "Ensure the Vision LM service is running on port 8087")
            else:
                # Test PaddleOCR
                ocr_host = IngestionConfig.OCR_ENDPOINT
                ocr_port = IngestionConfig.OCR_PORT
                ocr_url = f"{ocr_host}:{ocr_port}"
                self.test_pass(f"Using PaddleOCR (Fast OCR)")
                
                try:
                    response = requests.get(ocr_url, timeout=5)
                    self.test_pass(f"PaddleOCR endpoint is reachable: {ocr_url}")
                except requests.exceptions.Timeout:
                    self.test_warning(f"PaddleOCR endpoint timeout: {ocr_url}")
                except requests.exceptions.ConnectionError:
                    self.test_fail(f"Cannot connect to PaddleOCR endpoint: {ocr_url}", 
                                  "Ensure PaddleOCR service is running on port 8088")
            
        except Exception as e:
            self.test_fail("OCR endpoint test failed", str(e))
    
    def test_embedding_endpoint(self):
        """Test embedding service endpoint"""
        self.test_section("6. Embedding Service Endpoint")
        
        try:
            import requests
            from src.ingestion.config import IngestionConfig
            
            endpoint = IngestionConfig.EMBEDDING_ENDPOINT
            
            # Try a test embedding
            try:
                response = requests.post(
                    endpoint,
                    json={
                        "model": IngestionConfig.EMBEDDING_MODEL_NAME,
                        "text": "test",
                        "normalize": True
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    vector = result.get("vector", [])
                    if vector:
                        self.test_pass(f"Embedding service is working: {endpoint}")
                        self.test_pass(f"Embedding dimension: {len(vector)}")
                    else:
                        self.test_warning("Embedding service responded but returned empty vector")
                else:
                    self.test_fail(f"Embedding service returned status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.test_warning(f"Embedding endpoint timeout: {endpoint}")
            except requests.exceptions.ConnectionError:
                self.test_fail(f"Cannot connect to embedding endpoint: {endpoint}",
                              "Ensure the embedding service is running")
            
            self.test_pass(f"Embedding model configured: {IngestionConfig.EMBEDDING_MODEL_NAME}")
            
        except Exception as e:
            self.test_fail("Embedding endpoint test failed", str(e))
    
    def test_file_parsers(self):
        """Test if file parsers can be initialized"""
        self.test_section("7. File Parsers")
        
        try:
            from src.ingestion.parsers import (
                PDFParser, DOCXParser, ImageParser,
                CSVParser, ExcelParser
            )
            from src.ingestion.models.schemas import ParserConfig
            from src.ingestion.services import LLMService
            
            config = ParserConfig()
            llm_service = LLMService()
            
            parsers = [
                ('PDFParser', PDFParser),
                ('DOCXParser', DOCXParser),
                ('ImageParser', ImageParser),
                ('CSVParser', CSVParser),
                ('ExcelParser', ExcelParser)
            ]
            
            for name, parser_class in parsers:
                try:
                    if name in ['PDFParser', 'ImageParser']:
                        parser = parser_class(config, llm_service)
                    else:
                        parser = parser_class(config)
                    self.test_pass(f"{name} initialized successfully")
                except Exception as e:
                    self.test_fail(f"{name} initialization failed", str(e))
                    
        except Exception as e:
            self.test_fail("Parser initialization failed", str(e))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.passed) + len(self.failed)
        
        print(f"\n Passed: {len(self.passed)}/{total_tests}")
        print(f" Failed: {len(self.failed)}/{total_tests}")
        print(f"  Warnings: {len(self.warnings)}")
        
        if self.failed:
            print("\n" + "─" * 70)
            print(" FAILED TESTS:")
            print("─" * 70)
            for i, failure in enumerate(self.failed, 1):
                print(f"{i}. {failure}")
        
        if self.warnings:
            print("\n" + "─" * 70)
            print("  WARNINGS:")
            print("─" * 70)
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")
        
        print("\n" + "=" * 70)
        
        if self.failed:
            print(" VALIDATION FAILED - Please fix the issues above before running ingestion")
            print("=" * 70 + "\n")
            return False
        else:
            print(" VALIDATION PASSED - All systems ready for ingestion!")
            print("=" * 70 + "\n")
            print("🚀 To start ingestion, run:")
            print("   python src/ingestion/run_ingestion.py")
            print()
            return True


def main():
    """Main entry point"""
    validator = SetupValidator()
    
    validator.print_header()
    
    # Run all tests
    validator.test_python_packages()
    validator.test_environment_variables()
    validator.test_s3_connection()
    validator.test_elasticsearch_connection()
    validator.test_ocr_endpoint()
    validator.test_embedding_endpoint()
    validator.test_file_parsers()
    
    # Print summary
    success = validator.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
