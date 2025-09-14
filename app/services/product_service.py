"""
Product service for Firestore-based product management.

This service replaces the Excel-based product loading with Firestore queries,
providing faster startup and real-time data access.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from app.models.product import Product, ProductDescriptions, ProductSpecifications, ProductPricing
from app.services.firebase_service import FirebaseService
from google.cloud.firestore_v1 import FieldFilter


class ProductService:
    """Service for managing products in Firestore."""
    
    def __init__(self, firebase_service: FirebaseService):
        """Initialize the product service."""
        self.firebase_service = firebase_service
        self.logger = logging.getLogger(__name__)
        self._products_cache: Dict[str, Product] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 300  # Cache for 5 minutes
    
    def is_available(self) -> bool:
        """Check if the service is available."""
        return self.firebase_service.is_available()
    
    def _get_collection_ref(self):
        """Get the products collection reference."""
        if not self.firebase_service.is_available():
            raise Exception("Firebase service not available")
        return self.firebase_service._db.collection('products')
    
    def _firestore_doc_to_product(self, doc_data: Dict[str, Any], doc_id: str) -> Product:
        """Convert Firestore document to Product object."""
        try:
            # Extract descriptions
            descriptions_data = doc_data.get('descriptions', {})
            descriptions = ProductDescriptions(
                hebrew=descriptions_data.get('hebrew', ''),
                english=descriptions_data.get('english', '')
            )
            
            # Extract specifications
            specifications = None
            specs_data = doc_data.get('specifications', {})
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
            pricing_data = doc_data.get('pricing')
            if pricing_data:
                pricing = ProductPricing(
                    price=pricing_data.get('price', 0.0),
                    currency=pricing_data.get('currency', 'ILS'),
                    bulk_pricing=pricing_data.get('bulk_pricing'),
                    price_type=pricing_data.get('price_type', 'standard'),
                    minimum_quantity=pricing_data.get('minimum_quantity', 1)
                )
            
            # Create product
            product = Product(
                menora_id=doc_data.get('menora_id', doc_id),
                supplier_code=doc_data.get('supplier_code', ''),
                descriptions=descriptions,
                category=doc_data.get('category', 'cable_tray'),
                subcategory=doc_data.get('subcategory'),
                specifications=specifications,
                pricing=pricing,
                search_terms=doc_data.get('search_terms', {}),
                in_stock=doc_data.get('in_stock', True),
                lead_time=doc_data.get('lead_time', 7),
                tags=doc_data.get('tags', []),
                supplier_name=doc_data.get('supplier_name', 'HOLDEE'),
                image_url=doc_data.get('image_url'),
                image_path=doc_data.get('image_path'),
                has_image=doc_data.get('has_image', False)
            )
            
            return product
            
        except Exception as e:
            self.logger.error(f"Error converting Firestore doc to Product: {str(e)}")
            raise
    
    def get_all_products(self, use_cache: bool = True) -> List[Product]:
        """
        Get all products from Firestore.
        
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
            collection_ref = self._get_collection_ref()
            docs = collection_ref.stream()
            
            products = []
            for doc in docs:
                try:
                    product = self._firestore_doc_to_product(doc.to_dict(), doc.id)
                    products.append(product)
                    self._products_cache[product.menora_id] = product
                except Exception as e:
                    self.logger.error(f"Error processing product document {doc.id}: {str(e)}")
                    continue
            
            self._cache_timestamp = datetime.now(timezone.utc)
            self.logger.info(f"Loaded {len(products)} products from Firestore")
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading products from Firestore: {str(e)}")
            # Return cached data if available
            if self._products_cache:
                self.logger.warning("Returning cached products due to Firestore error")
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
            collection_ref = self._get_collection_ref()
            doc_ref = collection_ref.document(menora_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            product = self._firestore_doc_to_product(doc.to_dict(), doc.id)
            self._products_cache[menora_id] = product
            
            return product
            
        except Exception as e:
            self.logger.error(f"Error loading product {menora_id} from Firestore: {str(e)}")
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
            # TODO: Implement proper Firestore full-text search when available
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
        Get products by category.
        
        Args:
            category: Product category
            limit: Maximum number of results
            
        Returns:
            List of Product objects
        """
        try:
            collection_ref = self._get_collection_ref()
            query = collection_ref.where(
                filter=FieldFilter('category', '==', category)
            ).limit(limit)
            
            docs = query.stream()
            
            products = []
            for doc in docs:
                try:
                    product = self._firestore_doc_to_product(doc.to_dict(), doc.id)
                    products.append(product)
                except Exception as e:
                    self.logger.error(f"Error processing product document {doc.id}: {str(e)}")
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
            collection_ref = self._get_collection_ref()
            query = collection_ref.where(
                filter=FieldFilter('in_stock', '==', True)
            ).limit(limit)
            
            docs = query.stream()
            
            products = []
            for doc in docs:
                try:
                    product = self._firestore_doc_to_product(doc.to_dict(), doc.id)
                    products.append(product)
                except Exception as e:
                    self.logger.error(f"Error processing product document {doc.id}: {str(e)}")
                    continue
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading in-stock products: {str(e)}")
            return []
    
    def create_product(self, product: Product) -> bool:
        """
        Create a new product in Firestore.
        
        Args:
            product: Product object to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection_ref = self._get_collection_ref()
            doc_ref = collection_ref.document(product.menora_id)
            
            # Convert product to Firestore document format
            doc_data = {
                'menora_id': product.menora_id,
                'supplier_code': product.supplier_code,
                'descriptions': {
                    'hebrew': product.descriptions.hebrew if product.descriptions else '',
                    'english': product.descriptions.english if product.descriptions else ''
                },
                'category': product.category,
                'subcategory': product.subcategory,
                'specifications': product.specifications.to_dict() if product.specifications else {},
                'pricing': product.pricing.to_dict() if product.pricing else None,
                'search_terms': product.search_terms or {},
                'in_stock': product.in_stock,
                'lead_time': product.lead_time,
                'tags': product.tags or [],
                'supplier_name': product.supplier_name,
                'image_url': product.image_url,
                'image_path': product.image_path,
                'has_image': product.has_image,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            doc_ref.set(doc_data)
            
            # Update cache
            self._products_cache[product.menora_id] = product
            
            self.logger.info(f"Created product {product.menora_id} in Firestore")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating product {product.menora_id}: {str(e)}")
            return False
    
    def update_product(self, product: Product) -> bool:
        """
        Update an existing product in Firestore.
        
        Args:
            product: Product object to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection_ref = self._get_collection_ref()
            doc_ref = collection_ref.document(product.menora_id)
            
            # Check if document exists
            if not doc_ref.get().exists:
                self.logger.error(f"Product {product.menora_id} not found for update")
                return False
            
            # Convert product to Firestore document format
            doc_data = {
                'menora_id': product.menora_id,
                'supplier_code': product.supplier_code,
                'descriptions': {
                    'hebrew': product.descriptions.hebrew if product.descriptions else '',
                    'english': product.descriptions.english if product.descriptions else ''
                },
                'category': product.category,
                'subcategory': product.subcategory,
                'specifications': product.specifications.to_dict() if product.specifications else {},
                'pricing': product.pricing.to_dict() if product.pricing else None,
                'search_terms': product.search_terms or {},
                'in_stock': product.in_stock,
                'lead_time': product.lead_time,
                'tags': product.tags or [],
                'supplier_name': product.supplier_name,
                'image_url': product.image_url,
                'image_path': product.image_path,
                'has_image': product.has_image,
                'updated_at': datetime.now(timezone.utc)
            }
            
            doc_ref.update(doc_data)
            
            # Update cache
            self._products_cache[product.menora_id] = product
            
            self.logger.info(f"Updated product {product.menora_id} in Firestore")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating product {product.menora_id}: {str(e)}")
            return False
    
    def delete_product(self, menora_id: str) -> bool:
        """
        Delete a product from Firestore.
        
        Args:
            menora_id: Product ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection_ref = self._get_collection_ref()
            doc_ref = collection_ref.document(menora_id)
            
            # Check if document exists
            if not doc_ref.get().exists:
                self.logger.error(f"Product {menora_id} not found for deletion")
                return False
            
            doc_ref.delete()
            
            # Remove from cache
            if menora_id in self._products_cache:
                del self._products_cache[menora_id]
            
            self.logger.info(f"Deleted product {menora_id} from Firestore")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting product {menora_id}: {str(e)}")
            return False
    
    def get_product_count(self) -> int:
        """
        Get total number of products.
        
        Returns:
            Total product count
        """
        try:
            # Use cache if available
            if self._products_cache and self._cache_timestamp:
                return len(self._products_cache)
            
            # Count documents in collection
            collection_ref = self._get_collection_ref()
            docs = collection_ref.stream()
            count = sum(1 for _ in docs)
            
            return count
            
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