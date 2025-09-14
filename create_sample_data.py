#!/usr/bin/env python3
"""
Create sample Excel files for Store application.

This script creates the required Excel files with sample data for development and testing.
"""

import os
import pandas as pd
from pathlib import Path

def create_sample_excel_files():
    """Create sample Excel files with cable tray data."""
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    print("Creating sample Excel files...")
    
    # 1. Create "New shopping list.xlsx" - Product catalog
    create_shopping_list_file(data_dir / "New shopping list.xlsx")
    
    # 2. Create "Vered Price Table.xlsx" - Pricing data
    create_price_table_file(data_dir / "Vered Price Table.xlsx")
    
    print("✅ Sample Excel files created successfully!")
    print("\nFiles created:")
    print(f"  📄 {data_dir / 'New shopping list.xlsx'}")
    print(f"  📄 {data_dir / 'Vered Price Table.xlsx'}")
    print("\n🚀 You can now run the Flask application!")


def create_shopping_list_file(file_path):
    """Create the shopping list catalog file."""
    print(f"Creating {file_path}...")
    
    # Sample cable tray product data
    products_data = [
        # Ladder type cable trays
        {"Type": "LT50-100", "Hebrew Term": "מגש סולמי 50×100", "English term": "Ladder Tray 50x100mm"},
        {"Type": "LT50-150", "Hebrew Term": "מגש סולמי 50×150", "English term": "Ladder Tray 50x150mm"},
        {"Type": "LT50-200", "Hebrew Term": "מגש סולמי 50×200", "English term": "Ladder Tray 50x200mm"},
        {"Type": "LT75-100", "Hebrew Term": "מגש סולמי 75×100", "English term": "Ladder Tray 75x100mm"},
        {"Type": "LT75-150", "Hebrew Term": "מגש סולמי 75×150", "English term": "Ladder Tray 75x150mm"},
        {"Type": "LT75-200", "Hebrew Term": "מגש סולמי 75×200", "English term": "Ladder Tray 75x200mm"},
        {"Type": "LT100-100", "Hebrew Term": "מגש סולמי 100×100", "English term": "Ladder Tray 100x100mm"},
        {"Type": "LT100-150", "Hebrew Term": "מגש סולמי 100×150", "English term": "Ladder Tray 100x150mm"},
        {"Type": "LT100-200", "Hebrew Term": "מגש סולמי 100×200", "English term": "Ladder Tray 100x200mm"},
        {"Type": "LT100-300", "Hebrew Term": "מגש סולמי 100×300", "English term": "Ladder Tray 100x300mm"},
        
        # Perforated cable trays
        {"Type": "PT50-100", "Hebrew Term": "מגש מחורר 50×100", "English term": "Perforated Tray 50x100mm"},
        {"Type": "PT50-150", "Hebrew Term": "מגש מחורר 50×150", "English term": "Perforated Tray 50x150mm"},
        {"Type": "PT50-200", "Hebrew Term": "מגש מחורר 50×200", "English term": "Perforated Tray 50x200mm"},
        {"Type": "PT75-100", "Hebrew Term": "מגש מחורר 75×100", "English term": "Perforated Tray 75x100mm"},
        {"Type": "PT75-150", "Hebrew Term": "מגש מחורר 75×150", "English term": "Perforated Tray 75x150mm"},
        {"Type": "PT75-200", "Hebrew Term": "מגש מחורר 75×200", "English term": "Perforated Tray 75x200mm"},
        {"Type": "PT100-100", "Hebrew Term": "מגש מחורר 100×100", "English term": "Perforated Tray 100x100mm"},
        {"Type": "PT100-150", "Hebrew Term": "מגש מחורר 100×150", "English term": "Perforated Tray 100x150mm"},
        {"Type": "PT100-200", "Hebrew Term": "מגש מחורר 100×200", "English term": "Perforated Tray 100x200mm"},
        
        # Solid cable trays
        {"Type": "ST50-100", "Hebrew Term": "מגש מלא 50×100", "English term": "Solid Tray 50x100mm"},
        {"Type": "ST50-150", "Hebrew Term": "מגש מלא 50×150", "English term": "Solid Tray 50x150mm"},
        {"Type": "ST75-100", "Hebrew Term": "מגש מלא 75×100", "English term": "Solid Tray 75x100mm"},
        {"Type": "ST75-150", "Hebrew Term": "מגש מלא 75×150", "English term": "Solid Tray 75x150mm"},
        {"Type": "ST100-100", "Hebrew Term": "מגש מלא 100×100", "English term": "Solid Tray 100x100mm"},
        {"Type": "ST100-150", "Hebrew Term": "מגש מלא 100×150", "English term": "Solid Tray 100x150mm"},
        
        # Wire mesh trays
        {"Type": "WM50-100", "Hebrew Term": "מגש רשת 50×100", "English term": "Wire Mesh Tray 50x100mm"},
        {"Type": "WM50-150", "Hebrew Term": "מגש רשת 50×150", "English term": "Wire Mesh Tray 50x150mm"},
        {"Type": "WM75-100", "Hebrew Term": "מגש רשת 75×100", "English term": "Wire Mesh Tray 75x100mm"},
        {"Type": "WM75-150", "Hebrew Term": "מגש רשת 75×150", "English term": "Wire Mesh Tray 75x150mm"},
        
        # Accessories
        {"Type": "CNR-90", "Hebrew Term": "פינה 90 מעלות", "English term": "90° Corner"},
        {"Type": "CNR-45", "Hebrew Term": "פינה 45 מעלות", "English term": "45° Corner"},
        {"Type": "TEE-T", "Hebrew Term": "חיבור T", "English term": "T Junction"},
        {"Type": "RED-50-100", "Hebrew Term": "צמצום 50-100", "English term": "Reducer 50-100mm"},
        {"Type": "CVR-100", "Hebrew Term": "מכסה 100מ\"מ", "English term": "Cover 100mm"},
        {"Type": "CVR-150", "Hebrew Term": "מכסה 150מ\"מ", "English term": "Cover 150mm"},
        {"Type": "BRK-ADJ", "Hebrew Term": "תומך מתכוונן", "English term": "Adjustable Bracket"},
        {"Type": "BRK-FIX", "Hebrew Term": "תומך קבוע", "English term": "Fixed Bracket"},
        {"Type": "SEP-PLT", "Hebrew Term": "פלטת הפרדה", "English term": "Separator Plate"},
        {"Type": "END-CAP", "Hebrew Term": "סגירת קצה", "English term": "End Cap"}
    ]
    
    # Create DataFrame and save to Excel
    df = pd.DataFrame(products_data)
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Complete cable tray lookup', index=False)
    
    print(f"  ✅ Created product catalog with {len(products_data)} items")


def create_price_table_file(file_path):
    """Create the price table file with multiple sheets."""
    print(f"Creating {file_path}...")
    
    # Base prices and configurations
    base_configs = {
        # Height: (height_mm, base_price_multiplier)
        50: (50, 1.0),
        75: (75, 1.2),
        100: (100, 1.5),
        200: (200, 2.0)
    }
    
    galvanization_types = {
        'רגיל': ('Standard', 1.0),
        'מגולוון חם': ('Hot Galvanized', 1.3),
        'נירוסטה': ('Stainless Steel', 2.5),
        'אלומיניום': ('Aluminum', 1.8)
    }
    
    product_types = [
        ('LT', 'Ladder Tray', 45.0),
        ('PT', 'Perforated Tray', 55.0),
        ('ST', 'Solid Tray', 65.0),
        ('WM', 'Wire Mesh Tray', 40.0)
    ]
    
    widths = [100, 150, 200, 300, 400, 500, 600]
    thicknesses = [1.0, 1.2, 1.5, 2.0]
    
    # Create price data for each height sheet
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        for height, (height_mm, height_multiplier) in base_configs.items():
            sheet_data = []
            
            for product_code, product_name, base_price in product_types:
                for galv_hebrew, (galv_english, galv_multiplier) in galvanization_types.items():
                    for width in widths:
                        for thickness in thicknesses:
                            # Calculate final price
                            width_multiplier = 1.0 + (width - 100) / 1000  # Wider = more expensive
                            thickness_multiplier = 1.0 + (thickness - 1.0) * 0.2  # Thicker = more expensive
                            
                            final_price = (base_price * height_multiplier * 
                                         galv_multiplier * width_multiplier * thickness_multiplier)
                            
                            # Create TYPE code
                            type_code = f"{product_code}{height}-{width}"
                            
                            sheet_data.append({
                                'TYPE': type_code,
                                'גילוון': galv_hebrew,
                                'גובה': height_mm,
                                'רוחב': width,
                                'עובי': thickness,
                                'מחיר': round(final_price, 2)
                            })
            
            # Create DataFrame and save to sheet
            df = pd.DataFrame(sheet_data)
            df.to_excel(writer, sheet_name=str(height), index=False)
            
            print(f"  ✅ Created price sheet '{height}' with {len(sheet_data)} price points")


if __name__ == "__main__":
    print("🏗️  Store - Sample Data Generator")
    print("=" * 50)
    
    try:
        create_sample_excel_files()
    except Exception as e:
        print(f"❌ Error creating sample files: {e}")
        exit(1)