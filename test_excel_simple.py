#!/usr/bin/env python3
"""
Simple test for Excel data loading without Flask dependencies
"""

import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).parent.absolute()

def simple_excel_test():
    """Simple test to verify Excel files can be read."""
    print("=== Simple Excel File Test ===")
    
    # Test shopping list file
    shopping_file = project_root / 'data' / 'excel_files' / 'NEW Shopping list test.xlsm'
    price_file = project_root / 'data' / 'excel_files' / 'טבלת מחירים ורד 01092025.xlsx'
    
    print(f"Shopping list file exists: {shopping_file.exists()}")
    print(f"Price table file exists: {price_file.exists()}")
    
    if shopping_file.exists():
        try:
            # Read shopping list
            excel_file = pd.ExcelFile(shopping_file)
            print(f"Shopping list sheets: {excel_file.sheet_names}")
            
            # Read the complete lookup sheet
            df = pd.read_excel(shopping_file, sheet_name='Complete cable tray lookup', header=0)
            print(f"Lookup table: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"Sample products:")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                print(f"  {row['Type']}: {row['Hebrew Term']} / {row['English term']}")
            
        except Exception as e:
            print(f"Error reading shopping list: {e}")
    
    if price_file.exists():
        try:
            # Read price file
            excel_file = pd.ExcelFile(price_file)
            print(f"\nPrice table sheets: {excel_file.sheet_names}")
            
            # Read height 50 sheet
            sheet_name = '50'
            if sheet_name in excel_file.sheet_names:
                # Read with header at row 2 (0-based)
                df = pd.read_excel(price_file, sheet_name=sheet_name, header=2)
                print(f"Height {sheet_name} sheet: {df.shape[0]} rows, {df.shape[1]} columns")
                
                # Clean column names
                df.columns = df.columns.str.strip()
                print(f"Columns: {list(df.columns)}")
                
                # Show sample data
                print("Sample pricing data:")
                for i in range(min(3, len(df))):
                    row = df.iloc[i]
                    if pd.notna(row.iloc[0]):  # Skip empty rows
                        print(f"  {row['TYPE']} - {row['גילוון']} - H:{row['גובה']} W:{row['רוחב']} T:{row['עובי']} - Price:{row['מחיר']}")
            
        except Exception as e:
            print(f"Error reading price table: {e}")
    
    print("✅ Simple Excel test completed")

if __name__ == "__main__":
    simple_excel_test()