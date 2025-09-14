"""
Search result model for wrapping search results with metadata.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from .product import Product


@dataclass
class SearchPagination:
    """Pagination information for search results."""
    total: int
    limit: int
    offset: int
    has_more: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total': self.total,
            'limit': self.limit,
            'offset': self.offset,
            'hasMore': self.has_more
        }


@dataclass
class SearchInfo:
    """Search execution information."""
    query: str
    execution_time: float
    language: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    search_type: str = "text"  # text, filter
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query': self.query,
            'executionTime': self.execution_time,
            'language': self.language,
            'filters': self.filters,
            'searchType': self.search_type
        }


@dataclass
class SearchResult:
    """
    Search result wrapper containing products and metadata.
    
    Used to return search results with pagination, timing, and other metadata.
    """
    
    # Search results
    results: List[Product]
    
    # Pagination information
    pagination: SearchPagination
    
    # Search execution info
    search_info: SearchInfo
    
    # Suggested filters/facets (optional)
    available_filters: Optional[Dict[str, List[Any]]] = None
    
    def get_results_count(self) -> int:
        """Get count of results in current page."""
        return len(self.results)
    
    def get_total_count(self) -> int:
        """Get total count of all matching results."""
        return self.pagination.total
    
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return len(self.results) > 0
    
    def get_results_as_dicts(self) -> List[Dict[str, Any]]:
        """Convert all results to dictionary format."""
        return [product.to_dict() for product in self.results]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary format for API responses."""
        return {
            'results': self.get_results_as_dicts(),
            'pagination': self.pagination.to_dict(),
            'searchInfo': self.search_info.to_dict(),
            'availableFilters': self.available_filters
        }
    
    @classmethod
    def create_empty(cls, query: str, execution_time: float = 0.0, 
                    language: Optional[str] = None, 
                    filters: Optional[Dict[str, Any]] = None) -> 'SearchResult':
        """
        Create empty search result.
        
        Args:
            query: Search query that returned no results
            execution_time: Time taken to execute search
            language: Language preference used
            filters: Filters applied
            
        Returns:
            Empty SearchResult instance
        """
        pagination = SearchPagination(
            total=0,
            limit=20,
            offset=0,
            has_more=False
        )
        
        search_info = SearchInfo(
            query=query,
            execution_time=execution_time,
            language=language,
            filters=filters,
            search_type="filter" if filters else "text"
        )
        
        return cls(
            results=[],
            pagination=pagination,
            search_info=search_info
        )
    
    @classmethod
    def from_products(cls, products: List[Product], query: str, 
                     limit: int = 20, offset: int = 0,
                     execution_time: float = 0.0,
                     language: Optional[str] = None,
                     filters: Optional[Dict[str, Any]] = None,
                     available_filters: Optional[Dict[str, List[Any]]] = None) -> 'SearchResult':
        """
        Create search result from list of products.
        
        Args:
            products: List of matching products
            query: Search query
            limit: Results per page
            offset: Pagination offset
            execution_time: Search execution time
            language: Language preference
            filters: Applied filters
            available_filters: Available filter options
            
        Returns:
            SearchResult instance
        """
        total_count = len(products)
        
        # Apply pagination
        end_index = offset + limit
        page_results = products[offset:end_index]
        
        pagination = SearchPagination(
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=end_index < total_count
        )
        
        search_info = SearchInfo(
            query=query,
            execution_time=execution_time,
            language=language,
            filters=filters,
            search_type="filter" if filters else "text"
        )
        
        return cls(
            results=page_results,
            pagination=pagination,
            search_info=search_info,
            available_filters=available_filters
        )