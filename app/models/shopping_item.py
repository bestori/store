"""
Shopping item model representing individual items in a shopping list.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class ShoppingItem:
    """
    Individual item in a shopping list.
    
    Contains product information cached from Excel data and user-specific
    quantity and notes.
    """
    
    # Unique item identifier
    item_id: str
    
    # Product identifiers (from Excel data)
    menora_id: str
    supplier_code: str
    
    # Product details (cached from Excel for fast display)
    descriptions: Dict[str, str]  # {'hebrew': '...', 'english': '...'}
    
    # Order details
    quantity: int
    unit_price: float
    total_price: float
    
    # Additional information
    notes: Optional[str] = None
    
    # Metadata
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.added_at is None:
            self.added_at = datetime.now(timezone.utc)
        
        self.updated_at = datetime.now(timezone.utc)
        
        # Recalculate total price
        self.recalculate_total()
    
    def recalculate_total(self):
        """Recalculate total price based on quantity and unit price."""
        self.total_price = round(self.quantity * self.unit_price, 2)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_quantity(self, new_quantity: int):
        """
        Update item quantity and recalculate total.
        
        Args:
            new_quantity: New quantity value
        """
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative")
        
        self.quantity = new_quantity
        self.recalculate_total()
    
    def update_unit_price(self, new_price: float):
        """
        Update unit price and recalculate total.
        
        Args:
            new_price: New unit price
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        
        self.unit_price = new_price
        self.recalculate_total()
    
    def update_notes(self, notes: Optional[str]):
        """
        Update item notes.
        
        Args:
            notes: New notes text
        """
        self.notes = notes
        self.updated_at = datetime.now(timezone.utc)
    
    def get_hebrew_description(self) -> str:
        """Get Hebrew description."""
        return self.descriptions.get('hebrew', '')
    
    def get_english_description(self) -> str:
        """Get English description."""
        return self.descriptions.get('english', '')
    
    def get_description(self, language: str = 'hebrew') -> str:
        """
        Get description in specified language.
        
        Args:
            language: Language preference ('hebrew' or 'english')
            
        Returns:
            Description in requested language
        """
        if language == 'hebrew':
            return self.get_hebrew_description()
        elif language == 'english':
            return self.get_english_description()
        else:
            # Default to Hebrew
            return self.get_hebrew_description()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert shopping item to dictionary format."""
        return {
            'itemId': self.item_id,
            'menoraId': self.menora_id,
            'supplierCode': self.supplier_code,
            'descriptions': self.descriptions,
            'quantity': self.quantity,
            'unitPrice': self.unit_price,
            'totalPrice': self.total_price,
            'notes': self.notes,
            'addedAt': self.added_at.isoformat() if self.added_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_html_row(self, language: str = 'hebrew', show_supplier: bool = True) -> str:
        """
        Convert item to HTML table row for shopping list display.
        
        Args:
            language: Language preference for descriptions
            show_supplier: Whether to show supplier code
            
        Returns:
            HTML table row string
        """
        description = self.get_description(language)
        
        row = f"""
        <tr class="shopping-item">
            <td class="menora-id">{self.menora_id}</td>
            <td class="description">{description}</td>
        """
        
        if show_supplier:
            row += f'<td class="supplier-code">{self.supplier_code}</td>'
        
        row += f"""
            <td class="quantity">{self.quantity}</td>
            <td class="unit-price">{self.unit_price:.2f}</td>
            <td class="total-price">{self.total_price:.2f}</td>
        """
        
        if self.notes:
            row += f'<td class="notes">{self.notes}</td>'
        else:
            row += '<td class="notes">-</td>'
        
        row += "</tr>"
        
        return row
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShoppingItem':
        """
        Create ShoppingItem instance from dictionary data.
        
        Args:
            data: Dictionary containing item data
            
        Returns:
            ShoppingItem instance
        """
        # Parse datetime fields
        added_at = None
        if data.get('addedAt'):
            added_at = datetime.fromisoformat(data['addedAt'].replace('Z', '+00:00'))
        
        updated_at = None
        if data.get('updatedAt'):
            updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))
        
        return cls(
            item_id=data.get('itemId', ''),
            menora_id=data.get('menoraId', ''),
            supplier_code=data.get('supplierCode', ''),
            descriptions=data.get('descriptions', {}),
            quantity=data.get('quantity', 1),
            unit_price=data.get('unitPrice', 0.0),
            total_price=data.get('totalPrice', 0.0),
            notes=data.get('notes'),
            added_at=added_at,
            updated_at=updated_at
        )
    
    @classmethod
    def from_product(cls, product_data: Dict[str, Any], quantity: int = 1, 
                     notes: Optional[str] = None) -> 'ShoppingItem':
        """
        Create ShoppingItem from product data.
        
        Args:
            product_data: Product dictionary from Excel data or search results
            quantity: Item quantity
            notes: Optional notes
            
        Returns:
            ShoppingItem instance
        """
        import uuid
        
        # Generate unique item ID
        item_id = str(uuid.uuid4())
        
        # Extract product information
        menora_id = product_data.get('menoraId', '')
        supplier_code = product_data.get('supplierCode', '')
        descriptions = product_data.get('descriptions', {})
        
        # Get price information
        unit_price = 0.0
        if product_data.get('pricing'):
            unit_price = product_data['pricing'].get('price', 0.0)
        elif product_data.get('price'):
            unit_price = float(product_data['price'])
        
        return cls(
            item_id=item_id,
            menora_id=menora_id,
            supplier_code=supplier_code,
            descriptions=descriptions,
            quantity=quantity,
            unit_price=unit_price,
            total_price=quantity * unit_price,
            notes=notes
        )