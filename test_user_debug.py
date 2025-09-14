#!/usr/bin/env python3
"""
Test the debug endpoint to understand user state
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_debug():
    session = requests.Session()
    
    # Login first
    print("1. Logging in...")
    response = session.post(f"{BASE_URL}/auth/login", data={'user_code': 'TEST123'})
    print(f"Login status: {response.status_code}")
    
    if response.status_code != 200:
        print("Login failed")
        return
    
    # Check debug info
    print("\n2. Getting debug info...")
    response = session.get(f"{BASE_URL}/shopping-list/debug-user")
    print(f"Debug status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Debug data: {json.dumps(data, indent=2, default=str)}")
    else:
        print(f"Debug failed: {response.text}")

if __name__ == "__main__":
    test_debug()