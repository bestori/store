"""
Product model representing cable tray products from Excel data.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ProductSpecifications:
    """Product technical specifications."""
    type: str
    height: Optional[int] = None
    width: Optional[int] = None  
    thickness: Optional[float] = None
    galvanization: Optional[str] = None
    material: Optional[str] = None
    length: Optional[int] = None
    weight: Optional[float] = None
    load_capacity: Optional[int] = None
    finish: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ProductDescriptions:
    """Product descriptions in multiple languages."""
    hebrew: str
    english: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass 
class ProductPricing:
    """Product pricing information."""
    price: float
    currency: str = "ILS"
    bulk_pricing: Optional[List[Dict[str, Any]]] = None
    price_type: str = "standard"
    minimum_quantity: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Product:
    """
    Product model representing cable tray products.
    
    This model represents products loaded from the Excel files (read-only).
    Products are cached in memory for fast search operations.
    """
    
    # Primary identifiers
    menora_id: str
    supplier_code: str
    
    # Product information
    descriptions: ProductDescriptions
    category: str
    subcategory: Optional[str] = None
    
    # Technical specifications
    specifications: Optional[ProductSpecifications] = None
    
    # Pricing information (from Excel price table)
    pricing: Optional[ProductPricing] = None
    
    # Search optimization
    search_terms: Optional[Dict[str, List[str]]] = None
    
    # Availability
    in_stock: bool = True
    lead_time: int = 7
    
    # Additional data
    tags: Optional[List[str]] = None
    supplier_name: str = "HOLDEE"
    
    # Image data
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    has_image: bool = False
    
    def __post_init__(self):
        """Initialize computed fields after creation."""
        if self.search_terms is None:
            self.search_terms = self._generate_search_terms()
    
    def _generate_search_terms(self) -> Dict[str, List[str]]:
        """Generate search terms from product data."""
        hebrew_terms = []
        english_terms = []
        
        # Add description words
        if self.descriptions:
            # For Hebrew: split by spaces but also store the full description for substring matching
            if self.descriptions.hebrew:
                hebrew_terms.append(self.descriptions.hebrew)  # Full description for substring search
                hebrew_terms.extend(self.descriptions.hebrew.split())
            
            # For English: normal word splitting
            if self.descriptions.english:
                english_terms.extend(self.descriptions.english.split())
        
        # Add specification terms
        if self.specifications:
            spec_dict = self.specifications.to_dict()
            for key, value in spec_dict.items():
                if value and isinstance(value, str):
                    english_terms.append(value.lower())
                elif value and isinstance(value, (int, float)):
                    english_terms.append(str(value))
        
        # Add category terms
        if self.category:
            english_terms.append(self.category.lower())
        
        # Add supplier terms
        english_terms.extend([self.supplier_code.lower(), self.supplier_name.lower()])
        
        # Remove duplicates and empty terms
        hebrew_terms = list(set(filter(None, hebrew_terms)))
        english_terms = list(set(filter(None, english_terms)))
        
        # Combined search string
        combined = f"{' '.join(english_terms)} {' '.join(hebrew_terms)}"
        
        return {
            'hebrew': hebrew_terms,
            'english': english_terms, 
            'combined': combined
        }
    
    def matches_search(self, query: str, language: Optional[str] = None) -> bool:
        """
        Check if product matches search query.
        
        Args:
            query: Search query string
            language: Preferred language (hebrew/english)
            
        Returns:
            True if product matches query
        """
        if not query or not self.search_terms:
            return False
        
        query = query.strip()
        query_lower = query.lower()
        
        # Check combined search first for broad matching
        if query_lower in self.search_terms['combined'].lower():
            return True
        
        # For Hebrew search, also check exact substring matches
        if language == 'hebrew':
            # Hebrew→English synonym bridging (works without reloading cached data)
            # Maps common Hebrew terms to English tokens present in search_terms
            hebrew_to_english_synonyms = {
                "כבל": ["cable", "tray"],
                "כבלים": ["cable", "tray"],
                "תעלת כבלים": ["cable tray", "tray"],
                "מגש": ["tray", "cable tray"],
                "מגש כבלים": ["cable tray", "tray"],
            }
            mapped_english_terms = hebrew_to_english_synonyms.get(query, [])
            if mapped_english_terms:
                english_tokens = [t.lower() for t in (self.search_terms.get('english') or [])]
                combined_lower = self.search_terms['combined'].lower()
                for eng_term in mapped_english_terms:
                    if eng_term in english_tokens or eng_term in combined_lower:
                        return True

            # Check Hebrew terms
            if self.search_terms['hebrew']:
                for term in self.search_terms['hebrew']:
                    if isinstance(term, str) and (query in term or query_lower in term.lower()):
                        return True
            # Also check Hebrew description directly
            if hasattr(self, 'descriptions') and self.descriptions and self.descriptions.hebrew:
                if query in self.descriptions.hebrew or query_lower in self.descriptions.hebrew.lower():
                    return True
        elif language == 'english':
            # Check English terms
            if self.search_terms['english']:
                for term in self.search_terms['english']:
                    if isinstance(term, str) and query_lower in term.lower():
                        return True
        else:
            # Check all terms if no language preference
            all_terms = self.search_terms.get('hebrew', []) + self.search_terms.get('english', [])
            for term in all_terms:
                if isinstance(term, str) and (query in term or query_lower in term.lower()):
                    return True
            
            # Also check descriptions directly
            if hasattr(self, 'descriptions') and self.descriptions:
                if (self.descriptions.hebrew and (query in self.descriptions.hebrew or query_lower in self.descriptions.hebrew.lower())) or \
                   (self.descriptions.english and query_lower in self.descriptions.english.lower()):
                    return True
        
        return False
    
    def matches_filters(self, filters: Dict[str, Any]) -> bool:
        """
        Check if product matches filter criteria.
        
        Args:
            filters: Dictionary of filter criteria
            
        Returns:
            True if product matches all filters
        """
        if not filters or not self.specifications:
            return not filters  # If no filters, match all
        
        spec_dict = self.specifications.to_dict()
        
        for filter_key, filter_value in filters.items():
            if filter_value is None or filter_value == '':
                continue
                
            # Map filter keys to specification keys
            spec_key = filter_key
            if filter_key == 'type':
                spec_key = 'type'
            
            spec_value = spec_dict.get(spec_key)
            
            if spec_value is None:
                return False
                
            # Handle different comparison types
            if isinstance(filter_value, str) and isinstance(spec_value, str):
                if spec_value.lower() != filter_value.lower():
                    return False
            elif isinstance(filter_value, str) and isinstance(spec_value, (int, float)):
                # Convert filter value to number for numeric fields
                try:
                    filter_num = float(filter_value)
                    if spec_value != filter_num:
                        return False
                except (ValueError, TypeError):
                    return False
            elif isinstance(filter_value, (int, float)):
                if spec_value != filter_value:
                    return False
            elif isinstance(filter_value, list):
                if spec_value not in filter_value:
                    return False
        
        return True
    
    def get_price(self, quantity: int = 1) -> Optional[float]:
        """
        Get price for specified quantity, considering bulk pricing.
        
        Args:
            quantity: Quantity to price
            
        Returns:
            Unit price for the quantity
        """
        if not self.pricing:
            return None
        
        base_price = self.pricing.price
        
        # Check for bulk pricing
        if self.pricing.bulk_pricing and quantity > 1:
            applicable_price = base_price
            
            for bulk_tier in sorted(self.pricing.bulk_pricing, key=lambda x: x['minQty']):
                if quantity >= bulk_tier['minQty']:
                    applicable_price = bulk_tier['price']
                else:
                    break
            
            return applicable_price
        
        return base_price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary format."""
        result = {
            'menora_id': self.menora_id,  # Fixed field name consistency
            'supplier_code': self.supplier_code,
            'descriptions': self.descriptions.to_dict() if self.descriptions else None,
            'category': self.category,
            'subcategory': self.subcategory,
            'specifications': self.specifications.to_dict() if self.specifications else None,
            'pricing': self.pricing.to_dict() if self.pricing else None,
            'search_terms': self.search_terms,
            'in_stock': self.in_stock,
            'lead_time': self.lead_time,
            'tags': self.tags,
            'supplier_name': self.supplier_name,
            'image_url': self.image_url,
            'image_path': self.image_path,
            'has_image': self.has_image
        }
        
        # Remove None and undefined values
        return {k: v for k, v in result.items() if v is not None and v != 'undefined'}
    
    @classmethod
    def from_excel_row(cls, row_data: Dict[str, Any]) -> 'Product':
        """
        Create Product instance from Excel row data.
        
        Args:
            row_data: Dictionary containing Excel row data
            
        Returns:
            Product instance
        """
        # Create descriptions
        descriptions = ProductDescriptions(
            hebrew=row_data.get('hebrew_description', ''),
            english=row_data.get('english_description', '')
        )
        
        # Create specifications
        specifications = ProductSpecifications(
            type=row_data.get('type', ''),
            height=row_data.get('height'),
            width=row_data.get('width'),
            thickness=row_data.get('thickness'),
            galvanization=row_data.get('galvanization'),
            material=row_data.get('material')  # Don't default to Steel
        )
        
        # Create pricing if available
        pricing = None
        if row_data.get('price'):
            pricing = ProductPricing(
                price=float(row_data['price']),
                currency=row_data.get('currency', 'ILS')
            )
        
        return cls(
            menora_id=row_data.get('menora_id', ''),
            supplier_code=row_data.get('supplier_code', ''),
            descriptions=descriptions,
            category=row_data.get('category', 'cable_tray'),
            subcategory=row_data.get('subcategory'),
            specifications=specifications,
            pricing=pricing,
            supplier_name=row_data.get('supplier_name', 'HOLDEE')
        )