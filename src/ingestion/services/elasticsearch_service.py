"""
Elasticsearch service (minimal): index and search via HTTP.
"""
import logging
from typing import List, Dict, Any
import requests

from ..models.schemas import ProcessedDocument
from ..exceptions import ElasticsearchException
from ..config import IngestionConfig


logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Minimal Elasticsearch operations using HTTP requests"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        index_name: str = None,
        username: str = None,
        password: str = None
    ):
        try:
            resolved_host = host or IngestionConfig.ELASTICSEARCH_HOST
            resolved_port = port or IngestionConfig.ELASTICSEARCH_PORT
            self.index_name = index_name or IngestionConfig.ELASTICSEARCH_INDEX
            self.username = username or IngestionConfig.ELASTICSEARCH_USERNAME
            self.password = password or IngestionConfig.ELASTICSEARCH_PASSWORD

            if resolved_host.startswith("http://") or resolved_host.startswith("https://"):
                self.base_url = resolved_host
            else:
                self.base_url = f"http://{resolved_host}:{resolved_port}"

            # Simple reachability check
            resp = requests.get(self.base_url, timeout=3, auth=self._auth())
            if resp.status_code >= 500:
                raise ElasticsearchException("Cannot connect to Elasticsearch")
            logger.info(f" ElasticsearchService initialized: {self.base_url}, index={self.index_name}")
        except Exception as e:
            raise ElasticsearchException("Failed to connect to Elasticsearch", original_error=e)
    
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """Minimal behavior: do not create; just report existence."""
        return self.index_exists()
    
    def index_document(self, document: ProcessedDocument) -> bool:
        """
        Index a single document
        
        Args:
            document: Processed document to index
            
        Returns:
            bool: True if successful
            
        Raises:
            ElasticsearchException: If indexing fails
        """
        try:
            # Use model_dump with mode='json' to properly serialize datetime objects
            doc_dict = document.model_dump(mode='json')
            
            ok = self.index_raw(doc_dict, doc_id=document.doc_id)
            if ok:
                logger.debug(f"Indexed document: {document.file_name}")
            return ok
            
        except Exception as e:
            raise ElasticsearchException(
                f"Failed to index document {document.file_name}",
                original_error=e
            )
    
    def bulk_index_documents(
        self,
        documents: List[ProcessedDocument]
    ) -> Dict[str, int]:
        """
        Bulk index multiple documents
        
        Args:
            documents: List of processed documents
            
        Returns:
            dict: Success and failed counts
            
        Raises:
            ElasticsearchException: If bulk indexing fails
        """
        try:
            if not documents:
                return {"success": 0, "failed": 0}
            
            success = 0
            failed = 0
            for doc in documents:
                # Use model_dump with mode='json' to properly serialize datetime objects
                if self.index_raw(doc.model_dump(mode='json'), doc_id=doc.doc_id):
                    success += 1
                else:
                    failed += 1
            logger.info(f"Bulk indexed: {success} succeeded, {failed} failed")
            return {"success": success, "failed": failed}
            
        except Exception as e:
            raise ElasticsearchException(
                "Failed during bulk indexing",
                original_error=e
            )

    def index_exists(self) -> bool:
        """
        Check if the configured index exists.

        Returns:
            bool: True if index exists, False otherwise
        """
        try:
            # Use CAT indices API for simple existence check
            r = requests.get(
                f"{self.base_url}/_cat/indices/{self.index_name}?h=index&format=json",
                timeout=5,
                auth=self._auth()
            )
            if r.status_code == 200:
                data = r.json()
                return any(row.get('index') == self.index_name for row in data)
            if r.status_code == 404:
                return False
            # Fallback to HEAD
            hr = requests.head(f"{self.base_url}/{self.index_name}", timeout=5, auth=self._auth())
            return hr.status_code == 200
        except Exception:
            return False
    
    def refresh_index(self) -> bool:
        """
        Refresh the index to make recent changes searchable.

        Returns:
            bool: True if refresh succeeded.
        """
        try:
            resp = requests.post(f"{self.base_url}/{self.index_name}/_refresh", timeout=5, auth=self._auth())
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"Index refresh failed: {repr(e)}")
            return False

    def index_raw(self, document: Dict[str, Any], doc_id: str | None = None) -> bool:
        """
        Index a raw document dict into the configured index.

        Args:
            document: The document body.
            doc_id: Optional id. If None, ES auto-generates an id.

        Returns:
            bool: True if created/updated.
        """
        try:
            url = f"{self.base_url}/{self.index_name}/_doc"
            method = requests.post
            if doc_id:
                url = f"{url}/{doc_id}"
                method = requests.put
            resp = method(url, json=document, timeout=5, auth=self._auth())
            if resp.status_code in (200, 201):
                return True
            logger.warning(f"Index raw failed: status={resp.status_code} body={resp.text}")
            return False
        except Exception as e:
            raise ElasticsearchException(
                "Failed to index raw document",
                original_error=e
            )

    def search(self, query: Dict[str, Any], size: int = 10) -> Dict[str, Any]:
        """
        Execute a search query against the configured index.

        Args:
            query: Elasticsearch query DSL payload.
            size: Number of results to return.

        Returns:
            dict: Parsed search results.
        """
        try:
            url = f"{self.base_url}/{self.index_name}/_search"
            payload = {"size": size, **query}
            resp = requests.post(url, json=payload, timeout=8, auth=self._auth())
            if resp.status_code == 200:
                return resp.json()
            raise ElasticsearchException(
                f"Search failed: status={resp.status_code} body={resp.text}"
            )
        except Exception as e:
            raise ElasticsearchException(
                "Failed to execute search",
                original_error=e
            )
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics
        
        Returns:
            dict: Index statistics
            
        Raises:
            ElasticsearchException: If getting stats fails
        """
        try:
            count_resp = requests.get(
                f"{self.base_url}/{self.index_name}/_count", timeout=5, auth=self._auth()
            )
            size_resp = requests.get(
                f"{self.base_url}/{self.index_name}/_stats", timeout=5, auth=self._auth()
            )
            count = count_resp.json().get('count', 0) if count_resp.status_code == 200 else 0
            size = 0
            if size_resp.status_code == 200:
                stats = size_resp.json()
                try:
                    size = stats['indices'][self.index_name]['total']['store']['size_in_bytes']
                except Exception:
                    size = 0
            return {
                "document_count": count,
                "size_in_bytes": size,
                "index_name": self.index_name
            }
        except Exception as e:
            raise ElasticsearchException("Failed to get index stats", original_error=e)
    
    def check_duplicate(self, content_hash: str) -> bool:
        """
        Check if a document with the same content hash already exists
        
        Args:
            content_hash: SHA256 hash of document content
            
        Returns:
            bool: True if duplicate exists, False otherwise
        """
        try:
            query = {
                "query": {
                    "term": {
                        "content_hash": content_hash
                    }
                },
                "size": 1
            }
            
            url = f"{self.base_url}/{self.index_name}/_search"
            resp = requests.post(url, json=query, timeout=5, auth=self._auth())
            
            if resp.status_code == 200:
                data = resp.json()
                hits = data.get('hits', {}).get('hits', [])
                return len(hits) > 0
            elif resp.status_code == 404:
                # Index doesn't exist yet, so no duplicates
                return False
            else:
                logger.warning(f"Duplicate check failed with status {resp.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            return False  # Fail open - allow indexing if check fails
    
    def delete_document_by_s3_key(self, s3_key: str) -> bool:
        """
        Delete document(s) by S3 key from Elasticsearch
        
        Args:
            s3_key: S3 key of the file (e.g., 'xls_data/file.xlsx')
            
        Returns:
            bool: True if successful
        """
        try:
            # Construct the full S3 path to match file_path field
            # Documents store file_path as: s3://bucket/key
            # We need to match by the key part, so use wildcard query
            query = {
                "query": {
                    "wildcard": {
                        "file_path.keyword": f"s3://*/{s3_key}"
                    }
                }
            }
            
            url = f"{self.base_url}/{self.index_name}/_delete_by_query"
            resp = requests.post(url, json=query, timeout=10, auth=self._auth())
            
            if resp.status_code == 200:
                data = resp.json()
                deleted = data.get('deleted', 0)
                if deleted > 0:
                    logger.info(f" Deleted {deleted} document(s) for S3 key: {s3_key}")
                else:
                    logger.warning(f"  No documents found for S3 key: {s3_key}")
                return True
            elif resp.status_code == 404:
                logger.warning(f"  Index not found when trying to delete: {s3_key}")
                return True  # Not a failure if index doesn't exist
            else:
                logger.error(f" Delete failed: status={resp.status_code}, body={resp.text}")
                return False
                
        except Exception as e:
            logger.error(f" Error deleting document for {s3_key}: {e}")
            return False

    def _auth(self):
        if self.username and self.password:
            from requests.auth import HTTPBasicAuth
            return HTTPBasicAuth(self.username, self.password)
        return None
