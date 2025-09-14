"""
Search service for finding products in the cached Excel data.

This service provides text search and filtered search capabilities
across the in-memory product catalog.
"""

import logging
import time
from typing import Dict, List, Any, Optional
import re

from app.models.product import Product
from app.models.search_result import SearchResult


class SearchService:
    """
    Service for searching products in cached Excel data.
    
    Provides text search, filtered search, and search suggestions.
    """
    
    def __init__(self, excel_data: Dict[str, Any], product_service=None, database_service=None):
        """
        Initialize search service with Excel data and optional services.
        
        Args:
            excel_data: Dictionary containing loaded products and metadata
            product_service: Optional ProductService for Firestore queries
            database_service: Optional DatabaseService for PostgreSQL queries
        """
        self.logger = logging.getLogger(__name__)
        
        # Cache data references
        self.products: List[Product] = excel_data.get('products', [])
        self.filter_options: Dict[str, List[Any]] = excel_data.get('filter_options', {})
        self.product_service = product_service
        self.database_service = database_service
        
        # If we have database service but no products, load from database
        if self.database_service and len(self.products) == 0:
            self.logger.info("Loading products from database for search")
            try:
                db_products = self.database_service.get_all_products()
                self.logger.info(f"Loaded {len(db_products)} products from database")
                # Convert database products to Product objects for search
                # For now just store raw data
                self.db_products = db_products
            except Exception as e:
                self.logger.error(f"Failed to load products from database: {e}")
                self.db_products = []
        
        # Hebrew type translations (from actual Excel data)
        self.type_translations = {
            'Cable Tray (HMW)': 'מוצר HMW',
            'Cable Trunking': 'תעלת תקשורת', 
            'Channel Cable Tray': 'תעלה מלאה',
            'Decorated Cable Tray': 'תעלה מחורצת דקורטיבית',
            'Ladder Cable Tray': 'תעלה סולם',
            'Perforated Cable Tray': 'תעלה מחורצת'
        }
        
        # Use ProductService if available, otherwise use cached products
        products_source = "ProductService" if self.product_service else "cached products"
    
    def text_search(self, query: str, language: Optional[str] = None,
                    limit: int = 20, offset: int = 0) -> SearchResult:
        """
        Perform text search on product names and descriptions.
        """
        start_time = time.time()
        
        # If we have database service, search directly in database
        if self.database_service:
            try:
                db_results = self.database_service.search_products(query, limit=limit + offset)
                # Apply offset manually
                paginated_results = db_results[offset:offset + limit] if len(db_results) > offset else []
                
                execution_time = time.time() - start_time
                
                # Convert to SearchResult format - create simple Product-like objects
                simple_products = []
                for db_product in paginated_results:
                    # Create a simple object that has to_dict method
                    class SimpleProduct:
                        def __init__(self, db_data):
                            self.db_data = db_data
                        def to_dict(self):
                            return self.db_data
                    simple_products.append(SimpleProduct(db_product))
                
                from app.models.search_result import SearchResult, SearchPagination, SearchInfo
                
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
                
                self.logger.info(f"Database search '{query}': {len(db_results)} results in {execution_time:.3f}s")
                return result
                
            except Exception as e:
                self.logger.error(f"Database search failed: {e}")
                # Fall through to empty result
        
        # Fallback: return empty result
        execution_time = time.time() - start_time
        from app.models.search_result import SearchResult
        return SearchResult.create_empty(query, execution_time, language)
    
    def filter_search(self, filters: Dict[str, Any], limit: int = 20, offset: int = 0) -> SearchResult:
        """Perform filtered search - for now just return empty results."""
        start_time = time.time()
        execution_time = time.time() - start_time
        from app.models.search_result import SearchResult
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
    
    def get_popular_searches(self) -> List[str]:
        """Get popular search terms."""
        return ["100", "תעלה", "cable", "tray"]

        product_count = len(self.products)
        if self.product_service:
            try:
                product_count = self.product_service.get_product_count()
            except:
                product_count = 0
        
        self.logger.info(f"Search service initialized with {product_count} products from {products_source}")
    
    def text_search(self, query: str, language: Optional[str] = None, 
                   limit: int = 20, offset: int = 0) -> SearchResult:
        """
        Perform text search across products.
        
        Args:
            query: Search query string
            language: Preferred language (hebrew/english)
            limit: Maximum results per page
            offset: Pagination offset
            
        Returns:
            SearchResult with matching products
        """
        start_time = time.time()
        
        try:
            if not query or not query.strip():
                return SearchResult.create_empty("", 0.0, language)
            
            query = query.strip()
            self.logger.debug(f"Text search: '{query}' (language: {language})")
            
            # Find matching products
            if self.product_service and self.product_service.is_available():
                # Use ProductService for Firestore search
                try:
                    matching_products, total_count = self.product_service.search_products(
                        query=query, 
                        language=language, 
                        limit=limit + 100,  # Get more for better sorting
                        offset=offset
                    )
                except Exception as e:
                    self.logger.error(f"ProductService search failed: {str(e)}")
                    matching_products = []
            else:
                # Fallback to in-memory search
                matching_products = []
                for product in self.products:
                    if product.matches_search(query, language):
                        matching_products.append(product)
            
            execution_time = time.time() - start_time
            
            # Create search result
            result = SearchResult.from_products(
                products=matching_products,
                query=query,
                limit=limit,
                offset=offset,
                execution_time=execution_time,
                language=language,
                available_filters=self._get_filters_for_products(matching_products)
            )
            
            self.logger.info(f"Text search '{query}': {len(matching_products)} results in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in text search '{query}': {str(e)}")
            return SearchResult.create_empty(query, time.time() - start_time, language)
    
    def filter_search(self, filters: Dict[str, Any], limit: int = 20, 
                     offset: int = 0) -> SearchResult:
        """
        Perform filtered search using product specifications.
        
        Args:
            filters: Dictionary of filter criteria
            limit: Maximum results per page
            offset: Pagination offset
            
        Returns:
            SearchResult with matching products
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Filter search: {filters}")
            
            # Find matching products
            matching_products = []
            
            for product in self.products:
                if product.matches_filters(filters):
                    matching_products.append(product)
            
            execution_time = time.time() - start_time
            
            # Create search result
            result = SearchResult.from_products(
                products=matching_products,
                query=str(filters),
                limit=limit,
                offset=offset,
                execution_time=execution_time,
                filters=filters,
                available_filters=self._get_filters_for_products(matching_products)
            )
            
            self.logger.info(f"Filter search {filters}: {len(matching_products)} results in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in filter search {filters}: {str(e)}")
            return SearchResult.create_empty(str(filters), time.time() - start_time, filters=filters)
    
    def combined_search(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None,
                       language: Optional[str] = None, limit: int = 20, offset: int = 0) -> SearchResult:
        """
        Perform combined text and filter search.
        
        Args:
            query: Optional text query
            filters: Optional filter criteria
            language: Preferred language for text search
            limit: Maximum results per page
            offset: Pagination offset
            
        Returns:
            SearchResult with matching products
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Combined search - Query: '{query}', Filters: {filters}")
            
            # Find matching products
            matching_products = []
            
            for product in self.products:
                # Check text match if query provided
                text_match = True
                if query and query.strip():
                    text_match = product.matches_search(query.strip(), language)
                
                # Check filter match if filters provided
                filter_match = True
                if filters:
                    filter_match = product.matches_filters(filters)
                
                # Product must match both criteria
                if text_match and filter_match:
                    matching_products.append(product)
            
            execution_time = time.time() - start_time
            
            # Create search result
            search_query = query or str(filters)
            result = SearchResult.from_products(
                products=matching_products,
                query=search_query,
                limit=limit,
                offset=offset,
                execution_time=execution_time,
                language=language,
                filters=filters,
                available_filters=self._get_filters_for_products(matching_products)
            )
            
            self.logger.info(f"Combined search '{query}' + {filters}: {len(matching_products)} results in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in combined search '{query}' + {filters}: {str(e)}")
            return SearchResult.create_empty(query or str(filters), time.time() - start_time, language, filters)
    
    def get_suggestions(self, partial_query: str, language: Optional[str] = None, 
                       max_suggestions: int = 5) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            language: Preferred language
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested search terms
        """
        try:
            if not partial_query or len(partial_query.strip()) < 2:
                return []
            
            partial_query = partial_query.strip().lower()
            suggestions = set()
            
            # Collect suggestions from product data
            for product in self.products:
                if not product.search_terms:
                    continue
                
                # Check search terms
                terms_to_check = []
                if language == 'hebrew' and product.search_terms.get('hebrew'):
                    terms_to_check = product.search_terms['hebrew']
                elif language == 'english' and product.search_terms.get('english'):
                    terms_to_check = product.search_terms['english']
                else:
                    # Check both languages
                    terms_to_check = (product.search_terms.get('hebrew', []) + 
                                    product.search_terms.get('english', []))
                
                # Find matching terms
                for term in terms_to_check:
                    if isinstance(term, str) and len(term) > 2:
                        term_lower = term.lower()
                        if partial_query in term_lower:
                            suggestions.add(term)
                            
                            # Also add the beginning of the term if it starts with partial query
                            if term_lower.startswith(partial_query):
                                suggestions.add(term)
                
                # Stop when we have enough suggestions
                if len(suggestions) >= max_suggestions * 2:  # Get more to filter later
                    break
            
            # Sort suggestions by relevance (starts with query first)
            suggestions_list = list(suggestions)
            starts_with = [s for s in suggestions_list if s.lower().startswith(partial_query)]
            contains = [s for s in suggestions_list if s.lower() != partial_query and partial_query in s.lower() and not s.lower().startswith(partial_query)]
            
            # Combine and limit
            final_suggestions = starts_with[:max_suggestions//2] + contains[:max_suggestions//2]
            
            return final_suggestions[:max_suggestions]
            
        except Exception as e:
            self.logger.error(f"Error getting suggestions for '{partial_query}': {str(e)}")
            return []
    
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """
        Get product by Menora ID.
        
        Args:
            product_id: Menora catalog number
            
        Returns:
            Product instance or None if not found
        """
        try:
            for product in self.products:
                if product.menora_id == product_id:
                    return product
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting product {product_id}: {str(e)}")
            return None
    
    def get_available_filters(self, language: Optional[str] = None) -> Dict[str, List[Any]]:
        """
        Get all available filter options, optionally translated to Hebrew.
        
        Args:
            language: Language preference (hebrew/english)
            
        Returns:
            Dictionary of filter options
        """
        filters = self.filter_options.copy()
        
        # If Hebrew is requested and we have type options, translate them
        if language == 'hebrew' and 'type' in filters:
            hebrew_types = []
            for english_type in filters['type']:
                hebrew_translation = self.type_translations.get(english_type, english_type)
                hebrew_types.append({
                    'value': english_type,  # Keep English value for backend filtering
                    'label': hebrew_translation  # Show Hebrew label in UI
                })
            filters['type'] = hebrew_types
        
        return filters
    
    def _get_filters_for_products(self, products: List[Product]) -> Dict[str, List[Any]]:
        """
        Get available filter options for a specific set of products.
        
        Args:
            products: List of products to analyze
            
        Returns:
            Dictionary of available filters
        """
        try:
            if not products:
                return {}
            
            filters = {
                'type': set(),
                'height': set(),
                'width': set(),
                'thickness': set(),
                'galvanization': set(),
                'category': set()
            }
            
            for product in products:
                if product.specifications:
                    spec = product.specifications
                    if spec.type:
                        filters['type'].add(spec.type)
                    if spec.height:
                        filters['height'].add(spec.height)
                    if spec.width:
                        filters['width'].add(spec.width)
                    if spec.thickness:
                        filters['thickness'].add(spec.thickness)
                    if spec.galvanization:
                        filters['galvanization'].add(spec.galvanization)
                
                if product.category:
                    filters['category'].add(product.category)
            
            # Convert sets to sorted lists
            result = {}
            for key, values in filters.items():
                if values:
                    if isinstance(next(iter(values)), (int, float)):
                        result[key] = sorted(list(values))
                    else:
                        result[key] = sorted(list(values))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting filters for products: {str(e)}")
            return {}
    
    def get_popular_searches(self, limit: int = 10) -> List[str]:
        """
        Get popular search terms (mock implementation).
        
        Args:
            limit: Maximum number of terms
            
        Returns:
            List of popular search terms
        """
        # In a real implementation, this would come from search analytics
        popular_terms = [
            "תעלה מחורצת",
            "cable tray",
            "TCS",
            "PCS", 
            "תעלת תקשורת",
            "מחברים",
            "connectors",
            "supports",
            "תומכים",
            "מכסים"
        ]
        
        return popular_terms[:limit]
    
    def refresh_data(self, new_excel_data: Dict[str, Any]):
        """
        Refresh search data when Excel data is reloaded.
        
        Args:
            new_excel_data: New Excel data dictionary
        """
        try:
            old_count = len(self.products)
            
            self.products = new_excel_data.get('products', [])
            self.filter_options = new_excel_data.get('filter_options', {})
            
            new_count = len(self.products)
            
            self.logger.info(f"Search data refreshed: {old_count} -> {new_count} products")
            
        except Exception as e:
            self.logger.error(f"Error refreshing search data: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get search service statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            'total_products': len(self.products),
            'filter_options_count': len(self.filter_options),
            'categories': list(set(p.category for p in self.products if p.category)),
            'types': list(self.filter_options.get('type', [])),
            'height_range': {
                'min': min(self.filter_options.get('height', [0])),
                'max': max(self.filter_options.get('height', [0]))
            } if self.filter_options.get('height') else None,
            'with_pricing': sum(1 for p in self.products if p.pricing is not None)
        }