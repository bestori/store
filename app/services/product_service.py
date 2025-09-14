"""
Product service for PostgreSQL-based product management.

This service provides product queries from PostgreSQL database,
providing fast access to product data loaded from Excel files.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import json

from app.models.product import Product, ProductDescriptions, ProductSpecifications, ProductPricing
from app.services.database_service import DatabaseService


class ProductService:
    """Service for managing products in PostgreSQL."""
    
    def __init__(self, database_service: DatabaseService):
        """Initialize the product service."""
        self.database_service = database_service
        self.logger = logging.getLogger(__name__)
        self._products_cache: Dict[str, Product] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # Cache for 5 minutes
    
    def is_available(self) -> bool:
        """Check if the service is available."""
        return self.database_service.is_available()
    
    def _get_products_from_db(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get products from PostgreSQL database."""
        if not self.database_service.is_available():
            raise Exception("Database service not available")
        return self.database_service.execute_query(
            "SELECT * FROM products ORDER BY name_hebrew, menora_id LIMIT :limit",
            {'limit': limit}
        )
    
    def _db_row_to_product(self, row_data: Dict[str, Any]) -> Product:
        """Convert PostgreSQL row to Product object."""
        try:
            # Extract descriptions
            descriptions = ProductDescriptions(
                hebrew=row_data.get('name_hebrew', ''),
                english=row_data.get('name_english', '')
            )
            
            # Extract specifications from JSON field
            specifications = None
            specs_data = {}
            if row_data.get('specifications'):
                try:
                    specs_data = json.loads(row_data['specifications'])
                except (json.JSONDecodeError, TypeError):
                    specs_data = {}
            
            if specs_data:
                specifications = ProductSpecifications(
                    type=specs_data.get('type', ''),
                    height=specs_data.get('height'),
                    width=specs_data.get('width'),
                    thickness=specs_data.get('thickness'),
                    galvanization=specs_data.get('galvanization'),
                    material=specs_data.get('material'),
                    length=specs_data.get('length'),
                    weight=specs_data.get('weight'),
                    load_capacity=specs_data.get('load_capacity'),
                    finish=specs_data.get('finish')
                )
            
            # Extract pricing
            pricing = None
            price = row_data.get('price', 0.0)
            if price and price > 0:
                pricing = ProductPricing(
                    price=float(price),
                    currency='ILS',
                    bulk_pricing=None,
                    price_type='standard',
                    minimum_quantity=1
                )
            
            # Create product
            product = Product(
                menora_id=row_data.get('menora_id', ''),
                supplier_code=row_data.get('supplier_code', ''),
                descriptions=descriptions,
                category=row_data.get('category', 'cable_tray'),
                subcategory=row_data.get('subcategory'),
                specifications=specifications,
                pricing=pricing,
                search_terms={},
                in_stock=True,
                lead_time=7,
                tags=[],
                supplier_name='HOLDEE',
                image_url=None,
                image_path=None,
                has_image=False
            )
            
            return product
            
        except Exception as e:
            self.logger.error(f"Error converting database row to Product: {str(e)}")
            raise
    
    def get_all_products(self, use_cache: bool = True) -> List[Product]:
        """
        Get all products from PostgreSQL database.
        
        Args:
            use_cache: Whether to use cached results
            
        Returns:
            List of Product objects
        """
        # Check cache validity
        if (use_cache and self._products_cache and self._cache_timestamp and 
            (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds() < self._cache_ttl):
            return list(self._products_cache.values())
        
        try:
            rows = self._get_products_from_db(limit=10000)  # Get all products
            
            products = []
            for row in rows:
                try:
                    product = self._db_row_to_product(row)
                    products.append(product)
                    self._products_cache[product.menora_id] = product
                except Exception as e:
                    self.logger.error(f"Error processing product row {row.get('id', 'unknown')}: {str(e)}")
                    continue
            
            self._cache_timestamp = datetime.now(timezone.utc)
            self.logger.info(f"Loaded {len(products)} products from PostgreSQL database")
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading products from PostgreSQL database: {str(e)}")
            # Return cached data if available
            if self._products_cache:
                self.logger.warning("Returning cached products due to database error")
                return list(self._products_cache.values())
            return []
    
    def get_product_by_id(self, menora_id: str) -> Optional[Product]:
        """
        Get a specific product by ID.
        
        Args:
            menora_id: Product ID to search for
            
        Returns:
            Product object if found, None otherwise
        """
        # Check cache first
        if menora_id in self._products_cache:
            return self._products_cache[menora_id]
        
        try:
            results = self.database_service.execute_query(
                "SELECT * FROM products WHERE menora_id = :menora_id",
                {'menora_id': menora_id}
            )
            
            if not results:
                return None
            
            product = self._db_row_to_product(results[0])
            self._products_cache[menora_id] = product
            
            return product
            
        except Exception as e:
            self.logger.error(f"Error loading product {menora_id} from PostgreSQL database: {str(e)}")
            return None
    
    def search_products(self, query: str, language: Optional[str] = None, 
                       filters: Optional[Dict[str, Any]] = None, 
                       limit: int = 100, offset: int = 0) -> Tuple[List[Product], int]:
        """
        Search products with query and filters.
        
        Args:
            query: Search query string
            language: Preferred language (hebrew/english)
            filters: Additional filter criteria
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Tuple of (products, total_count)
        """
        try:
            # For now, get all products and filter in memory
            # TODO: Implement proper PostgreSQL full-text search when available
            all_products = self.get_all_products()
            
            # Apply text search
            matching_products = []
            if query:
                for product in all_products:
                    if product.matches_search(query, language):
                        matching_products.append(product)
            else:
                matching_products = all_products
            
            # Apply filters
            if filters:
                filtered_products = []
                for product in matching_products:
                    if product.matches_filters(filters):
                        filtered_products.append(product)
                matching_products = filtered_products
            
            total_count = len(matching_products)
            
            # Apply pagination
            end_idx = offset + limit
            paginated_products = matching_products[offset:end_idx]
            
            return paginated_products, total_count
            
        except Exception as e:
            self.logger.error(f"Error searching products: {str(e)}")
            return [], 0
    
    def get_products_by_category(self, category: str, limit: int = 100) -> List[Product]:
        """
        Get products by category from PostgreSQL.
        
        Args:
            category: Product category
            limit: Maximum number of results
            
        Returns:
            List of Product objects
        """
        try:
            results = self.database_service.execute_query(
                "SELECT * FROM products WHERE category = :category LIMIT :limit",
                {'category': category, 'limit': limit}
            )
            
            products = []
            for row in results:
                try:
                    product = self._db_row_to_product(row)
                    products.append(product)
                except Exception as e:
                    self.logger.error(f"Error processing product row: {str(e)}")
                    continue
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading products by category {category}: {str(e)}")
            return []
    
    def get_products_in_stock(self, limit: int = 100) -> List[Product]:
        """
        Get products that are in stock.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of Product objects
        """
        try:
            results = self.database_service.execute_query(
                "SELECT * FROM products WHERE in_stock = true LIMIT :limit",
                {'limit': limit}
            )
            
            products = []
            for row in results:
                try:
                    product = self._db_row_to_product(row)
                    products.append(product)
                except Exception as e:
                    self.logger.error(f"Error processing product row: {str(e)}")
                    continue
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading in-stock products: {str(e)}")
            return []
    
    def create_product(self, product: Product) -> bool:
        """
        Create a new product in PostgreSQL.
        
        Args:
            product: Product object to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert product to database format
            product_data = {
                'menora_id': product.menora_id,
                'name_hebrew': product.descriptions.hebrew if product.descriptions else '',
                'name_english': product.descriptions.english if product.descriptions else '',
                'description_hebrew': product.descriptions.hebrew if product.descriptions else '',
                'description_english': product.descriptions.english if product.descriptions else '',
                'price': product.pricing.price if product.pricing else 0,
                'category': product.category,
                'subcategory': product.subcategory or '',
                'specifications': json.dumps(product.specifications.to_dict() if product.specifications else {}),
                'dimensions': '{}',
                'weight': product.specifications.weight if product.specifications and product.specifications.weight else 0,
                'material': product.specifications.material if product.specifications and product.specifications.material else '',
                'coating': product.specifications.finish if product.specifications and product.specifications.finish else '',
                'standard': ''
            }
            
            success = self.database_service.insert_product(product_data)
            
            if success:
                self.logger.info(f"Created product {product.menora_id} in PostgreSQL")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error creating product {product.menora_id}: {str(e)}")
            return False
    
    def update_product(self, product: Product) -> bool:
        """
        Update an existing product in PostgreSQL.
        
        Args:
            product: Product object to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert product to database format
            product_data = {
                'menora_id': product.menora_id,
                'name_hebrew': product.descriptions.hebrew if product.descriptions else '',
                'name_english': product.descriptions.english if product.descriptions else '',
                'description_hebrew': product.descriptions.hebrew if product.descriptions else '',
                'description_english': product.descriptions.english if product.descriptions else '',
                'price': product.pricing.price if product.pricing else 0,
                'category': product.category,
                'subcategory': product.subcategory or '',
                'specifications': json.dumps(product.specifications.to_dict() if product.specifications else {}),
                'dimensions': '{}',
                'weight': product.specifications.weight if product.specifications and product.specifications.weight else 0,
                'material': product.specifications.material if product.specifications and product.specifications.material else '',
                'coating': product.specifications.finish if product.specifications and product.specifications.finish else '',
                'standard': ''
            }
            
            success = self.database_service.insert_product(product_data)
            
            if success:
                self.logger.info(f"Updated product {product.menora_id} in PostgreSQL")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating product {product.menora_id}: {str(e)}")
            return False
    
    def delete_product(self, menora_id: str) -> bool:
        """
        Delete a product from PostgreSQL.
        
        Args:
            menora_id: Product ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.database_service.execute_update(
                "DELETE FROM products WHERE menora_id = :menora_id",
                {'menora_id': menora_id}
            )
            
            if success:
                self.logger.info(f"Deleted product {menora_id} from PostgreSQL")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting product {menora_id}: {str(e)}")
            return False
    
    def get_product_count(self) -> int:
        """
        Get total number of products from PostgreSQL.
        
        Returns:
            Total product count
        """
        try:
            result = self.database_service.execute_query("SELECT COUNT(*) as count FROM products")
            return result[0]['count'] if result else 0
            
        except Exception as e:
            self.logger.error(f"Error getting product count: {str(e)}")
            return 0
    
    def clear_cache(self):
        """Clear the products cache."""
        self._products_cache.clear()
        self._cache_timestamp = None
        self.logger.info("Product cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'cache_size': len(self._products_cache),
            'cache_timestamp': self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            'cache_ttl': self._cache_ttl,
            'cache_expired': (
                self._cache_timestamp is None or 
                (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds() >= self._cache_ttl
            )
        }