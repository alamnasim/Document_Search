from pydantic import BaseModel, Field
from typing import List, Optional


class SearchRequest(BaseModel):
    """Schema for search request"""
    query: str = Field(..., description="Search query string")
    size: int = Field(10, description="Number of results to return (1-100)", ge=1, le=100)
    fields: Optional[List[str]] = Field(
        default=["content", "file_name"],
        description="Fields to search in (content, file_name, file_type, file_path)"
    )
    fuzziness: Optional[str] = Field(
        default="AUTO",
        description="Typo tolerance: 0 (exact), 1, 2, or AUTO (recommended)"
    )
    min_score: Optional[float] = Field(
        default=0.0,
        description="Minimum relevance score threshold (0.0 = all results)",
        ge=0.0
    )
    use_snippets: Optional[bool] = Field(
        default=True,
        description="Return content snippets instead of full content (faster)"
    )


class SearchResult(BaseModel):
    """Schema for individual search result"""
    file_name: str
    file_path: str
    file_type: str
    score: float
    content: str
    chunk_index: int
    total_chunks: int


class SearchResponse(BaseModel):
    """Schema for search response"""
    total: int
    results: List[SearchResult]
