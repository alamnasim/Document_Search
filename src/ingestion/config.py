"""
Configuration for ingestion pipeline
Loads all settings from .env file
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent.parent
load_dotenv(root_dir / '.env')


class IngestionConfig:
    """Configuration class for ingestion pipeline"""
    
    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # S3 Configuration
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    S3_BUCKET_ARN = os.getenv('S3_BUCKET_ARN')
    
    # Elasticsearch Configuration
    ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
    ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', 9200))
    ELASTICSEARCH_USERNAME = os.getenv('ELASTICSEARCH_USERNAME')
    ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD')
    ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'documents_v1')
    
    # LLM Configuration
    LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'qwen2.5-vl-3b-instruct')
    LLM_ENDPOINT = os.getenv('LLM_ENDPOINT', 'http://localhost:8080/v1/chat/completions')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    
    # OCR Configuration (PaddleOCR)
    USE_LLM_FOR_OCR = os.getenv('USE_LLM_FOR_OCR', 'true').strip().lower() == 'true'
    OCR_ENDPOINT = os.getenv('OCR_ENDPOINT', 'http://localhost')
    OCR_PORT = int(os.getenv('OCR_PORT', 8088))
    
    # Embedding Configuration
    EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'bge-small-en-v1.5')
    EMBEDDING_ENDPOINT = os.getenv('EMBEDDING_ENDPOINT', 'http://localhost:8001/embed')
    
    # SQS Queue Configuration (optional)
    SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
    # Toggle SQS usage and first-run behavior
    SQS_ENABLED = os.getenv('SQS_ENABLED', 'false').strip().lower() == 'true'
    FIRST_RUN_FULL_INGEST = os.getenv('FIRST_RUN_FULL_INGEST', 'true').strip().lower() == 'true'
    
    # Background Sync Configuration
    ENABLE_BACKGROUND_SYNC = os.getenv('ENABLE_BACKGROUND_SYNC', 'true').strip().lower() == 'true'
    SYNC_INTERVAL_HOURS = int(os.getenv('SYNC_INTERVAL_HOURS', '6'))  # Default: 6 hours
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        required_vars = [
            ('AWS_ACCESS_KEY_ID', cls.AWS_ACCESS_KEY_ID),
            ('AWS_SECRET_ACCESS_KEY', cls.AWS_SECRET_ACCESS_KEY),
            ('S3_BUCKET_NAME', cls.S3_BUCKET_NAME),
        ]
        
        missing = [var for var, val in required_vars if not val]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_s3_config(cls):
        """Get S3 configuration as dict"""
        return {
            'bucket_name': cls.S3_BUCKET_NAME,
            'aws_access_key_id': cls.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': cls.AWS_SECRET_ACCESS_KEY,
            'aws_region': cls.AWS_REGION
        }
    
    @classmethod
    def get_elasticsearch_config(cls):
        """Get Elasticsearch configuration as dict"""
        return {
            'host': cls.ELASTICSEARCH_HOST,
            'port': cls.ELASTICSEARCH_PORT,
            'index_name': cls.ELASTICSEARCH_INDEX,
            'username': cls.ELASTICSEARCH_USERNAME,
            'password': cls.ELASTICSEARCH_PASSWORD
        }
    
    @classmethod
    def print_config(cls):
        """Print current configuration (masked sensitive data)"""
        print("\n=== Ingestion Pipeline Configuration ===")
        print(f"AWS Region: {cls.AWS_REGION}")
        print(f"S3 Bucket: {cls.S3_BUCKET_NAME}")
        print(f"Elasticsearch: {cls.ELASTICSEARCH_HOST}:{cls.ELASTICSEARCH_PORT}")
        print(f"Elasticsearch Index: {cls.ELASTICSEARCH_INDEX}")
        print(f"LLM Model: {cls.LLM_MODEL_NAME}")
        print(f"LLM Endpoint: {cls.LLM_ENDPOINT}")
        print(f"Use LLM for OCR: {cls.USE_LLM_FOR_OCR}")
        print(f"OCR Endpoint: {cls.OCR_ENDPOINT}:{cls.OCR_PORT}")
        print(f"Embedding Model: {cls.EMBEDDING_MODEL_NAME}")
        print(f"Embedding Endpoint: {cls.EMBEDDING_ENDPOINT}")
        print(f"First-Run Full Ingest: {cls.FIRST_RUN_FULL_INGEST}")
        print(f"SQS Enabled: {cls.SQS_ENABLED}")
        if cls.SQS_QUEUE_URL:
            print(f"SQS Queue: {cls.SQS_QUEUE_URL}")
        print(f"Background Sync: {cls.ENABLE_BACKGROUND_SYNC}")
        if cls.ENABLE_BACKGROUND_SYNC:
            print(f"Sync Interval: {cls.SYNC_INTERVAL_HOURS} hours")
        print("=" * 40 + "\n")
