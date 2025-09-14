#!/usr/bin/env python3
"""
Check the structure of existing shopping_lists table
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def check_shopping_lists():
    session = requests.Session()
    
    # Login first
    response = session.post(f"{BASE_URL}/auth/login", data={'user_code': 'TEST123'})
    if response.status_code != 200:
        print("Login failed")
        return
    
    # Try to access database through a simple endpoint
    response = session.get(f"{BASE_URL}/shopping-list/debug-user")
    
    if response.status_code == 200:
        data = response.json()
        shopping_lists = data.get('shopping_lists', [])
        print(f"Shopping lists in DB: {shopping_lists}")
        
        # Show the structure
        if shopping_lists:
            print(f"Sample shopping list structure: {shopping_lists[0].keys()}")
        else:
            print("No shopping lists found - need to check table schema")
    else:
        print(f"Failed to get debug info: {response.text}")

if __name__ == "__main__":
    check_shopping_lists()