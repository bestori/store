#!/usr/bin/env python3
"""
Simple test to isolate the add to cart issue
"""

import requests

BASE_URL = "https://web-production-8f004.up.railway.app"

def test_simple_cart():
    session = requests.Session()
    
    # Login
    print("1. Logging in...")
    response = session.post(f"{BASE_URL}/auth/login", data={'user_code': 'TEST123'})
    print(f"Login status: {response.status_code}")
    print(f"Cookies after login: {session.cookies.get_dict()}")
    
    # Immediate add-to-cart test
    print("\n2. Immediate add to cart test...")
    
    add_data = {
        'menora_id': 'MEN-HB30-041',
        'quantity': 1,
        'notes': 'Test'
    }
    
    # Show exactly what we're sending
    print(f"Sending data: {add_data}")
    print(f"Session cookies: {session.cookies}")
    
    response = session.post(
        f"{BASE_URL}/shopping-list/add-item",
        json=add_data
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    print(f"Response headers: {dict(response.headers)}")

if __name__ == "__main__":
    test_simple_cart()