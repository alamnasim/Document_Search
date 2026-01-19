"""
Background sync service for cleanup of orphaned Elasticsearch documents
Runs periodically to ensure Elasticsearch is in sync with S3
"""
import logging
import time
from typing import Dict, Any
import requests

logger = logging.getLogger(__name__)


class SyncService:
    """Background sync service for cleaning orphaned documents"""
    
    def __init__(
        self,
        s3_service,
        elasticsearch_service,
        check_interval: int = 3600  # Default: 1 hour
    ):
        """
        Initialize sync service
        
        Args:
            s3_service: S3 service instance
            elasticsearch_service: Elasticsearch service instance
            check_interval: Interval between checks in seconds
        """
        self.s3_service = s3_service
        self.es_service = elasticsearch_service
        self.check_interval = check_interval
        self.running = False
        
        logger.info(f"SyncService initialized: check_interval={check_interval}s ({check_interval/3600:.1f}h)")
    
    def start_background_sync(self):
        """Start background sync in a loop"""
        self.running = True
        logger.info("🔄 Starting background sync service...")
        
        while self.running:
            try:
                self.run_sync()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("Background sync interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in background sync: {e}", exc_info=True)
                time.sleep(self.check_interval)
    
    def stop_background_sync(self):
        """Stop background sync"""
        self.running = False
        logger.info("Stopping background sync...")
    
    def run_sync(self) -> Dict[str, Any]:
        """
        Run a single sync operation
        
        Returns:
            dict: Sync statistics
        """
        logger.info("=" * 60)
        logger.info("🔍 Running background sync check...")
        start_time = time.time()
        
        try:
            # Get all S3 keys
            logger.info("📦 Fetching S3 file list...")
            s3_keys = self._get_all_s3_keys()
            s3_keys_set = set(s3_keys)
            logger.info(f"   Found {len(s3_keys)} files in S3")
            
            # Get all Elasticsearch document S3 keys
            logger.info("📊 Fetching Elasticsearch document list...")
            es_keys = self._get_all_es_s3_keys()
            es_keys_set = set(es_keys)
            logger.info(f"   Found {len(es_keys)} documents in Elasticsearch")
            
            # Find orphaned documents (in ES but not in S3)
            orphaned = es_keys_set - s3_keys_set
            
            if not orphaned:
                elapsed = time.time() - start_time
                logger.info(f" No orphaned documents found. Sync complete in {elapsed:.2f}s")
                logger.info("=" * 60)
                return {
                    'total_s3_files': len(s3_keys),
                    'total_es_docs': len(es_keys),
                    'orphaned_found': 0,
                    'orphaned_deleted': 0,
                    'elapsed_time': elapsed
                }
            
            # Delete orphaned documents
            logger.info(f"  Found {len(orphaned)} orphaned documents. Cleaning up...")
            deleted_count = 0
            
            for s3_key in orphaned:
                try:
                    if self.es_service.delete_document_by_s3_key(s3_key):
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete orphaned document {s3_key}: {e}")
            
            elapsed = time.time() - start_time
            logger.info(f" Sync complete: deleted {deleted_count}/{len(orphaned)} orphaned documents in {elapsed:.2f}s")
            logger.info("=" * 60)
            
            return {
                'total_s3_files': len(s3_keys),
                'total_es_docs': len(es_keys),
                'orphaned_found': len(orphaned),
                'orphaned_deleted': deleted_count,
                'elapsed_time': elapsed
            }
            
        except Exception as e:
            logger.error(f" Sync failed: {e}", exc_info=True)
            return {
                'error': str(e),
                'elapsed_time': time.time() - start_time
            }
    
    def _get_all_s3_keys(self):
        """Get all S3 keys from the bucket"""
        try:
            # Use boto3 to list all objects
            s3_client = self.s3_service.s3_client
            bucket_name = self.s3_service.bucket_name
            
            keys = []
            paginator = s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        keys.append(obj['Key'])
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list S3 objects: {e}")
            return []
    
    def _get_all_es_s3_keys(self):
        """Get all S3 keys from Elasticsearch documents"""
        try:
            # Use scroll API to get all documents
            es_keys = []
            
            # Initial search
            query = {
                "query": {"match_all": {}},
                "_source": ["file_path"],
                "size": 1000
            }
            
            url = f"{self.es_service.base_url}/{self.es_service.index_name}/_search"
            params = {"scroll": "2m"}
            
            resp = requests.post(
                url,
                json=query,
                params=params,
                timeout=30,
                auth=self.es_service._auth()
            )
            
            if resp.status_code != 200:
                logger.error(f"Failed to search Elasticsearch: {resp.status_code}, response: {resp.text}")
                return []
            
            data = resp.json()
            scroll_id = data.get('_scroll_id')
            hits = data.get('hits', {}).get('hits', [])
            
            # Collect S3 keys from first batch
            for hit in hits:
                file_path = hit.get('_source', {}).get('file_path')
                if file_path:
                    # Extract S3 key from file_path (format: s3://bucket/key)
                    if file_path.startswith('s3://'):
                        # Remove 's3://bucket/' to get just the key
                        parts = file_path.replace('s3://', '').split('/', 1)
                        if len(parts) == 2:
                            s3_key = parts[1]  # Get the key part after bucket name
                            es_keys.append(s3_key)
            
            # Continue scrolling if there are more results
            while hits:
                scroll_resp = requests.post(
                    f"{self.es_service.base_url}/_search/scroll",
                    json={"scroll": "2m", "scroll_id": scroll_id},
                    timeout=30,
                    auth=self.es_service._auth()
                )
                
                if scroll_resp.status_code != 200:
                    break
                
                scroll_data = scroll_resp.json()
                hits = scroll_data.get('hits', {}).get('hits', [])
                
                for hit in hits:
                    file_path = hit.get('_source', {}).get('file_path')
                    if file_path:
                        # Extract S3 key from file_path
                        if file_path.startswith('s3://'):
                            parts = file_path.replace('s3://', '').split('/', 1)
                            if len(parts) == 2:
                                s3_key = parts[1]
                                es_keys.append(s3_key)
            
            # Clear scroll
            if scroll_id:
                try:
                    requests.delete(
                        f"{self.es_service.base_url}/_search/scroll",
                        json={"scroll_id": scroll_id},
                        timeout=5,
                        auth=self.es_service._auth()
                    )
                except:
                    pass
            
            return es_keys
            
        except Exception as e:
            logger.error(f"Failed to get Elasticsearch documents: {e}")
            return []
