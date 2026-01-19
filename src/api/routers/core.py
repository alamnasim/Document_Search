from fastapi import APIRouter, HTTPException
import requests
from typing import List, Dict, Any

from src.api.schema.data import SearchRequest, SearchResponse
from src.api.config import Config

router = APIRouter(prefix="/api/v1", tags=["Document Search"])

# Initialize search engine lazily
_search_engine = None


def get_search_engine():
    """Initialize DocumentSearchEngine lazily"""
    global _search_engine
    if _search_engine is None:
        _search_engine = DocumentSearchEngine()
    return _search_engine


class DocumentSearchEngine:
    """Service for searching documents in Elasticsearch"""
    
    def __init__(self):
        """Initialize Elasticsearch connection"""
        self.base_url = f"http://{Config.ELASTICSEARCH_HOST}:{Config.ELASTICSEARCH_PORT}"
        self.index_name = Config.ELASTICSEARCH_INDEX
        
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ DocumentSearchEngine: Connected to Elasticsearch at {self.base_url}")
            else:
                raise ConnectionError(f"Failed to connect: status {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to Elasticsearch: {str(e)}")
    
    def search(
        self,
        query: str,
        size: int = 10,
        fields: List[str] = None,
        fuzziness: str = "AUTO",
        min_score: float = 0.0,
        use_snippets: bool = True
    ) -> Dict[str, Any]:
        """Search documents in the index"""
        if not query or not query.strip():
            return {"total": 0, "results": []}
        
        if fields is None:
            fields = ["content", "file_name"]
        
        # Build multi-match query
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    "fuzziness": fuzziness,
                    "operator": "or"
                }
            },
            "size": min(max(1, size), 100),
            "min_score": min_score,
            "_source": ["file_name", "file_path", "file_type", "content", "chunk_index", "total_chunks"]
        }
        
        # Add highlighting for snippets
        if use_snippets:
            search_body["highlight"] = {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 3
                    }
                },
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        
        try:
            response = requests.post(
                f"{self.base_url}/{self.index_name}/_search",
                json=search_body,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            
            results = []
            for hit in hits:
                source = hit["_source"]
                result = {
                    "file_name": source.get("file_name", "Unknown"),
                    "file_path": source.get("file_path", ""),
                    "file_type": source.get("file_type", "unknown"),
                    "score": hit["_score"],
                    "chunk_index": source.get("chunk_index", 0),
                    "total_chunks": source.get("total_chunks", 1)
                }
                
                # Use snippets if available, otherwise full content
                if use_snippets and "highlight" in hit:
                    result["content"] = " ... ".join(hit["highlight"].get("content", []))
                else:
                    result["content"] = source.get("content", "")
                
                results.append(result)
            
            return {
                "total": data.get("hits", {}).get("total", {}).get("value", 0),
                "results": results
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Elasticsearch query failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Document Search API"}


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search documents in Elasticsearch
    
    - **query**: Search query string
    - **size**: Number of results to return (1-100, default: 10)
    - **fields**: Fields to search in (default: content, file_name)
    - **fuzziness**: Typo tolerance - 0 (exact), 1, 2, or AUTO (default)
    - **min_score**: Minimum relevance score (0.0 = all results)
    - **use_snippets**: Return content snippets instead of full content (faster, default: true)
    """
    try:
        search_engine = get_search_engine()
        
        results = search_engine.search(
            query=request.query,
            size=request.size,
            fields=request.fields,
            fuzziness=request.fuzziness,
            min_score=request.min_score,
            use_snippets=request.use_snippets
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
