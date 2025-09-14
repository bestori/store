"""
Shopping list service for managing user shopping lists and items.

This service handles creation, modification, and management of shopping lists
and their items, including price calculations and HTML generation.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.models.user import User
from app.models.shopping_list import ShoppingList
from app.models.shopping_item import ShoppingItem
from app.models.product import Product, ProductDescriptions, ProductSpecifications, ProductPricing
from app.services.database_service import DatabaseService


class ShoppingListService:
    """
    Service for shopping list management.
    
    Handles shopping list CRUD operations, item management,
    and price calculations using PostgreSQL.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize shopping list service.
        
        Args:
            database_service: Database service instance
        """
        self.db = database_service
        self.logger = logging.getLogger(__name__)
    
    def get_user_shopping_lists(self, user: User) -> List[ShoppingList]:
        """
        Get all shopping lists for a user.
        
        Args:
            user: User instance
            
        Returns:
            List of user's shopping lists
        """
        try:
            # Get shopping lists from database
            results = self.db.execute_query(
                "SELECT * FROM shopping_lists WHERE user_id = :user_id ORDER BY updated_at DESC",
                {'user_id': user.user_id}
            )
            
            shopping_lists = []
            for row in results:
                # Convert database row to ShoppingList object
                shopping_list = ShoppingList.from_dict(row)
                shopping_lists.append(shopping_list)
            
            self.logger.debug(f"Retrieved {len(shopping_lists)} shopping lists for user {user.user_code}")
            
            return shopping_lists
            
        except Exception as e:
            self.logger.error(f"Error getting shopping lists for user {user.user_code}: {str(e)}")
            return []
    
    def get_shopping_list(self, list_id: str, user: User) -> Optional[ShoppingList]:
        """
        Get shopping list by ID, ensuring user ownership.
        
        Args:
            list_id: Shopping list ID
            user: User instance
            
        Returns:
            ShoppingList instance if found and owned by user, None otherwise
        """
        try:
            # Get shopping list from database with user ownership check
            results = self.db.execute_query(
                "SELECT * FROM shopping_lists WHERE list_id = :list_id AND user_id = :user_id",
                {'list_id': list_id, 'user_id': user.user_id}
            )
            
            if results:
                shopping_list = ShoppingList.from_dict(results[0])
                return shopping_list
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting shopping list {list_id}: {str(e)}")
            return None
    
    def create_shopping_list(self, user: User, list_name: str, 
                           description: Optional[str] = None) -> Optional[ShoppingList]:
        """
        Create a new shopping list for user.
        
        Args:
            user: User instance
            list_name: Name of the shopping list
            description: Optional description
            
        Returns:
            Created ShoppingList instance or None if failed
        """
        try:
            # Create new shopping list
            shopping_list = ShoppingList.create_new_list(
                user_id=user.user_id,
                user_code=user.user_code,
                list_name=list_name,
                description=description
            )
            
            # Save to database
            success = self._save_shopping_list_to_db(shopping_list)
            
            if success:
                # Update user's active lists
                user.add_shopping_list(shopping_list.list_id, set_as_default=len(user.active_lists) == 0)
                self._update_user_in_db(user)
                
                self.logger.info(f"Created shopping list '{list_name}' for user {user.user_code}")
                return shopping_list
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating shopping list for user {user.user_code}: {str(e)}")
            return None
    
    def update_shopping_list(self, shopping_list: ShoppingList, 
                           list_name: Optional[str] = None,
                           description: Optional[str] = None) -> bool:
        """
        Update shopping list information.
        
        Args:
            shopping_list: ShoppingList instance to update
            list_name: New name (optional)
            description: New description (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if list_name:
                shopping_list.list_name = list_name
            
            if description is not None:
                shopping_list.description = description
            
            shopping_list.updated_at = datetime.now(timezone.utc)
            
            success = self._save_shopping_list_to_db(shopping_list)
            
            if success:
                self.logger.info(f"Updated shopping list {shopping_list.list_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating shopping list {shopping_list.list_id}: {str(e)}")
            return False
    
    def delete_shopping_list(self, shopping_list: ShoppingList, user: User) -> bool:
        """
        Delete shopping list.
        
        Args:
            shopping_list: ShoppingList instance to delete
            user: User instance (for updating user's list references)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from database
            success = self.db.execute_update(
                "DELETE FROM shopping_lists WHERE list_id = :list_id",
                {'list_id': shopping_list.list_id}
            )
            
            if success:
                # Update user's active lists
                user.remove_shopping_list(shopping_list.list_id)
                
                self.logger.info(f"Deleted shopping list {shopping_list.list_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting shopping list {shopping_list.list_id}: {str(e)}")
            return False
    
    def add_item_to_list(self, shopping_list: ShoppingList, menora_id: str, 
                        quantity: int = 1, notes: Optional[str] = None) -> bool:
        """
        Add item to shopping list.
        
        Args:
            shopping_list: ShoppingList instance
            menora_id: Product Menora ID
            quantity: Item quantity
            notes: Optional notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find product in Excel data
            product = self._find_product_by_menora_id(menora_id)
            
            if not product:
                self.logger.error(f"Product not found: {menora_id}")
                return False
            
            # Create shopping item from product
            shopping_item = ShoppingItem.from_product(
                product_data=product.to_dict(),
                quantity=quantity,
                notes=notes
            )
            
            # Add to shopping list
            shopping_list.add_item(shopping_item)
            
            # Save to database
            success = self._save_shopping_list_to_db(shopping_list)
            
            if success:
                self.logger.info(f"Added item {menora_id} to shopping list {shopping_list.list_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error adding item {menora_id} to list {shopping_list.list_id}: {str(e)}")
            return False
    
    def update_item_in_list(self, shopping_list: ShoppingList, item_id: str,
                          quantity: Optional[int] = None, notes: Optional[str] = None) -> bool:
        """
        Update item in shopping list.
        
        Args:
            shopping_list: ShoppingList instance
            item_id: Item ID to update
            quantity: New quantity (optional)
            notes: New notes (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updated = False
            
            if quantity is not None:
                updated = shopping_list.update_item_quantity(item_id, quantity) or updated
            
            if notes is not None:
                updated = shopping_list.update_item_notes(item_id, notes) or updated
            
            if updated:
                success = self._save_shopping_list_to_db(shopping_list)
                
                if success:
                    self.logger.info(f"Updated item {item_id} in shopping list {shopping_list.list_id}")
                
                return success
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating item {item_id} in list {shopping_list.list_id}: {str(e)}")
            return False
    
    def remove_item_from_list(self, shopping_list: ShoppingList, item_id: str) -> bool:
        """
        Remove item from shopping list.
        
        Args:
            shopping_list: ShoppingList instance
            item_id: Item ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            removed = shopping_list.remove_item(item_id)
            
            if removed:
                success = self._save_shopping_list_to_db(shopping_list)
                
                if success:
                    self.logger.info(f"Removed item {item_id} from shopping list {shopping_list.list_id}")
                
                return success
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing item {item_id} from list {shopping_list.list_id}: {str(e)}")
            return False
    
    def calculate_item_pricing(self, menora_id: str, quantity: int) -> Dict[str, Any]:
        """
        Calculate pricing for an item with quantity.
        
        Args:
            menora_id: Product Menora ID
            quantity: Quantity to calculate for
            
        Returns:
            Dictionary with pricing information
        """
        try:
            product = self._find_product_by_menora_id(menora_id)
            
            if not product or not product.pricing:
                return {
                    'found': False,
                    'error': 'Product or pricing not found'
                }
            
            unit_price = product.get_price(quantity)
            total_price = unit_price * quantity if unit_price else 0
            
            pricing_info = {
                'found': True,
                'menora_id': menora_id,
                'unit_price': unit_price,
                'total_price': round(total_price, 2),
                'currency': product.pricing.currency,
                'quantity': quantity
            }
            
            # Add bulk pricing info if available
            if product.pricing.bulk_pricing:
                pricing_info['bulk_pricing'] = product.pricing.bulk_pricing
            
            return pricing_info
            
        except Exception as e:
            self.logger.error(f"Error calculating pricing for {menora_id}: {str(e)}")
            return {
                'found': False,
                'error': str(e)
            }
    
    def calculate_list_totals(self, shopping_list: ShoppingList) -> Dict[str, Any]:
        """
        Calculate totals for shopping list.
        
        Args:
            shopping_list: ShoppingList instance
            
        Returns:
            Dictionary with total calculations
        """
        try:
            # Recalculate to ensure accuracy
            shopping_list.recalculate_summary()
            
            summary = shopping_list.summary
            
            if not summary:
                return {
                    'total_items': 0,
                    'total_quantity': 0,
                    'subtotal': 0.0,
                    'tax': 0.0,
                    'total': 0.0,
                    'currency': 'ILS'
                }
            
            subtotal = summary.total_price
            tax_rate = 0.17  # Israeli VAT
            tax = subtotal * tax_rate
            total = subtotal + tax
            
            return {
                'total_items': summary.total_items,
                'total_quantity': summary.total_quantity,
                'subtotal': round(subtotal, 2),
                'tax': round(tax, 2),
                'total': round(total, 2),
                'currency': summary.currency,
                'tax_rate': tax_rate
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating list totals for {shopping_list.list_id}: {str(e)}")
            return {}
    
    def _find_product_by_menora_id(self, menora_id: str) -> Optional[Product]:
        """
        Find product by Menora ID in database.
        
        Args:
            menora_id: Menora catalog number
            
        Returns:
            Product instance or None if not found
        """
        try:
            # Query database for product
            results = self.db.execute_query(
                "SELECT * FROM products WHERE menora_id = :menora_id LIMIT 1",
                {'menora_id': menora_id}
            )
            
            if not results:
                self.logger.warning(f"Product not found in database: {menora_id}")
                return None
            
            # Convert database row to Product object
            product_data = results[0]
            return self._db_row_to_product(product_data)
            
        except Exception as e:
            self.logger.error(f"Error finding product {menora_id}: {str(e)}")
            return None
    
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
    
    def get_list_statistics(self) -> Dict[str, Any]:
        """
        Get shopping list service statistics.
        
        Returns:
            Dictionary of statistics
        """
        try:
            # Get product statistics from database
            product_count_result = self.db.execute_query("SELECT COUNT(*) as count FROM products")
            product_count = product_count_result[0]['count'] if product_count_result else 0
            
            pricing_count_result = self.db.execute_query("SELECT COUNT(*) as count FROM products WHERE price > 0")
            pricing_count = pricing_count_result[0]['count'] if pricing_count_result else 0
            
            stats = {
                'available_products': product_count,
                'products_with_pricing': pricing_count
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting list statistics: {str(e)}")
            return {}
    
    def get_or_create_default_list(self, user_code: str) -> Optional[ShoppingList]:
        """
        Get user's default shopping list or create one if none exists.
        
        Args:
            user_code: User code
            
        Returns:
            ShoppingList instance or None if failed
        """
        try:
            # Get user's existing lists
            user_id = f"user_{user_code}"
            existing_lists = self.db.execute_query(
                "SELECT * FROM shopping_lists WHERE user_id = :user_id ORDER BY created_at DESC LIMIT 1",
                {'user_id': user_id}
            )
            
            if existing_lists:
                # Return the most recent list
                return ShoppingList.from_dict(existing_lists[0])
            
            # No lists exist, create a default one
            default_name = f"My Shopping List"
            list_id = f"list_{user_code}_{int(datetime.now().timestamp())}"
            
            # Create new shopping list
            new_list = ShoppingList(
                list_id=list_id,
                user_id=user_id,
                list_name=default_name,
                status='active',
                items=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Save to database
            success = self._save_shopping_list_to_db(new_list)
            
            if success:
                self.logger.info(f"Auto-created default shopping list for user {user_code}")
                return new_list
            else:
                self.logger.error(f"Failed to create default shopping list for user {user_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting or creating default list for user {user_code}: {str(e)}")
            return None
    
    def refresh_product_data(self, new_excel_data: Dict[str, Any]):
        """
        Refresh product data when Excel data is reloaded.
        
        Args:
            new_excel_data: New Excel data dictionary
        """
        try:
            # Since we now query the database directly, we don't need to maintain
            # a local cache of products. This method is kept for compatibility.
            self.logger.info("Shopping list service product data refresh - using database queries")
            
        except Exception as e:
            self.logger.error(f"Error refreshing product data: {str(e)}")
    
    def duplicate_shopping_list(self, shopping_list: ShoppingList, user: User, 
                              new_name: Optional[str] = None) -> Optional[ShoppingList]:
        """
        Create a duplicate of an existing shopping list.
        
        Args:
            shopping_list: ShoppingList to duplicate
            user: User instance
            new_name: Optional new name for the duplicate
            
        Returns:
            New ShoppingList instance or None if failed
        """
        try:
            duplicate_name = new_name or f"{shopping_list.list_name} (Copy)"
            
            # Create new shopping list
            new_list = ShoppingList.create_new_list(
                user_id=user.user_id,
                user_code=user.user_code,
                list_name=duplicate_name,
                description=shopping_list.description
            )
            
            # Copy all items
            for item in shopping_list.items:
                # Create new item with same data
                new_item = ShoppingItem.from_dict(item.to_dict())
                new_item.item_id = f"item_{len(new_list.items) + 1}"  # Generate new ID
                new_list.add_item(new_item)
            
            # Save to database
            success = self._save_shopping_list_to_db(new_list)
            
            if success:
                # Update user's active lists
                user.add_shopping_list(new_list.list_id)
                
                self.logger.info(f"Duplicated shopping list {shopping_list.list_id} as {new_list.list_id}")
                return new_list
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error duplicating shopping list {shopping_list.list_id}: {str(e)}")
            return None
    
    def get_or_create_default_list(self, user: User) -> Optional[ShoppingList]:
        """
        Get user's default shopping list or create one if none exists.
        
        Args:
            user: User instance
            
        Returns:
            ShoppingList instance or None if failed
        """
        try:
            # Get user's existing lists
            existing_lists = self.get_user_shopping_lists(user)
            
            if existing_lists:
                # Return the most recent list
                return existing_lists[0]
            
            # No lists exist, create a default one
            default_name = f"My Shopping List"
            shopping_list = self.create_shopping_list(
                user=user,
                list_name=default_name,
                description="Automatically created shopping list"
            )
            
            if shopping_list:
                self.logger.info(f"Auto-created default shopping list for user {user.user_code}")
            
            return shopping_list
            
        except Exception as e:
            self.logger.error(f"Error getting or creating default list for user {user.user_code}: {str(e)}")
            return None
    
    def _save_shopping_list_to_db(self, shopping_list: ShoppingList) -> bool:
        """Save shopping list to PostgreSQL database."""
        try:
            list_data = shopping_list.to_dict()
            
            # Convert items to JSON string for PostgreSQL
            import json
            items_json = json.dumps([item.to_dict() for item in shopping_list.items])
            
            return self.db.execute_update(
                """INSERT INTO shopping_lists (
                    list_id, user_id, name, status, items, total_price, 
                    created_at, updated_at
                ) VALUES (
                    :list_id, :user_id, :name, :status, :items, :total_price,
                    :created_at, :updated_at
                ) ON CONFLICT (list_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    items = EXCLUDED.items,
                    total_price = EXCLUDED.total_price,
                    updated_at = EXCLUDED.updated_at""",
                {
                    'list_id': shopping_list.list_id,
                    'user_id': shopping_list.user_id,
                    'name': shopping_list.list_name,
                    'status': shopping_list.status,
                    'items': items_json,
                    'total_price': shopping_list.total_price,
                    'created_at': shopping_list.created_at,
                    'updated_at': shopping_list.updated_at
                }
            )
        except Exception as e:
            self.logger.error(f"Error saving shopping list to database: {str(e)}")
            return False
    
    def _update_user_in_db(self, user: User) -> bool:
        """Update user in PostgreSQL database."""
        try:
            import json
            user_data = user.to_dict()
            
            # Convert preferences dict to JSON string for PostgreSQL
            preferences_json = json.dumps(user_data.get('preferences', {}))
            
            return self.db.execute_update(
                """UPDATE users SET 
                   preferences = :preferences,
                   updated_at = CURRENT_TIMESTAMP,
                   last_activity = CURRENT_TIMESTAMP
                   WHERE user_id = :user_id""",
                {
                    'user_id': user.user_id,
                    'preferences': preferences_json
                }
            )
        except Exception as e:
            self.logger.error(f"Error updating user in database: {str(e)}")
            return False