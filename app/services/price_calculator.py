"""
Price calculator service for computing prices with bulk discounts and taxes.
"""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP

from app.models.product import Product
from app.models.shopping_list import ShoppingList


class PriceCalculator:
    """
    Service for calculating prices, taxes, and totals.
    
    Handles bulk pricing, tax calculations, and currency formatting.
    """
    
    def __init__(self, default_currency: str = "ILS", tax_rate: float = 0.17):
        """
        Initialize price calculator.
        
        Args:
            default_currency: Default currency code
            tax_rate: Tax rate (Israeli VAT is 17%)
        """
        self.default_currency = default_currency
        self.tax_rate = tax_rate
        self.logger = logging.getLogger(__name__)
    
    def calculate_item_price(self, product: Product, quantity: int) -> Dict[str, Any]:
        """
        Calculate price for a product with specific quantity.
        
        Args:
            product: Product instance
            quantity: Quantity to calculate for
            
        Returns:
            Dictionary with price calculations
        """
        try:
            if not product or not product.pricing:
                return {
                    'unit_price': 0.0,
                    'total_price': 0.0,
                    'currency': self.default_currency,
                    'bulk_discount_applied': False,
                    'error': 'Product or pricing not available'
                }
            
            base_price = product.pricing.price
            currency = product.pricing.currency or self.default_currency
            
            # Check for bulk pricing
            unit_price = base_price
            bulk_discount_applied = False
            
            if product.pricing.bulk_pricing and quantity > 1:
                # Find applicable bulk price
                applicable_bulk = None
                for bulk_tier in sorted(product.pricing.bulk_pricing, key=lambda x: x['minQty'], reverse=True):
                    if quantity >= bulk_tier['minQty']:
                        applicable_bulk = bulk_tier
                        break
                
                if applicable_bulk:
                    unit_price = applicable_bulk['price']
                    bulk_discount_applied = True
            
            total_price = self._round_currency(unit_price * quantity)
            
            return {
                'unit_price': self._round_currency(unit_price),
                'total_price': total_price,
                'currency': currency,
                'bulk_discount_applied': bulk_discount_applied,
                'base_price': self._round_currency(base_price),
                'savings': self._round_currency((base_price - unit_price) * quantity) if bulk_discount_applied else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating item price: {str(e)}")
            return {
                'unit_price': 0.0,
                'total_price': 0.0,
                'currency': self.default_currency,
                'bulk_discount_applied': False,
                'error': str(e)
            }
    
    def calculate_list_totals(self, shopping_list: ShoppingList, 
                            include_tax: bool = True) -> Dict[str, Any]:
        """
        Calculate totals for entire shopping list.
        
        Args:
            shopping_list: ShoppingList instance
            include_tax: Whether to include tax calculations
            
        Returns:
            Dictionary with comprehensive totals
        """
        try:
            if not shopping_list.items:
                return self._empty_totals()
            
            subtotal = 0.0
            total_savings = 0.0
            items_with_bulk_discount = 0
            currency = self.default_currency
            
            # Calculate subtotal and savings
            for item in shopping_list.items:
                subtotal += item.total_price
                
                # Update currency from first item (assume all same currency)
                if not currency and hasattr(item, 'currency'):
                    currency = getattr(item, 'currency', self.default_currency)
            
            subtotal = self._round_currency(subtotal)
            
            # Calculate tax
            tax_amount = 0.0
            if include_tax:
                tax_amount = self._round_currency(subtotal * self.tax_rate)
            
            # Calculate final total
            total = self._round_currency(subtotal + tax_amount)
            
            return {
                'subtotal': subtotal,
                'tax_rate': self.tax_rate if include_tax else 0.0,
                'tax_amount': tax_amount,
                'total': total,
                'currency': currency,
                'total_items': len(shopping_list.items),
                'total_quantity': sum(item.quantity for item in shopping_list.items),
                'total_savings': total_savings,
                'items_with_bulk_discount': items_with_bulk_discount,
                'breakdown': self._get_price_breakdown(shopping_list)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating list totals: {str(e)}")
            return self._empty_totals()
    
    def calculate_bulk_pricing_table(self, product: Product, 
                                   quantities: List[int] = None) -> List[Dict[str, Any]]:
        """
        Generate bulk pricing table for a product.
        
        Args:
            product: Product instance
            quantities: List of quantities to calculate for
            
        Returns:
            List of pricing tiers
        """
        try:
            if not product or not product.pricing:
                return []
            
            if not quantities:
                quantities = [1, 10, 25, 50, 100]
            
            pricing_table = []
            
            for qty in quantities:
                price_info = self.calculate_item_price(product, qty)
                
                pricing_table.append({
                    'quantity': qty,
                    'unit_price': price_info['unit_price'],
                    'total_price': price_info['total_price'],
                    'bulk_discount_applied': price_info['bulk_discount_applied'],
                    'savings_per_unit': price_info.get('savings', 0.0) / qty if qty > 0 else 0.0,
                    'currency': price_info['currency']
                })
            
            return pricing_table
            
        except Exception as e:
            self.logger.error(f"Error generating bulk pricing table: {str(e)}")
            return []
    
    def format_price(self, amount: float, currency: str = None, 
                    include_currency: bool = True) -> str:
        """
        Format price for display.
        
        Args:
            amount: Price amount
            currency: Currency code
            include_currency: Whether to include currency symbol
            
        Returns:
            Formatted price string
        """
        try:
            currency = currency or self.default_currency
            formatted_amount = self._round_currency(amount)
            
            if currency == "ILS":
                symbol = "₪" if include_currency else ""
                return f"{formatted_amount:,.2f} {symbol}".strip()
            elif currency == "USD":
                symbol = "$" if include_currency else ""
                return f"{symbol}{formatted_amount:,.2f}"
            elif currency == "EUR":
                symbol = "€" if include_currency else ""
                return f"{formatted_amount:,.2f} {symbol}".strip()
            else:
                symbol = currency if include_currency else ""
                return f"{formatted_amount:,.2f} {symbol}".strip()
                
        except Exception as e:
            self.logger.error(f"Error formatting price: {str(e)}")
            return "0.00"
    
    def _round_currency(self, amount: float) -> float:
        """Round amount to currency precision (2 decimal places)."""
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def _empty_totals(self) -> Dict[str, Any]:
        """Return empty totals dictionary."""
        return {
            'subtotal': 0.0,
            'tax_rate': 0.0,
            'tax_amount': 0.0,
            'total': 0.0,
            'currency': self.default_currency,
            'total_items': 0,
            'total_quantity': 0,
            'total_savings': 0.0,
            'items_with_bulk_discount': 0,
            'breakdown': []
        }
    
    def _get_price_breakdown(self, shopping_list: ShoppingList) -> List[Dict[str, Any]]:
        """Get detailed price breakdown by item."""
        breakdown = []
        
        for item in shopping_list.items:
            breakdown.append({
                'item_id': item.item_id,
                'menora_id': item.menora_id,
                'description': item.get_description(),
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            })
        
        return breakdown