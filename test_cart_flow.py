#!/usr/bin/env python3
"""
Simple test script to debug the add to cart flow
"""

import requests
import json

BASE_URL = "https://web-production-8f004.up.railway.app"

def test_login_and_add_to_cart():
    print("🧪 Testing login and add to cart flow...")
    
    # Create a session
    session = requests.Session()
    
    # Step 1: Try to login
    print("\n1. Testing login...")
    login_data = {
        'user_code': 'TEST123'
    }
    
    response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
    print(f"Login response status: {response.status_code}")
    print(f"Login response headers: {dict(response.headers)}")
    
    # Check if we got redirected (successful login)
    if response.status_code == 302:
        print("✅ Login successful - got redirect")
        print(f"Redirect location: {response.headers.get('Location')}")
    else:
        print("❌ Login failed or unexpected response")
        print(f"Response text: {response.text[:500]}")
        return
    
    # Step 2: Check cookies after login
    print("\n2. Checking cookies after login...")
    cookies = session.cookies.get_dict()
    print(f"Cookies after login: {cookies}")
    
    # Step 2b: Check if we can access shopping list (authentication check)  
    print("\n2b. Testing shopping list access...")
    response = session.get(f"{BASE_URL}/shopping-list")
    print(f"Shopping list access status: {response.status_code}")
    print(f"Response cookies: {response.cookies.get_dict()}")
    
    if response.status_code == 200:
        print("✅ Can access shopping list - authentication working")
    else:
        print("❌ Cannot access shopping list")
        print(f"Response text: {response.text[:500]}")
        return
    
    # Step 3: Check session cookies
    print("\n3. Checking session cookies...")
    cookies = session.cookies.get_dict()
    print(f"Session cookies: {cookies}")
    
    # Step 4: Try to add item to cart
    print("\n4. Testing add to cart...")
    add_item_data = {
        'menora_id': 'MEN-HB30-041',  # From our search results
        'quantity': 2,
        'notes': 'Test item'
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Add cookies manually if needed
    if cookies:
        headers['Cookie'] = '; '.join([f'{k}={v}' for k, v in cookies.items()])
    
    response = session.post(
        f"{BASE_URL}/shopping-list/add-item",
        json=add_item_data,
        headers=headers
    )
    
    print(f"Add to cart status: {response.status_code}")
    print(f"Add to cart response: {response.text}")
    print(f"Request headers sent: {headers}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('success'):
                print("✅ Add to cart successful!")
                print(f"Response data: {json.dumps(data, indent=2)}")
            else:
                print("❌ Add to cart failed")
                print(f"Error: {data.get('error')}")
        except:
            print("❌ Could not parse JSON response")
    else:
        print("❌ Add to cart HTTP error")
    
    # Step 4: Check shopping list contents
    print("\n4. Checking shopping list contents...")
    response = session.get(f"{BASE_URL}/shopping-list")
    if response.status_code == 200 and "MEN-HB30-041" in response.text:
        print("✅ Item appears in shopping list!")
    else:
        print("❌ Item not found in shopping list")

if __name__ == "__main__":
    test_login_and_add_to_cart()