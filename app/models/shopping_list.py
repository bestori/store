"""
Shopping list model for managing user shopping lists.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
from .shopping_item import ShoppingItem


@dataclass
class ShoppingListSummary:
    """Shopping list summary with totals."""
    total_items: int = 0
    total_quantity: int = 0
    total_price: float = 0.0
    currency: str = "ILS"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'totalItems': self.total_items,
            'totalQuantity': self.total_quantity,
            'totalPrice': self.total_price,
            'currency': self.currency
        }


@dataclass
class ShoppingList:
    """
    Shopping list model for managing user's product selections.
    
    Stores user-specific shopping lists with items, quantities, and calculations.
    """
    
    # List identification
    list_id: str
    user_id: str
    user_code: str
    
    # List information
    list_name: str
    description: Optional[str] = None
    
    # Shopping items
    items: List[ShoppingItem] = None
    
    # List totals (computed)
    summary: Optional[ShoppingListSummary] = None
    
    # List status
    status: str = "active"  # active, completed, archived
    
    # HTML output tracking
    html_generated: bool = False
    last_html_generation: Optional[datetime] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.items is None:
            self.items = []
        
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate summary
        self.recalculate_summary()
    
    def recalculate_summary(self):
        """Recalculate list summary from items."""
        total_items = len(self.items)
        total_quantity = sum(item.quantity for item in self.items)
        total_price = sum(item.total_price for item in self.items)
        
        self.summary = ShoppingListSummary(
            total_items=total_items,
            total_quantity=total_quantity,
            total_price=round(total_price, 2),
            currency="ILS"
        )
        
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1
    
    def add_item(self, item: ShoppingItem) -> bool:
        """
        Add item to shopping list.
        
        Args:
            item: ShoppingItem to add
            
        Returns:
            True if item was added, False if already exists
        """
        # Check if item already exists (by menora_id)
        existing_item = self.find_item_by_menora_id(item.menora_id)
        
        if existing_item:
            # Update quantity instead of adding duplicate
            new_quantity = existing_item.quantity + item.quantity
            existing_item.update_quantity(new_quantity)
            if item.notes and not existing_item.notes:
                existing_item.update_notes(item.notes)
        else:
            # Add new item
            self.items.append(item)
        
        self.recalculate_summary()
        self.html_generated = False  # Mark HTML as stale
        
        return existing_item is None
    
    def remove_item(self, item_id: str) -> bool:
        """
        Remove item from shopping list.
        
        Args:
            item_id: ID of item to remove
            
        Returns:
            True if item was removed, False if not found
        """
        for i, item in enumerate(self.items):
            if item.item_id == item_id:
                del self.items[i]
                self.recalculate_summary()
                self.html_generated = False
                return True
        
        return False
    
    def update_item_quantity(self, item_id: str, new_quantity: int) -> bool:
        """
        Update quantity of an item.
        
        Args:
            item_id: ID of item to update
            new_quantity: New quantity value
            
        Returns:
            True if item was updated, False if not found
        """
        item = self.find_item_by_id(item_id)
        if item:
            if new_quantity <= 0:
                return self.remove_item(item_id)
            else:
                item.update_quantity(new_quantity)
                self.recalculate_summary()
                self.html_generated = False
                return True
        
        return False
    
    def update_item_notes(self, item_id: str, notes: Optional[str]) -> bool:
        """
        Update notes of an item.
        
        Args:
            item_id: ID of item to update
            notes: New notes text
            
        Returns:
            True if item was updated, False if not found
        """
        item = self.find_item_by_id(item_id)
        if item:
            item.update_notes(notes)
            self.updated_at = datetime.now(timezone.utc)
            self.html_generated = False
            return True
        
        return False
    
    def find_item_by_id(self, item_id: str) -> Optional[ShoppingItem]:
        """Find item by ID."""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None
    
    def find_item_by_menora_id(self, menora_id: str) -> Optional[ShoppingItem]:
        """Find item by Menora ID."""
        for item in self.items:
            if item.menora_id == menora_id:
                return item
        return None
    
    def clear_items(self):
        """Clear all items from the list."""
        self.items = []
        self.recalculate_summary()
        self.html_generated = False
    
    def get_item_count(self) -> int:
        """Get total number of items."""
        return len(self.items)
    
    def get_total_quantity(self) -> int:
        """Get total quantity of all items."""
        return self.summary.total_quantity if self.summary else 0
    
    def get_total_price(self) -> float:
        """Get total price of all items."""
        return self.summary.total_price if self.summary else 0.0
    
    def get_total_value(self) -> float:
        """Get total value of all items (alias for get_total_price)."""
        return self.get_total_price()
    
    def is_empty(self) -> bool:
        """Check if list is empty."""
        return len(self.items) == 0
    
    def mark_html_generated(self):
        """Mark HTML as generated."""
        self.html_generated = True
        self.last_html_generation = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert shopping list to dictionary format."""
        return {
            'listId': self.list_id,
            'userId': self.user_id,
            'userCode': self.user_code,
            'listName': self.list_name,
            'description': self.description,
            'items': [item.to_dict() for item in self.items],
            'summary': self.summary.to_dict() if self.summary else None,
            'status': self.status,
            'htmlGenerated': self.html_generated,
            'lastHtmlGeneration': self.last_html_generation.isoformat() if self.last_html_generation else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary format for list views."""
        return {
            'listId': self.list_id,
            'listName': self.list_name,
            'description': self.description,
            'itemCount': self.get_item_count(),
            'totalPrice': self.get_total_price(),
            'currency': 'ILS',
            'status': self.status,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShoppingList':
        """
        Create ShoppingList instance from dictionary data.
        
        Args:
            data: Dictionary containing list data
            
        Returns:
            ShoppingList instance
        """
        # Parse datetime fields
        created_at = None
        if data.get('createdAt'):
            created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        
        updated_at = None
        if data.get('updatedAt'):
            updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))
        
        last_html_generation = None
        if data.get('lastHtmlGeneration'):
            last_html_generation = datetime.fromisoformat(data['lastHtmlGeneration'].replace('Z', '+00:00'))
        
        # Parse items
        items = []
        if data.get('items'):
            items = [ShoppingItem.from_dict(item_data) for item_data in data['items']]
        
        # Parse summary
        summary = None
        if data.get('summary'):
            summary_data = data['summary']
            summary = ShoppingListSummary(
                total_items=summary_data.get('totalItems', 0),
                total_quantity=summary_data.get('totalQuantity', 0),
                total_price=summary_data.get('totalPrice', 0.0),
                currency=summary_data.get('currency', 'ILS')
            )
        
        return cls(
            list_id=data.get('listId', ''),
            user_id=data.get('userId', ''),
            user_code=data.get('userCode', ''),
            list_name=data.get('listName', ''),
            description=data.get('description'),
            items=items,
            summary=summary,
            status=data.get('status', 'active'),
            html_generated=data.get('htmlGenerated', False),
            last_html_generation=last_html_generation,
            created_at=created_at,
            updated_at=updated_at,
            version=data.get('version', 1)
        )
    
    @classmethod
    def create_new_list(cls, user_id: str, user_code: str, 
                       list_name: str, description: Optional[str] = None) -> 'ShoppingList':
        """
        Create a new empty shopping list.
        
        Args:
            user_id: User ID
            user_code: User code
            list_name: Name of the list
            description: Optional description
            
        Returns:
            New ShoppingList instance
        """
        list_id = str(uuid.uuid4())
        
        return cls(
            list_id=list_id,
            user_id=user_id,
            user_code=user_code,
            list_name=list_name,
            description=description
        )