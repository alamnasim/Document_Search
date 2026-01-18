"""
S3 service for file operations
"""
import os
import logging
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..models.schemas import S3FileInfo
from ..exceptions import S3Exception
from ..config import IngestionConfig


logger = logging.getLogger(__name__)


class S3Service:
    """Service for AWS S3 operations"""
    
    def __init__(
        self,
        bucket_name: str = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = None
    ):
        """
        Initialize S3 service
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            aws_region: AWS region
            
        Raises:
            S3Exception: If initialization fails
        """
        try:
            # Fallback to .env config when args are not provided
            resolved_bucket = bucket_name or IngestionConfig.S3_BUCKET_NAME
            resolved_access_key = aws_access_key_id or IngestionConfig.AWS_ACCESS_KEY_ID
            resolved_secret_key = aws_secret_access_key or IngestionConfig.AWS_SECRET_ACCESS_KEY
            resolved_region = aws_region or IngestionConfig.AWS_REGION

            if not resolved_bucket:
                raise S3Exception("S3 bucket name is not configured")

            # Store bucket
            self.bucket_name = resolved_bucket

            # Initialize client (boto3 will still use env/instance profile if keys are None)
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=resolved_access_key,
                aws_secret_access_key=resolved_secret_key,
                region_name=resolved_region
            )
            
            # Test connection to bucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f" S3Service initialized: bucket={self.bucket_name}, region={resolved_region}")
            
        except NoCredentialsError as e:
            raise S3Exception("AWS credentials not found", original_error=e)
        except ClientError as e:
            raise S3Exception(
                f"Failed to connect to S3 bucket {bucket_name}",
                original_error=e
            )
        except Exception as e:
            raise S3Exception(
                "Unexpected error initializing S3 service",
                original_error=e
            )
    
    def list_files(self, prefix: str = "", max_keys: Optional[int] = None) -> List[str]:
        """
        List all files in the S3 bucket
        
        Args:
            prefix: Filter files by prefix
            max_keys: Maximum number of keys to return (optional)
            
        Returns:
            list: List of S3 keys
            
        Raises:
            S3Exception: If listing fails
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Prefix': prefix
            }
            if max_keys is not None:
                params['MaxKeys'] = max_keys

            response = self.s3_client.list_objects_v2(**params)
            
            if 'Contents' not in response:
                logger.info(f"No files found with prefix: {prefix}")
                return []
            
            # Filter out folder markers (keys ending with '/')
            files = [obj['Key'] for obj in response['Contents'] if not obj['Key'].endswith('/')]
            logger.info(f"Found {len(files)} files in S3")
            
            return files
            
        except ClientError as e:
            raise S3Exception(
                f"Failed to list files in bucket {self.bucket_name}",
                original_error=e
            )
    
    def get_file_content(self, s3_key: str) -> bytes:
        """
        Read file content from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            bytes: File content
            
        Raises:
            S3Exception: If reading fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            content = response['Body'].read()
            logger.debug(f"Read {len(content)} bytes from {s3_key}")
            
            return content
            
        except ClientError as e:
            raise S3Exception(
                f"Failed to read file {s3_key}",
                original_error=e
            )
    
    def get_file_info(self, s3_key: str) -> S3FileInfo:
        """
        Get file information and metadata
        
        Args:
            s3_key: S3 object key
            
        Returns:
            S3FileInfo: File information
            
        Raises:
            S3Exception: If getting metadata fails
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return S3FileInfo(
                s3_key=s3_key,
                file_name=os.path.basename(s3_key),
                file_size=response['ContentLength'],
                content_type=response.get('ContentType', 'Unknown'),
                last_modified=response['LastModified'],
                bucket_name=self.bucket_name
            )
            
        except ClientError as e:
            raise S3Exception(
                f"Failed to get metadata for {s3_key}",
                original_error=e
            )
    
    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for file access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            str: Presigned URL
            
        Raises:
            S3Exception: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            raise S3Exception(
                f"Failed to generate presigned URL for {s3_key}",
                original_error=e
            )
    
    def get_files_with_info(
        self,
        prefix: str = "",
        include_presigned_urls: bool = True,
        url_expiration: int = 3600
    ) -> List[S3FileInfo]:
        """
        Get detailed information for all files
        
        Args:
            prefix: Filter files by prefix
            include_presigned_urls: Whether to generate presigned URLs
            url_expiration: URL expiration time
            
        Returns:
            list: List of S3FileInfo objects
            
        Raises:
            S3Exception: If operation fails
        """
        try:
            files = self.list_files(prefix)
            file_infos = []
            
            for s3_key in files:
                file_info = self.get_file_info(s3_key)
                
                if include_presigned_urls:
                    file_info.presigned_url = self.generate_presigned_url(
                        s3_key,
                        url_expiration
                    )
                
                file_infos.append(file_info)
            
            logger.info(f"Retrieved info for {len(file_infos)} files")
            return file_infos
            
        except S3Exception:
            raise
        except Exception as e:
            raise S3Exception(
                "Failed to get files with info",
                original_error=e
            )
