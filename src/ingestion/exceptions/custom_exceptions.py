"""
Custom exception classes for the ingestion pipeline
"""


class IngestionException(Exception):
    """Base exception for ingestion pipeline"""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class ParserException(IngestionException):
    """Exception raised during document parsing"""
    pass


class S3Exception(IngestionException):
    """Exception raised during S3 operations"""
    pass


class ElasticsearchException(IngestionException):
    """Exception raised during Elasticsearch operations"""
    pass


class LLMServiceException(IngestionException):
    """Exception raised during LLM service calls"""
    pass


class EmbeddingServiceException(IngestionException):
    """Exception raised during embedding generation"""
    pass


class ChunkingException(IngestionException):
    """Exception raised during text chunking"""
    pass


class ValidationException(IngestionException):
    """Exception raised during data validation"""
    pass
