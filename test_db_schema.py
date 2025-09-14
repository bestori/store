#!/usr/bin/env python3
"""
Check database schema to see what shopping list tables exist
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def check_tables():
    # Check health endpoint for database info
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        tables = data.get('database', {}).get('tables', [])
        print(f"Database tables: {tables}")
        
        # Check if shopping list tables exist
        shopping_tables = [t for t in tables if 'shopping' in t.lower()]
        print(f"Shopping-related tables: {shopping_tables}")
    else:
        print(f"Health check failed: {response.status_code}")

if __name__ == "__main__":
    check_tables()