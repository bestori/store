"""
Excel data loader service for reading cable tray product data.

This service loads data from Excel files in read-only mode and caches
the data in memory for fast search operations.
"""

import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import time
from datetime import datetime, timezone
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage

from app.models.product import Product, ProductDescriptions, ProductSpecifications, ProductPricing


class ExcelLoader:
    """
    Service for loading and caching data from Excel files.
    
    Handles the two Excel files:
    1. Shopping list file - Master product database
    2. Price table file - Pricing information
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Excel loader with configuration.
        
        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # File paths
        self.data_dir = Path(config['EXCEL_DATA_DIR'])
        self.shopping_list_file = self.data_dir / config['SHOPPING_LIST_FILE']
        self.price_table_file = self.data_dir / config['PRICE_TABLE_FILE']
        
        # Cache
        self._products_cache: List[Product] = []
        self._prices_cache: Dict[str, float] = {}
        self._filter_options_cache: Dict[str, List[Any]] = {}
        self._all_images: Dict[str, str] = {}
        self._last_load_time: Optional[datetime] = None
        
        # Load status
        self._is_loaded = False
        
        # Background image extraction
        self._images_loaded = False
        self._image_extraction_thread = None
    
    def load_data(self) -> Dict[str, Any]:
        """
        Load data from Excel files.
        
        Returns:
            Dictionary containing loaded products and metadata
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting Excel data load...")
            
            # Skip image extraction for now - do in background
            self._all_images = {}  # Start with empty image map
            
            # Start background image extraction
            self._start_background_image_extraction()
            
            # Load base product types from shopping list file  
            base_products = self._load_shopping_list_data()
            
            # Clear products cache and start fresh
            self._products_cache = []

            # Include base products for comprehensive search coverage
            # This ensures items present in the lookup (e.g., covers "מכסה")
            # are searchable even if no priced variants exist
            self._products_cache.extend(base_products)
            
            # Load pricing data and create specific product variants
            self._load_pricing_data(base_products)
            
            # Generate filter options from final products
            self._generate_filter_options()
            
            # Update load status
            self._last_load_time = datetime.now(timezone.utc)
            self._is_loaded = True
            
            load_time = time.time() - start_time
            
            self.logger.info(f"Excel data loaded successfully: {len(self._products_cache)} products in {load_time:.2f} seconds")
            
            return {
                'products': self._products_cache,
                'prices': self._prices_cache,
                'filter_options': self._filter_options_cache,
                'load_time': load_time,
                'loaded_at': self._last_load_time,
                'product_count': len(self._products_cache)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load Excel data: {str(e)}")
            raise
    
    def _load_shopping_list_data(self) -> List[Product]:
        """
        Load product data from the shopping list Excel file.
        
        Returns:
            List of Product instances
        """
        if not self.shopping_list_file.exists():
            raise FileNotFoundError(f"Shopping list file not found: {self.shopping_list_file}")
        
        self.logger.info(f"Loading shopping list data from: {self.shopping_list_file}")
        
        try:
            # Load the complete cable tray lookup sheet
            df = pd.read_excel(
                self.shopping_list_file,
                sheet_name='Complete cable tray lookup',
                header=0
            )
            
            self.logger.info(f"Loaded {len(df)} rows from shopping list file")
            
            products = []
            
            for index, row in df.iterrows():
                try:
                    product = self._create_product_from_lookup_row(row, index)
                    if product:
                        products.append(product)
                
                except Exception as e:
                    self.logger.warning(f"Failed to process row {index}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully created {len(products)} products from shopping list")
            return products
            
        except Exception as e:
            self.logger.error(f"Error reading shopping list file: {str(e)}")
            raise
    
    def _create_product_from_lookup_row(self, row: pd.Series, index: int) -> Optional[Product]:
        """
        Create Product instance from Excel lookup table row.
        
        Based on actual Excel structure:
        - Type: Product type code (TCS, PCS, HET, etc.)
        - Hebrew Term: Hebrew description
        - English term: English description
        
        Args:
            row: Pandas Series representing Excel row
            index: Row index for logging
            
        Returns:
            Product instance or None if invalid
        """
        try:
            # Extract data from actual Excel columns
            product_type_code = self._safe_get_value(row, ['Type'], f"UNK-{index}")
            hebrew_desc = self._safe_get_value(row, ['Hebrew Term'], "")
            english_desc = self._safe_get_value(row, ['English term'], "")
            
            if not product_type_code or (not hebrew_desc and not english_desc):
                self.logger.warning(f"Row {index}: Missing required data - Type: {product_type_code}, Hebrew: {hebrew_desc}, English: {english_desc}")
                return None
            
            descriptions = ProductDescriptions(
                hebrew=hebrew_desc,
                english=english_desc
            )
            
            # Generate menora_id and supplier_code based on type
            menora_id = f"MEN-{product_type_code}-{index:03d}"
            supplier_code = f"HOLDEE-{product_type_code}-{index:03d}"
            
            # Specifications - basic type mapping
            product_type_name = self._map_type_code_to_name(product_type_code)
            
            # Only assign specific material if explicitly known, don't default to Steel
            material = None
            # Could be determined from Excel data if available in future columns
            
            specifications = ProductSpecifications(
                type=product_type_name,
                material=material
            )
            
            # Category mapping
            category = self._determine_category(product_type_code, english_desc)
            
            # Check for associated image
            image_url = self._get_product_image(index, product_type_code)
            
            return Product(
                menora_id=menora_id,
                supplier_code=supplier_code,
                descriptions=descriptions,
                category=category,
                specifications=specifications,
                supplier_name="HOLDEE",
                image_url=image_url,
                has_image=bool(image_url)
            )
            
        except Exception as e:
            self.logger.error(f"Error creating product from row {index}: {str(e)}")
            return None
    
    def _map_type_code_to_name(self, type_code: str) -> str:
        """Map type code to full product type name."""
        type_mapping = {
            'TCS': 'Channel Cable Tray',
            'PCS': 'Perforated Cable Tray', 
            'HET': 'Cable Trunking',
            'HWM': 'Wire Mesh Cable Tray',
            'HEL': 'Ladder Cable Tray',
            'HEP': 'Decorated Cable Tray',
            'CTC': 'Cable Tray Cover',
            'HETC': 'Cable Trunking Cover',
            'HELC': 'Ladder Cable Tray Cover',
            'HTCT': 'Half Tee for Cable Tray'
        }
        
        return type_mapping.get(type_code, f"Cable Tray ({type_code})")
    
    def _determine_category(self, type_code: str, english_desc: str) -> str:
        """Determine product category based on type code and description."""
        type_code_lower = type_code.lower()
        desc_lower = english_desc.lower()
        
        if any(keyword in desc_lower for keyword in ['cover', 'lid']):
            return 'cover'
        elif any(keyword in desc_lower for keyword in ['connector', 'tee', 'elbow', 'cross']):
            return 'connector'
        elif any(keyword in desc_lower for keyword in ['support', 'bracket', 'hanger']):
            return 'support'
        elif 'trunking' in desc_lower:
            return 'trunking'
        elif any(keyword in desc_lower for keyword in ['ladder', 'mesh', 'perforated', 'channel']):
            return 'cable_tray'
        else:
            return 'accessory'
    
    def _load_pricing_data(self, base_products: List[Product]) -> None:
        """
        Load pricing data from price table Excel file and create specific product variants.
        
        This creates actual sellable products with dimensions and pricing from the price sheets,
        using the base product types from the lookup table.
        
        Args:
            base_products: Base product types from lookup table
        """
        if not self.price_table_file.exists():
            self.logger.warning(f"Price table file not found: {self.price_table_file}")
            return
        
        self.logger.info(f"Loading pricing data from: {self.price_table_file}")
        
        try:
            # Read all sheets from price table file
            excel_file = pd.ExcelFile(self.price_table_file)
            sheet_names = excel_file.sheet_names
            
            self.logger.info(f"Found sheets in price table: {sheet_names}")
            
            # Create lookup of base products by type code
            base_product_lookup = {}
            for product in base_products:
                # Extract type code from menora_id (format: MEN-{TYPE}-{index})
                parts = product.menora_id.split('-')
                if len(parts) >= 2:
                    type_code = parts[1]
                    base_product_lookup[type_code] = product
            
            # Process height-specific sheets
            height_sheets = [name for name in sheet_names if name.isdigit()]
            
            for sheet_name in height_sheets:
                try:
                    new_products = self._create_products_from_price_sheet(
                        excel_file, sheet_name, base_product_lookup, int(sheet_name)
                    )
                    self._products_cache.extend(new_products)
                except Exception as e:
                    self.logger.error(f"Error processing price sheet {sheet_name}: {str(e)}")
                    continue
            
            # Process accessory sheets
            accessory_sheets = [name for name in sheet_names if not name.isdigit()]
            
            for sheet_name in accessory_sheets:
                try:
                    new_products = self._create_products_from_price_sheet(
                        excel_file, sheet_name, base_product_lookup
                    )
                    self._products_cache.extend(new_products)
                except Exception as e:
                    self.logger.error(f"Error processing accessory sheet {sheet_name}: {str(e)}")
                    continue
            
            # Update products cache to include only the priced variants
            total_products = len(self._products_cache)
            priced_products = sum(1 for p in self._products_cache if p.pricing is not None)
            
            self.logger.info(f"Created {total_products} products with {priced_products} having pricing")
            
        except Exception as e:
            self.logger.error(f"Error loading pricing data: {str(e)}")
    
    def _create_products_from_price_sheet(self, excel_file: pd.ExcelFile, sheet_name: str, 
                                         base_product_lookup: Dict[str, Product], 
                                         sheet_height: Optional[int] = None) -> List[Product]:
        """
        Create specific product variants from a price sheet.
        
        Args:
            excel_file: Excel file object
            sheet_name: Name of sheet to process
            base_product_lookup: Dictionary of base products by type code
            sheet_height: Height from sheet name (for height-specific sheets)
            
        Returns:
            List of new product variants
        """
        self.logger.debug(f"Creating products from price sheet: {sheet_name}")
        
        try:
            # Read with header at row 2 (0-based indexing)
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=2)
            
            if df.empty:
                self.logger.warning(f"Sheet {sheet_name} is empty")
                return []
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            self.logger.debug(f"Price sheet {sheet_name} columns: {list(df.columns)}")
            
            products = []
            row_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Extract pricing data based on actual structure
                    type_code = self._safe_get_value(row, ['TYPE', 'Type'], "")
                    galvanization = self._safe_get_value(row, ['גילוון'], "")
                    height = self._safe_get_numeric(row, ['גובה']) or sheet_height
                    width = self._safe_get_numeric(row, ['רוחב'])
                    thickness = self._safe_get_numeric(row, ['עובי'])
                    price = self._safe_get_numeric(row, ['מחיר'])
                    
                    if not type_code or price is None or price <= 0:
                        continue
                    
                    # Get base product for this type
                    base_product = base_product_lookup.get(type_code)
                    if not base_product:
                        # Create a generic base product for unknown types
                        base_product = self._create_generic_product(type_code)
                    
                    # Create specific product variant
                    variant_product = self._create_product_variant(
                        base_product, type_code, height, width, thickness, 
                        galvanization, price, row_count
                    )
                    
                    if variant_product:
                        products.append(variant_product)
                        row_count += 1
                    
                except Exception as e:
                    self.logger.debug(f"Error processing price row {index} in {sheet_name}: {str(e)}")
                    continue
            
            self.logger.info(f"Created {len(products)} product variants from sheet {sheet_name}")
            return products
                    
        except Exception as e:
            self.logger.error(f"Error reading price sheet {sheet_name}: {str(e)}")
            return []
    
    def _create_generic_product(self, type_code: str) -> Product:
        """Create a generic base product for unknown type codes."""
        image_url = self._get_product_image(0, type_code)
        
        return Product(
            menora_id=f"MEN-{type_code}-000",
            supplier_code=f"HOLDEE-{type_code}-000",
            descriptions=ProductDescriptions(
                hebrew=f"מוצר {type_code}",
                english=f"Product {type_code}"
            ),
            category="cable_tray",
            specifications=ProductSpecifications(
                type=self._map_type_code_to_name(type_code),
                material=None  # Don't default to Steel
            ),
            supplier_name="HOLDEE",
            image_url=image_url,
            has_image=bool(image_url)
        )
    
    def _create_product_variant(self, base_product: Product, type_code: str, 
                              height: Optional[float], width: Optional[float], 
                              thickness: Optional[float], galvanization: str, 
                              price: float, variant_index: int) -> Optional[Product]:
        """
        Create a specific product variant with dimensions and pricing.
        
        Args:
            base_product: Base product to clone
            type_code: Product type code
            height: Height dimension
            width: Width dimension
            thickness: Thickness dimension
            galvanization: Galvanization code
            price: Unit price
            variant_index: Index for unique ID generation
            
        Returns:
            Product variant or None
        """
        try:
            # Create unique identifiers
            dimensions = f"{int(height) if height else 'XX'}-{int(width) if width else 'XX'}-{thickness if thickness else 'X'}"
            menora_id = f"MEN-{type_code}-{dimensions}"
            supplier_code = f"{type_code}-{dimensions}-{galvanization}"
            
            # Create specifications with dimensions
            specifications = ProductSpecifications(
                type=base_product.specifications.type if base_product.specifications else self._map_type_code_to_name(type_code),
                height=int(height) if height else None,
                width=int(width) if width else None,
                thickness=thickness,
                galvanization=self._map_galvanization_code(galvanization),
                material=None  # Don't default to Steel, determine from actual data
            )
            
            # Create pricing
            pricing = ProductPricing(
                price=price,
                currency="ILS"
            )
            
            # Get image for this variant
            image_url = self._get_product_image(0, type_code)
            
            # Create product variant
            variant = Product(
                menora_id=menora_id,
                supplier_code=supplier_code,
                descriptions=base_product.descriptions,
                category=base_product.category,
                specifications=specifications,
                pricing=pricing,
                supplier_name=base_product.supplier_name,
                image_url=image_url,
                has_image=bool(image_url)
            )
            
            # Cache price for quick lookup
            self._prices_cache[supplier_code] = price
            
            return variant
            
        except Exception as e:
            self.logger.error(f"Error creating product variant: {str(e)}")
            return None
    
    def _map_galvanization_code(self, code: str) -> str:
        """Map galvanization code to full name."""
        galv_mapping = {
            'PGL': 'Pre-Galvanized',
            'HDG': 'Hot Dip Galvanized',
            'SS': 'Stainless Steel',
            'AL': 'Aluminum'
        }
        
        return galv_mapping.get(code, code)
    
    def _generate_filter_options(self) -> None:
        """Generate available filter options from loaded products."""
        if not self._products_cache:
            return
        
        types = set()
        heights = set()
        widths = set()
        thicknesses = set()
        galvanizations = set()
        
        for product in self._products_cache:
            if product.specifications:
                spec = product.specifications
                if spec.type:
                    types.add(spec.type)
                if spec.height:
                    heights.add(spec.height)
                if spec.width:
                    widths.add(spec.width)
                if spec.thickness:
                    thicknesses.add(spec.thickness)
                if spec.galvanization:
                    galvanizations.add(spec.galvanization)
        
        self._filter_options_cache = {
            'type': sorted(list(types)),
            'height': sorted(list(heights)),
            'width': sorted(list(widths)),
            'thickness': sorted(list(thicknesses)),
            'galvanization': sorted(list(galvanizations))
        }
    
    def _safe_get_value(self, row: pd.Series, column_names: List[str], default: str = "") -> str:
        """
        Safely get string value from row with multiple possible column names.
        
        Args:
            row: Pandas row
            column_names: List of possible column names
            default: Default value if not found
            
        Returns:
            String value or default
        """
        for col_name in column_names:
            if col_name in row.index:
                value = row[col_name]
                if pd.notna(value):
                    return str(value).strip()
        
        return default
    
    def _safe_get_numeric(self, row: pd.Series, column_names: List[str]) -> Optional[float]:
        """
        Safely get numeric value from row with multiple possible column names.
        
        Args:
            row: Pandas row  
            column_names: List of possible column names
            
        Returns:
            Numeric value or None
        """
        for col_name in column_names:
            if col_name in row.index:
                value = row[col_name]
                if pd.notna(value):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def get_products(self) -> List[Product]:
        """Get cached products list."""
        if not self._is_loaded:
            raise RuntimeError("Excel data not loaded. Call load_data() first.")
        
        return self._products_cache.copy()
    
    def get_filter_options(self) -> Dict[str, List[Any]]:
        """Get available filter options."""
        if not self._is_loaded:
            raise RuntimeError("Excel data not loaded. Call load_data() first.")
        
        return self._filter_options_cache.copy()
    
    def get_product_by_menora_id(self, menora_id: str) -> Optional[Product]:
        """
        Get product by Menora ID.
        
        Args:
            menora_id: Menora catalog number
            
        Returns:
            Product instance or None
        """
        if not self._is_loaded:
            return None
        
        for product in self._products_cache:
            if product.menora_id == menora_id:
                return product
        
        return None
    
    def is_data_loaded(self) -> bool:
        """Check if data is loaded."""
        return self._is_loaded
    
    def get_load_info(self) -> Dict[str, Any]:
        """Get information about last data load."""
        return {
            'is_loaded': self._is_loaded,
            'last_load_time': self._last_load_time,
            'product_count': len(self._products_cache),
            'has_pricing': len(self._prices_cache),
            'filter_options': len(self._filter_options_cache)
        }
    
    def _extract_images_from_excel(self, file_path: Path) -> Dict[str, str]:
        """
        Extract embedded images from Excel file and map them to row numbers.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Dictionary mapping row numbers to image paths
        """
        image_map = {}
        
        try:
            workbook = openpyxl.load_workbook(file_path, data_only=False)
            
            # Focus on the specific sheet with product data
            if 'Complete cable tray lookup' in workbook.sheetnames:
                sheet = workbook['Complete cable tray lookup']
                
                # Create static images directory for web access
                static_images_dir = Path('app/static/images')
                static_images_dir.mkdir(parents=True, exist_ok=True)
                
                # Check for embedded images in the sheet
                if hasattr(sheet, '_images') and sheet._images:
                    self.logger.info(f"Found {len(sheet._images)} embedded images in Complete cable tray lookup sheet")
                    
                    for i, image in enumerate(sheet._images):
                        try:
                            # Get the row where the image is located
                            if hasattr(image, 'anchor') and hasattr(image.anchor, '_from'):
                                row = image.anchor._from.row + 1  # Convert to 1-based indexing
                                
                                # Generate unique filename for the image
                                image_filename = f"product_row_{row}_{i}.png"
                                static_image_path = static_images_dir / image_filename
                                
                                # Extract and save the image
                                if hasattr(image, '_data') and callable(image._data):
                                    with open(static_image_path, 'wb') as f:
                                        f.write(image._data())
                                    
                                    # Store relative path for web access, mapped by row number
                                    relative_path = f"/static/images/{image_filename}"
                                    image_map[str(row)] = relative_path
                                    
                                    self.logger.debug(f"Extracted image for row {row}: {image_filename}")
                                elif hasattr(image, 'ref'):
                                    # Alternative approach for different openpyxl versions
                                    with open(static_image_path, 'wb') as f:
                                        f.write(image.ref)
                                    
                                    relative_path = f"/static/images/{image_filename}"
                                    image_map[str(row)] = relative_path
                                    
                                    self.logger.debug(f"Extracted image for row {row}: {image_filename}")
                        except Exception as img_error:
                            self.logger.warning(f"Failed to extract individual image {i}: {str(img_error)}")
                            continue
            
            workbook.close()
            self.logger.info(f"Successfully extracted {len(image_map)} images from Excel file")
            
        except Exception as e:
            self.logger.warning(f"Failed to extract images from {file_path}: {str(e)}")
        
        return image_map
    
    def _get_product_image(self, row_index: int, product_type: str) -> Optional[str]:
        """
        Get image URL for a product based on Excel row number.
        
        Args:
            row_index: Excel row index (1-based)
            product_type: Product type code
            
        Returns:
            Image URL if found, None otherwise
        """
        # Direct row match - images are mapped by row number
        row_key = str(row_index)
        if row_key in self._all_images:
            return self._all_images[row_key]
        
        # Try row + 1 (sometimes there's an offset)
        row_key_plus = str(row_index + 1)
        if row_key_plus in self._all_images:
            return self._all_images[row_key_plus]
        
        # Try row - 1 (header offset)
        row_key_minus = str(row_index - 1)
        if row_key_minus in self._all_images:
            return self._all_images[row_key_minus]
        
        return None
    
    def _start_background_image_extraction(self):
        """Start background thread for image extraction."""
        if self._image_extraction_thread and self._image_extraction_thread.is_alive():
            return  # Already running
        
        self._image_extraction_thread = threading.Thread(
            target=self._background_image_extraction,
            daemon=True,
            name="ImageExtractor"
        )
        self._image_extraction_thread.start()
        self.logger.info("Started background image extraction thread")
    
    def _background_image_extraction(self):
        """Extract images in background thread."""
        try:
            self.logger.info("Starting background image extraction...")
            start_time = time.time()
            
            # Extract images from Excel files
            shopping_list_images = self._extract_images_from_excel(self.shopping_list_file)
            price_table_images = self._extract_images_from_excel(self.price_table_file)
            
            # Combine all image maps (thread-safe update)
            combined_images = {**shopping_list_images, **price_table_images}
            self._all_images.update(combined_images)
            
            extraction_time = time.time() - start_time
            self._images_loaded = True
            
            self.logger.info(f"Background image extraction completed: {len(combined_images)} images in {extraction_time:.2f}s")
            
            # Update products with image URLs now that images are extracted
            self._update_product_images()
            
        except Exception as e:
            self.logger.error(f"Background image extraction failed: {str(e)}")
    
    def _update_product_images(self):
        """Update existing products with extracted image URLs."""
        updated_count = 0
        for product in self._products_cache:
            if not product.image_url:  # Only update if no image URL set
                # Try to find image for this product
                row_number = self._get_row_number_for_product(product)
                if row_number:
                    image_url = self._get_product_image(row_number, product.supplier_code.split('-')[-2] if '-' in product.supplier_code else '')
                    if image_url:
                        product.image_url = image_url
                        product.has_image = True
                        updated_count += 1
        
        if updated_count > 0:
            self.logger.info(f"Updated {updated_count} products with background-extracted images")
    
    def _get_row_number_for_product(self, product) -> Optional[int]:
        """Try to determine Excel row number for a product."""
        # For products created from shopping list, extract row from menora_id
        if hasattr(product, 'menora_id') and 'MEN-' in product.menora_id:
            try:
                parts = product.menora_id.split('-')
                if len(parts) >= 3:
                    return int(parts[-1])  # Last part should be row number
            except (ValueError, IndexError):
                pass
        return None
    
    def is_images_loaded(self) -> bool:
        """Check if background image extraction is complete."""
        return self._images_loaded