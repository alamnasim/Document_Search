"""
Metadata extractor using boto3
"""
import logging
from typing import Dict, Any
from datetime import datetime

from ..models.schemas import S3FileInfo


logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extractor for document metadata"""
    
    def __init__(self):
        """Initialize metadata extractor"""
        logger.info("MetadataExtractor initialized")
    
    def extract_from_s3_info(self, file_info: S3FileInfo) -> Dict[str, Any]:
        """
        Extract metadata from S3 file info
        
        Args:
            file_info: S3 file information
            
        Returns:
            dict: Extracted metadata
        """
        metadata = {
            "s3_bucket": file_info.bucket_name,
            "s3_key": file_info.s3_key,
            "file_size": file_info.file_size,
            "content_type": file_info.content_type,
            "last_modified": file_info.last_modified.isoformat(),
            "ingestion_timestamp": datetime.utcnow().isoformat()
        }
        
        return metadata
    
    def enrich_metadata(
        self,
        base_metadata: Dict[str, Any],
        additional_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich base metadata with additional information
        
        Args:
            base_metadata: Base metadata dictionary
            additional_metadata: Additional metadata to merge
            
        Returns:
            dict: Enriched metadata
        """
        enriched = {**base_metadata}
        enriched.update(additional_metadata)
        
        return enriched
