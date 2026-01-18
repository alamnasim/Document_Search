import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent.parent
load_dotenv(root_dir / '.env')

class Config:
    """Configuration class to manage AWS credentials and S3 settings"""
    
    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'eu-north-1')
    
    # S3 Bucket Configuration
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    S3_BUCKET_ARN = os.getenv('S3_BUCKET_ARN')
    
    # Elasticsearch Configuration
    ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
    ELASTICSEARCH_PORT = int(os.getenv('ELASTICSEARCH_PORT', 9200))
    ELASTICSEARCH_USERNAME = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
    ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD')
    ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'documents_v1')

    # LLM Endpoint/Model
    LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'qwen2.5-vl-3b-instruct')
    LLM_ENDPOINT = os.getenv('LLM_ENDPOINT', 'http://localhost:8080/v1/chat/completions')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')

    # Embedding Model Endpoint/Model
    EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'bge-small-en-v1.5')
    EMBEDDING_ENDPOINT = os.getenv('EMBEDDING_ENDPOINT', 'http://localhost:8001/embed')
    
    @classmethod
    def validate(cls):
        """Validate that all required credentials are set"""
        required_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'S3_BUCKET_NAME'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(
                f"Missing required configuration variables: {', '.join(missing_vars)}\n"
                "Please check your .env file."
            )
        
        return True
