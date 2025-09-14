#!/usr/bin/env python3
"""
Simple test to isolate the add to cart issue
"""

import requests

def find_server_port():
    """Try to find which port the Flask server is running on"""
    common_ports = [5000, 5001, 5002, 5003, 5004, 5005, 8000, 8080, 3000, 8888, 4000, 4001]
    
    for port in common_ports:
        try:
            url = f"http://localhost:{port}"
            response = requests.get(url, timeout=1)
            print(f"Port {port}: {response.status_code} - {response.headers.get('Server', 'Unknown')}")
            
            # Check if it's a Flask server by looking for Flask-specific routes
            if response.status_code in [200, 302, 404]:
                try:
                    health_response = requests.get(f"{url}/health", timeout=1)
                    if health_response.status_code == 200 and 'app_status' in health_response.text:
                        print(f"Found Flask server on port {port}")
                        return url
                except:
                    pass
        except requests.exceptions.RequestException as e:
            print(f"Port {port}: Connection failed")
            continue
    
    print("Could not find Flask server on common ports")
    return None

def test_simple_cart():
    # Use the specific address the user mentioned
    base_url = "http://127.0.0.1:5000"
        
    session = requests.Session()
    
    # Login
    print("1. Logging in...")
    response = session.post(f"{base_url}/auth/login", data={'user_code': 'TEST123'})
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
        f"{base_url}/shopping-list/add-item",
        json=add_data
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    print(f"Response headers: {dict(response.headers)}")

if __name__ == "__main__":
    test_simple_cart()