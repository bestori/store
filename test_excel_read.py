#!/usr/bin/env python3
"""
Test script to understand the Excel file structure
"""

import pandas as pd
import sys
from pathlib import Path

def analyze_shopping_list_file():
    """Analyze the shopping list Excel file."""
    print("=== Shopping List File Analysis ===")
    
    file_path = Path("data/excel_files/NEW Shopping list test.xlsm")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    try:
        excel_file = pd.ExcelFile(file_path)
        print(f"Available sheets: {excel_file.sheet_names}")
        
        # Read the complete lookup sheet
        sheet_name = "Complete cable tray lookup"
        if sheet_name in excel_file.sheet_names:
            print(f"\n--- Analyzing {sheet_name} ---")
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print(f"\nFirst 10 rows:")
            print(df.head(10))
            print(f"\nData types:")
            print(df.dtypes)
        
    except Exception as e:
        print(f"Error: {e}")

def analyze_price_table_file():
    """Analyze the price table Excel file."""
    print("\n=== Price Table File Analysis ===")
    
    file_path = Path("data/excel_files/טבלת מחירים ורד 01092025.xlsx")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    try:
        excel_file = pd.ExcelFile(file_path)
        print(f"Available sheets: {excel_file.sheet_names}")
        
        # Analyze height sheets (50, 75, 100, 200)
        for sheet_name in ['50', '75', '100']:
            if sheet_name in excel_file.sheet_names:
                print(f"\n--- Analyzing sheet {sheet_name} ---")
                
                # Try to read with different approaches
                df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                print(f"Raw shape: {df_raw.shape}")
                print("Raw first few rows:")
                print(df_raw.head())
                
                # Try to find the header row
                for i in range(min(5, len(df_raw))):
                    row = df_raw.iloc[i]
                    if 'TYPE' in str(row.values).upper() or 'גובה' in str(row.values):
                        print(f"Found potential header at row {i}: {row.values}")
                        
                        # Read with this header
                        df_with_header = pd.read_excel(file_path, sheet_name=sheet_name, header=i)
                        print(f"With header - Shape: {df_with_header.shape}")
                        print(f"Columns: {list(df_with_header.columns)}")
                        print("Sample data:")
                        print(df_with_header.head())
                        break
                break  # Just analyze one sheet for now
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_shopping_list_file()
    analyze_price_table_file()