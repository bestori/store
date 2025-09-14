#!/usr/bin/env python3
"""
Test script for Excel loader functionality
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app.services.excel_loader import ExcelLoader
from config.config import DevelopmentConfig
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_excel_loader():
    """Test the Excel loader functionality."""
    print("=== Testing Excel Loader ===")
    
    # Create config
    config = {
        'EXCEL_DATA_DIR': project_root / 'data' / 'excel_files',
        'SHOPPING_LIST_FILE': 'NEW Shopping list test.xlsm',
        'PRICE_TABLE_FILE': 'טבלת מחירים ורד 01092025.xlsx'
    }
    
    # Create loader
    loader = ExcelLoader(config)
    
    try:
        # Load data
        print("Loading Excel data...")
        result = loader.load_data()
        
        print(f"\nLoad Results:")
        print(f"- Products loaded: {result['product_count']}")
        print(f"- Load time: {result['load_time']:.2f} seconds")
        print(f"- Prices cached: {len(result['prices'])}")
        print(f"- Filter options: {list(result['filter_options'].keys())}")
        
        # Show sample products
        products = result['products']
        if products:
            print(f"\nSample Products (first 5):")
            for i, product in enumerate(products[:5]):
                print(f"{i+1}. {product.menora_id}")
                print(f"   Hebrew: {product.descriptions.hebrew}")
                print(f"   English: {product.descriptions.english}")
                print(f"   Category: {product.category}")
                if product.specifications:
                    print(f"   Specs: H={product.specifications.height}, W={product.specifications.width}, T={product.specifications.thickness}")
                if product.pricing:
                    print(f"   Price: {product.pricing.price} {product.pricing.currency}")
                print()
        
        # Show filter options
        filter_options = result['filter_options']
        print("Filter Options:")
        for key, values in filter_options.items():
            print(f"- {key}: {values[:5]}..." if len(values) > 5 else f"- {key}: {values}")
        
        # Test search functionality
        print(f"\nTesting search...")
        test_queries = ["תעלה", "cable", "TCS", "50"]
        
        for query in test_queries:
            matches = []
            for product in products:
                if product.matches_search(query):
                    matches.append(product)
            
            print(f"Query '{query}': {len(matches)} matches")
            if matches:
                print(f"  First match: {matches[0].descriptions.english}")
        
        print("\n✅ Excel loader test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing Excel loader: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_excel_loader()