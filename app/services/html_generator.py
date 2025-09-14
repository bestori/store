"""
HTML generator service for creating shopping list HTML outputs.

This service generates printable HTML shopping lists with proper formatting
for both Hebrew and English content.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from app.models.shopping_list import ShoppingList
from app.models.user import User
from app.services.price_calculator import PriceCalculator


class HtmlGenerator:
    """
    Service for generating HTML shopping lists.
    
    Creates formatted, printable HTML documents with bilingual support.
    """
    
    def __init__(self, price_calculator: PriceCalculator):
        """
        Initialize HTML generator.
        
        Args:
            price_calculator: Price calculator service
        """
        self.price_calculator = price_calculator
        self.logger = logging.getLogger(__name__)
    
    def generate_shopping_list_html(self, shopping_list: ShoppingList, user: User,
                                  language: str = 'hebrew', include_images: bool = False,
                                  format_type: str = 'print') -> str:
        """
        Generate HTML shopping list.
        
        Args:
            shopping_list: ShoppingList instance
            user: User instance
            language: Language preference (hebrew/english)
            include_images: Whether to include product images
            format_type: Format type (print/screen)
            
        Returns:
            HTML string
        """
        try:
            # Calculate totals
            totals = self.price_calculator.calculate_list_totals(shopping_list)
            
            # Generate HTML
            html_content = self._generate_html_template(
                shopping_list=shopping_list,
                user=user,
                language=language,
                totals=totals,
                include_images=include_images,
                format_type=format_type
            )
            
            # Mark as generated
            shopping_list.mark_html_generated()
            
            self.logger.info(f"Generated HTML for shopping list {shopping_list.list_id}")
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error generating HTML for list {shopping_list.list_id}: {str(e)}")
            return self._generate_error_html(str(e))
    
    def _generate_html_template(self, shopping_list: ShoppingList, user: User,
                              language: str, totals: Dict[str, Any],
                              include_images: bool, format_type: str) -> str:
        """Generate the main HTML template."""
        
        # Language-specific text
        texts = self._get_language_texts(language)
        
        # HTML direction for RTL/LTR
        direction = "rtl" if language == 'hebrew' else "ltr"
        text_align = "right" if language == 'hebrew' else "left"
        
        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html dir="{direction}" lang="{'he' if language == 'hebrew' else 'en'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{texts['shopping_list']} - {shopping_list.list_name}</title>
    <style>
        {self._get_css_styles(language, format_type)}
    </style>
</head>
<body>
    <div class="shopping-list-container">
        {self._generate_header(shopping_list, user, language, texts)}
        
        {self._generate_list_info(shopping_list, language, texts)}
        
        {self._generate_items_table(shopping_list, language, texts, include_images)}
        
        {self._generate_totals_section(totals, language, texts)}
        
        {self._generate_footer(language, texts)}
    </div>
    
    {self._get_javascript(format_type)}
</body>
</html>
        """
        
        return html
    
    def _generate_header(self, shopping_list: ShoppingList, user: User, 
                        language: str, texts: Dict[str, str]) -> str:
        """Generate HTML header section."""
        
        current_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        
        return f"""
        <header class="header">
            <div class="logo-section">
                <h1 class="company-name">{texts['company_name']}</h1>
                <p class="tagline">{texts['tagline']}</p>
            </div>
            
            <div class="document-info">
                <h2 class="document-title">{texts['shopping_list']}</h2>
                <div class="meta-info">
                    <div class="meta-row">
                        <span class="meta-label">{texts['list_name']}:</span>
                        <span class="meta-value">{shopping_list.list_name}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">{texts['user_code']}:</span>
                        <span class="meta-value">{user.user_code}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">{texts['date']}:</span>
                        <span class="meta-value">{current_date}</span>
                    </div>
                </div>
            </div>
        </header>
        """
    
    def _generate_list_info(self, shopping_list: ShoppingList, 
                           language: str, texts: Dict[str, str]) -> str:
        """Generate shopping list information section."""
        
        description_section = ""
        if shopping_list.description:
            description_section = f"""
            <div class="list-description">
                <strong>{texts['description']}:</strong> {shopping_list.description}
            </div>
            """
        
        return f"""
        <section class="list-info">
            {description_section}
            <div class="list-stats">
                <span class="stat-item">{texts['total_items']}: <strong>{shopping_list.get_item_count()}</strong></span>
                <span class="stat-item">{texts['total_quantity']}: <strong>{shopping_list.get_total_quantity()}</strong></span>
                <span class="stat-item">{texts['created']}: <strong>{shopping_list.created_at.strftime("%d/%m/%Y") if shopping_list.created_at else 'N/A'}</strong></span>
            </div>
        </section>
        """
    
    def _generate_items_table(self, shopping_list: ShoppingList, language: str,
                             texts: Dict[str, str], include_images: bool) -> str:
        """Generate items table."""
        
        if not shopping_list.items:
            return f"""
            <div class="empty-list">
                <p>{texts['no_items']}</p>
            </div>
            """
        
        # Table header
        image_header = f"<th class='image-col'>{texts['image']}</th>" if include_images else ""
        
        table_header = f"""
        <thead>
            <tr>
                <th class="item-no">#</th>
                {image_header}
                <th class="menora-id">{texts['menora_id']}</th>
                <th class="description">{texts['description']}</th>
                <th class="supplier-code">{texts['supplier_code']}</th>
                <th class="quantity">{texts['quantity']}</th>
                <th class="unit-price">{texts['unit_price']}</th>
                <th class="total-price">{texts['total_price']}</th>
                <th class="notes">{texts['notes']}</th>
            </tr>
        </thead>
        """
        
        # Table rows
        table_rows = ""
        for i, item in enumerate(shopping_list.items, 1):
            image_cell = f"<td class='image-cell'>-</td>" if include_images else ""
            
            # Get description in preferred language
            description = item.get_description(language)
            
            # Format prices
            unit_price_formatted = self.price_calculator.format_price(item.unit_price)
            total_price_formatted = self.price_calculator.format_price(item.total_price)
            
            notes = item.notes or "-"
            
            table_rows += f"""
            <tr class="item-row">
                <td class="item-no">{i}</td>
                {image_cell}
                <td class="menora-id">{item.menora_id}</td>
                <td class="description">{description}</td>
                <td class="supplier-code">{item.supplier_code}</td>
                <td class="quantity">{item.quantity}</td>
                <td class="unit-price">{unit_price_formatted}</td>
                <td class="total-price">{total_price_formatted}</td>
                <td class="notes">{notes}</td>
            </tr>
            """
        
        return f"""
        <section class="items-section">
            <h3 class="section-title">{texts['items_list']}</h3>
            <table class="items-table">
                {table_header}
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </section>
        """
    
    def _generate_totals_section(self, totals: Dict[str, Any], 
                               language: str, texts: Dict[str, str]) -> str:
        """Generate totals section."""
        
        subtotal_formatted = self.price_calculator.format_price(totals['subtotal'])
        tax_formatted = self.price_calculator.format_price(totals['tax_amount'])
        total_formatted = self.price_calculator.format_price(totals['total'])
        
        tax_row = ""
        if totals['tax_amount'] > 0:
            tax_row = f"""
            <div class="total-row">
                <span class="total-label">{texts['tax']} ({totals['tax_rate']:.1%}):</span>
                <span class="total-value">{tax_formatted}</span>
            </div>
            """
        
        return f"""
        <section class="totals-section">
            <h3 class="section-title">{texts['summary']}</h3>
            <div class="totals-container">
                <div class="total-row">
                    <span class="total-label">{texts['subtotal']}:</span>
                    <span class="total-value">{subtotal_formatted}</span>
                </div>
                {tax_row}
                <div class="total-row final-total">
                    <span class="total-label">{texts['final_total']}:</span>
                    <span class="total-value">{total_formatted}</span>
                </div>
            </div>
        </section>
        """
    
    def _generate_footer(self, language: str, texts: Dict[str, str]) -> str:
        """Generate footer section."""
        
        generation_time = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        
        return f"""
        <footer class="footer">
            <div class="generation-info">
                <p>{texts['generated_on']}: {generation_time}</p>
                <p>{texts['generated_by']}</p>
            </div>
        </footer>
        """
    
    def _get_language_texts(self, language: str) -> Dict[str, str]:
        """Get language-specific text strings."""
        
        if language == 'hebrew':
            return {
                'company_name': 'חנות',
                'tagline': 'פתרונות תשתית חשמל',
                'shopping_list': 'רשימת קניות',
                'list_name': 'שם הרשימה',
                'user_code': 'קוד לקוח',
                'date': 'תאריך',
                'description': 'תיאור',
                'total_items': 'סה"כ פריטים',
                'total_quantity': 'סה"כ כמות',
                'created': 'נוצר בתאריך',
                'no_items': 'אין פריטים ברשימה',
                'image': 'תמונה',
                'menora_id': 'קוד מנורה',
                'description': 'תיאור',
                'supplier_code': 'קוד ספק',
                'quantity': 'כמות',
                'unit_price': 'מחיר יחידה',
                'total_price': 'מחיר כולל',
                'notes': 'הערות',
                'items_list': 'רשימת פריטים',
                'summary': 'סיכום',
                'subtotal': 'סה"כ',
                'tax': 'מע"מ',
                'final_total': 'סה"כ לתשלום',
                'generated_on': 'נוצר בתאריך',
                'generated_by': '🤖 נוצר עם Claude Code'
            }
        else:
            return {
                'company_name': 'Store',
                'tagline': 'Electrical Infrastructure Solutions',
                'shopping_list': 'Shopping List',
                'list_name': 'List Name',
                'user_code': 'Customer Code',
                'date': 'Date',
                'description': 'Description',
                'total_items': 'Total Items',
                'total_quantity': 'Total Quantity',
                'created': 'Created',
                'no_items': 'No items in list',
                'image': 'Image',
                'menora_id': 'Menora ID',
                'description': 'Description',
                'supplier_code': 'Supplier Code',
                'quantity': 'Quantity',
                'unit_price': 'Unit Price',
                'total_price': 'Total Price',
                'notes': 'Notes',
                'items_list': 'Items List',
                'summary': 'Summary',
                'subtotal': 'Subtotal',
                'tax': 'VAT',
                'final_total': 'Total Amount',
                'generated_on': 'Generated on',
                'generated_by': '🤖 Generated with Claude Code'
            }
    
    def _get_css_styles(self, language: str, format_type: str) -> str:
        """Get CSS styles for the HTML document."""
        
        direction = "rtl" if language == 'hebrew' else "ltr"
        text_align = "right" if language == 'hebrew' else "left"
        
        return f"""
        /* Reset and base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Arial', 'Helvetica', 'David', sans-serif;
            direction: {direction};
            text-align: {text_align};
            line-height: 1.6;
            color: #333;
            background: white;
        }}
        
        .shopping-list-container {{
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
            background: white;
        }}
        
        /* Header styles */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .logo-section h1 {{
            color: #007bff;
            font-size: 28px;
            margin-bottom: 5px;
        }}
        
        .tagline {{
            color: #666;
            font-size: 14px;
        }}
        
        .document-info {{
            text-align: {'left' if language == 'hebrew' else 'right'};
        }}
        
        .document-title {{
            font-size: 24px;
            color: #007bff;
            margin-bottom: 10px;
        }}
        
        .meta-row {{
            margin-bottom: 5px;
            font-size: 14px;
        }}
        
        .meta-label {{
            font-weight: bold;
            margin-right: 10px;
        }}
        
        /* List info styles */
        .list-info {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 25px;
        }}
        
        .list-description {{
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .list-stats {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .stat-item {{
            font-size: 14px;
        }}
        
        /* Table styles */
        .section-title {{
            font-size: 20px;
            color: #007bff;
            margin-bottom: 15px;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 5px;
        }}
        
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
            font-size: 12px;
        }}
        
        .items-table th,
        .items-table td {{
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: center;
        }}
        
        .items-table th {{
            background: #007bff;
            color: white;
            font-weight: bold;
        }}
        
        .items-table .description {{
            text-align: {text_align};
            max-width: 200px;
        }}
        
        .items-table .notes {{
            text-align: {text_align};
            max-width: 150px;
            font-size: 11px;
        }}
        
        .item-row:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        /* Totals section */
        .totals-section {{
            margin-top: 30px;
        }}
        
        .totals-container {{
            background: #f8f9fa;
            border: 2px solid #007bff;
            border-radius: 5px;
            padding: 20px;
            max-width: 300px;
            margin-left: auto;
        }}
        
        .total-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        
        .final-total {{
            border-top: 1px solid #007bff;
            padding-top: 10px;
            font-weight: bold;
            font-size: 16px;
            color: #007bff;
        }}
        
        /* Footer styles */
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
        
        .generation-info p {{
            margin-bottom: 5px;
        }}
        
        /* Empty list */
        .empty-list {{
            text-align: center;
            padding: 40px;
            color: #666;
            font-style: italic;
        }}
        
        /* Print styles */
        @media print {{
            .shopping-list-container {{
                padding: 0;
                max-width: none;
            }}
            
            @page {{
                margin: 20mm;
                size: A4;
            }}
            
            .header {{
                break-inside: avoid;
            }}
            
            .items-table {{
                font-size: 10px;
            }}
            
            .item-row {{
                break-inside: avoid;
            }}
        }}
        
        /* Screen-specific styles */
        @media screen {{
            body {{
                background: #f5f5f5;
                padding: 20px;
            }}
            
            .shopping-list-container {{
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                border-radius: 5px;
            }}
        }}
        """
    
    def _get_javascript(self, format_type: str) -> str:
        """Get JavaScript for the HTML document."""
        
        if format_type == 'print':
            return """
            <script>
                // Auto-print functionality
                window.onload = function() {
                    if (window.location.search.includes('autoprint=true')) {
                        window.print();
                    }
                };
            </script>
            """
        
        return ""
    
    def _generate_error_html(self, error_message: str) -> str:
        """Generate error HTML when generation fails."""
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Shopping List</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .error {{ color: red; padding: 20px; border: 1px solid red; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h2>Error Generating Shopping List</h2>
                <p>An error occurred while generating the shopping list HTML:</p>
                <p><strong>{error_message}</strong></p>
            </div>
        </body>
        </html>
        """