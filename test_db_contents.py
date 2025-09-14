#!/usr/bin/env python3
"""
Check raw database contents
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def check_db():
    session = requests.Session()
    
    # Login first
    response = session.post(f"{BASE_URL}/auth/login", data={'user_code': 'TEST123'})
    if response.status_code != 200:
        print("Login failed")
        return
    
    # Check raw database contents
    response = session.get(f"{BASE_URL}/shopping-list/debug-db")
    
    if response.status_code == 200:
        data = response.json()
        print(f"All shopping lists: {json.dumps(data['all_shopping_lists'], indent=2, default=str)}")
        print(f"\nAll users: {json.dumps(data['all_users'], indent=2, default=str)}")
    else:
        print(f"DB check failed: {response.text}")

if __name__ == "__main__":
    check_db()