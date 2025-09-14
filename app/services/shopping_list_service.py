"""
Shopping list service for managing user shopping lists and items.

This service handles creation, modification, and management of shopping lists
and their items, including price calculations and HTML generation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.models.user import User
from app.models.shopping_list import ShoppingList
from app.models.shopping_item import ShoppingItem
from app.models.product import Product
from app.services.firebase_service import FirebaseService


class ShoppingListService:
    """
    Service for shopping list management.
    
    Handles shopping list CRUD operations, item management,
    and price calculations.
    """
    
    def __init__(self, firebase_service: FirebaseService, excel_data: Dict[str, Any]):
        """
        Initialize shopping list service.
        
        Args:
            firebase_service: Firebase service instance
            excel_data: Excel data with products for price lookup
        """
        self.firebase = firebase_service
        self.excel_data = excel_data
        self.products: List[Product] = excel_data.get('products', [])
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
            shopping_lists = self.firebase.get_shopping_lists_by_user(user.user_id)
            
            # Sort by updated date (most recent first)
            shopping_lists.sort(key=lambda x: x.updated_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            
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
            shopping_list = self.firebase.get_shopping_list(list_id)
            
            if shopping_list and shopping_list.user_id == user.user_id:
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
            
            # Save to Firebase
            success = self.firebase.save_shopping_list(shopping_list)
            
            if success:
                # Update user's active lists
                user.add_shopping_list(shopping_list.list_id, set_as_default=len(user.active_lists) == 0)
                self.firebase.update_user(user)
                
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
            
            success = self.firebase.save_shopping_list(shopping_list)
            
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
            # Delete from Firebase
            success = self.firebase.delete_shopping_list(shopping_list.list_id)
            
            if success:
                # Update user's active lists
                user.remove_shopping_list(shopping_list.list_id)
                self.firebase.update_user(user)
                
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
            
            # Save to Firebase
            success = self.firebase.save_shopping_list(shopping_list)
            
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
                success = self.firebase.save_shopping_list(shopping_list)
                
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
                success = self.firebase.save_shopping_list(shopping_list)
                
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
        Find product by Menora ID in Excel data.
        
        Args:
            menora_id: Menora catalog number
            
        Returns:
            Product instance or None if not found
        """
        for product in self.products:
            if product.menora_id == menora_id:
                return product
        
        return None
    
    def get_list_statistics(self) -> Dict[str, Any]:
        """
        Get shopping list service statistics.
        
        Returns:
            Dictionary of statistics
        """
        try:
            stats = self.firebase.get_shopping_list_statistics()
            
            stats.update({
                'available_products': len(self.products),
                'products_with_pricing': sum(1 for p in self.products if p.pricing is not None)
            })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting list statistics: {str(e)}")
            return {}
    
    def refresh_product_data(self, new_excel_data: Dict[str, Any]):
        """
        Refresh product data when Excel data is reloaded.
        
        Args:
            new_excel_data: New Excel data dictionary
        """
        try:
            old_count = len(self.products)
            
            self.excel_data = new_excel_data
            self.products = new_excel_data.get('products', [])
            
            new_count = len(self.products)
            
            self.logger.info(f"Shopping list service product data refreshed: {old_count} -> {new_count} products")
            
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
            
            # Save to Firebase
            success = self.firebase.save_shopping_list(new_list)
            
            if success:
                # Update user's active lists
                user.add_shopping_list(new_list.list_id)
                self.firebase.update_user(user)
                
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