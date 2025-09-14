"""
Search service for finding products in the database.

This service provides text search and filtered search capabilities
across the product catalog stored in PostgreSQL.
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional

from app.models.product import Product
from app.models.search_result import SearchResult, SearchPagination, SearchInfo


class SearchService:
    """
    Service for searching products in database.
    
    Provides text search, filtered search, and search suggestions.
    """
    
    def __init__(self, excel_data: Dict[str, Any], product_service=None, database_service=None):
        """
        Initialize search service with database service.
        
        Args:
            excel_data: Dictionary containing loaded products and metadata (unused for database search)
            product_service: Optional ProductService for Firestore queries (unused)
            database_service: DatabaseService for PostgreSQL queries
        """
        self.logger = logging.getLogger(__name__)
        
        # Store services
        self.database_service = database_service
        self.product_service = product_service
        
        # Hebrew type translations (from actual Excel data)
        self.type_translations = {
            'Cable Tray (HMW)': 'מוצר HMW',
            'Cable Trunking': 'תעלת תקשורת', 
            'Channel Cable Tray': 'תעלה מלאה',
            'Decorated Cable Tray': 'תעלה מחורצת דקורטיבית',
            'Ladder Cable Tray': 'תעלה סולם',
            'Perforated Cable Tray': 'תעלה מחורצת'
        }
        
        self.logger.info("Search service initialized with database backend")
    
    def text_search(self, query: str, language: Optional[str] = None,
                    limit: int = 20, offset: int = 0) -> SearchResult:
        """
        Perform text search on product names and descriptions.
        """
        start_time = time.time()
        
        # Use database service for search
        if self.database_service:
            try:
                # Get more results to handle pagination
                db_results = self.database_service.search_products(query, limit=limit + offset)
                self.logger.info(f"Database returned {len(db_results)} results for query '{query}'")
                
                # Apply pagination
                paginated_results = db_results[offset:offset + limit] if len(db_results) > offset else []
                
                execution_time = time.time() - start_time
                
                # Convert database results to properly formatted products
                simple_products = []
                for db_product in paginated_results:
                    # Create a properly formatted product object
                    class SimpleProduct:
                        def __init__(self, db_data):
                            self.db_data = db_data
                        
                        def to_dict(self):
                            # Parse JSON fields safely
                            try:
                                specs = json.loads(self.db_data.get('specifications', '{}')) if self.db_data.get('specifications') else {}
                            except:
                                specs = {}
                            
                            try:
                                dimensions = json.loads(self.db_data.get('dimensions', '{}')) if self.db_data.get('dimensions') else {}
                            except:
                                dimensions = {}
                            
                            return {
                                'id': self.db_data.get('id'),
                                'menora_id': self.db_data.get('menora_id', ''),
                                'hebrew': self.db_data.get('name_hebrew', ''),
                                'english': self.db_data.get('name_english', ''),
                                'price': self.db_data.get('price', 0),
                                'currency': '₪',
                                'type': specs.get('type', ''),
                                'material': self.db_data.get('material', '') or specs.get('material', ''),
                                'height': dimensions.get('height', ''),
                                'width': dimensions.get('width', ''),
                                'thickness': dimensions.get('thickness', ''),
                                'category': self.db_data.get('category', ''),
                                'subcategory': self.db_data.get('subcategory', ''),
                                'description_hebrew': self.db_data.get('description_hebrew', ''),
                                'description_english': self.db_data.get('description_english', ''),
                                'image_url': None,
                                'has_image': False
                            }
                    
                    simple_products.append(SimpleProduct(db_product))
                
                # Create search result
                pagination = SearchPagination(
                    total=len(db_results),
                    limit=limit,
                    offset=offset,
                    has_more=len(db_results) > offset + limit
                )
                
                search_info = SearchInfo(
                    query=query,
                    execution_time=execution_time,
                    language=language,
                    search_type="text"
                )
                
                result = SearchResult(
                    results=simple_products,
                    pagination=pagination,
                    search_info=search_info
                )
                
                self.logger.info(f"Database search '{query}': {len(paginated_results)} results in {execution_time:.3f}s")
                return result
                
            except Exception as e:
                self.logger.error(f"Database search failed: {e}")
                # Fall through to empty result
        
        # Fallback: return empty result
        execution_time = time.time() - start_time
        return SearchResult.create_empty(query, execution_time, language)
    
    def filter_search(self, filters: Dict[str, Any], limit: int = 20, offset: int = 0) -> SearchResult:
        """Perform filtered search - for now just return empty results."""
        start_time = time.time()
        execution_time = time.time() - start_time
        return SearchResult.create_empty(str(filters), execution_time, filters=filters)
    
    def combined_search(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None,
                       language: Optional[str] = None, limit: int = 20, offset: int = 0) -> SearchResult:
        """Perform combined search - for now just use text search."""
        if query:
            return self.text_search(query, language, limit, offset)
        else:
            return self.filter_search(filters or {}, limit, offset)
    
    def get_available_filters(self, language: str = 'hebrew') -> Dict[str, List[Any]]:
        """Get available filter options."""
        return {}
    
    def get_popular_searches(self, limit: int = 10) -> List[str]:
        """Get popular search terms."""
        return ["100", "תעלה", "cable", "tray"]
    
    def get_suggestions(self, partial_query: str, language: Optional[str] = None, 
                       max_suggestions: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        # For now return popular searches
        return self.get_popular_searches(max_suggestions)
    
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        if self.database_service:
            try:
                results = self.database_service.execute_query(
                    "SELECT * FROM products WHERE menora_id = :product_id",
                    {"product_id": product_id}
                )
                if results:
                    # Convert to Product object if needed
                    return results[0]
            except Exception as e:
                self.logger.error(f"Failed to get product by ID: {e}")
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get search service statistics."""
        stats = {
            'total_products': 0,
            'database_available': bool(self.database_service),
        }
        
        if self.database_service:
            try:
                stats['total_products'] = self.database_service.get_products_count()
            except:
                pass
        
        return stats