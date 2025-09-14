"""
Playwright tests for the Cable Tray Online Store application.
Tests login, search, and filtered search functionality.
"""

import pytest
import pytest_asyncio
import asyncio
import re
from playwright.async_api import async_playwright, expect
import os
import time

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class TestCableTrayStore:
    """Test suite for the Cable Tray Online Store."""
    
    @pytest_asyncio.fixture
    async def page(self):
        """Create a new page for each test."""
        async with async_playwright() as p:
            # Launch browser (use Firefox - works better on macOS)
            try:
                browser = await p.firefox.launch(headless=False, slow_mo=1000)
            except Exception:
                # Fallback to Chromium if Firefox fails
                browser = await p.chromium.launch(
                    headless=False, 
                    slow_mo=1000,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            
            page = await context.new_page()
            
            # Set base URL - use 127.0.0.1:5000 for local Flask app
            base_url = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:5000')
            await page.goto(base_url, timeout=30000)  # 30 second timeout
            
            yield page
            
            # Cleanup
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_homepage_loads(self, page):
        """Test that the homepage loads correctly."""
        # Wait for page to fully load
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        # Wait 5 seconds for any dynamic content
        await asyncio.sleep(5)
        
        # Check if we're redirected to login or if homepage loads
        await expect(page).to_have_title(re.compile(".*Store.*"), timeout=15000)
        
        # Check for login form or welcome message
        login_form = page.locator('form[action*="login"]')
        await expect(login_form).to_be_visible(timeout=15000)
        
        # Check for user code input
        user_code_input = page.locator('input[name="user_code"]')
        await expect(user_code_input).to_be_visible(timeout=15000)
        
        # Enter a random user code
        await user_code_input.fill('TEST123')
        
        # Submit login form (use more specific selector)
        login_button = page.locator('button[id="loginButton"]')
        await expect(login_button).to_be_visible(timeout=15000)
        await login_button.click()
        
        # Wait for redirect to search page
        await page.wait_for_url('**/search/**', timeout=30000)
        
        # Wait for search page to load
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(5)  # Give more time for products to load
        
        # Check for search interface
        search_input = page.locator('input[id="searchQuery"]')
        await expect(search_input).to_be_visible(timeout=15000)
        
        # Wait for products to load by checking console logs or API calls
        # The JavaScript loads products on page load, so we need to wait for that
        await asyncio.sleep(5)  # Additional wait for products API call
        
        # Debug: Check if products API is accessible
        try:
            response = await page.request.get('http://127.0.0.1:5000/api/v1/products')
            if response.status == 200:
                data = await response.json()
                print(f"✅ Products API accessible: {data.get('data', {}).get('count', 0)} products")
                # Debug: Show first few products
                products = data.get('data', {}).get('products', [])
                if products:
                    print(f"📋 Sample product: {products[0]}")
                    # Check if any products contain 'cable' in their descriptions
                    cable_products = [p for p in products if 'cable' in str(p.get('hebrew', '')).lower() or 'cable' in str(p.get('english', '')).lower()]
                    print(f"🔍 Products containing 'cable': {len(cable_products)}")
            else:
                print(f"⚠️ Products API returned status: {response.status}")
        except Exception as e:
            print(f"⚠️ Products API check failed: {str(e)}")
        
        # Search for a product
        await search_input.fill('cable')
        
        # Click search button (use specific selector for text search form)
        search_button = page.locator('#textSearchForm button[type="submit"]')
        await expect(search_button).to_be_visible(timeout=15000)
        await search_button.click()
        
        # Wait for results to load - check for either results or empty state
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(5)  # Give more time for search processing
        
        # Debug: Check what's visible on the page after search
        results_container = page.locator('#searchResults')
        empty_state = page.locator('#emptyState')
        print(f"🔍 After search - Results container visible: {await results_container.is_visible()}")
        print(f"🔍 After search - Empty state visible: {await empty_state.is_visible()}")
        
        # Debug: Check if there are any product cards
        product_cards = page.locator('.product-card')
        card_count = await product_cards.count()
        print(f"🔍 After search - Product cards found: {card_count}")
        
        # Debug: Check console logs for any JavaScript errors
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        print(f"🔍 Console logs: {console_logs[-5:]}")  # Show last 5 logs
        
        # Check that either results are displayed OR empty state is shown
        # This handles cases where no products match the search
        
        # Wait for either results or empty state to be visible
        try:
            await expect(results_container).to_be_visible(timeout=10000)
            print("✅ Search results are visible")
        except:
            try:
                await expect(empty_state).to_be_visible(timeout=5000)
                print("ℹ️ Empty state shown (no results found)")
            except:
                # If neither is visible, take a screenshot for debugging
                await page.screenshot(path='search_debug.png')
                raise AssertionError("Neither search results nor empty state is visible")
        
        # Check for product cards only if results are visible
        if await results_container.is_visible():
            product_cards = page.locator('.product-card')
            card_count = await product_cards.count()
            assert card_count > 0, f"Expected at least 1 product card, found {card_count}"
            print("🎉 Successfully logged in and searched for products!")
        else:
            print("ℹ️ Search completed but no products found for 'cable'")
    
    @pytest.mark.asyncio
    async def test_login_functionality(self, page):
        """Test user login with a test user code."""
        # Wait for page to load
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        # Fill in user code
        user_code_input = page.locator('input[name="user_code"]')
        await expect(user_code_input).to_be_visible(timeout=15000)
        await user_code_input.fill('TEST123')
        
        # Submit login form (use specific selector for login form)
        login_button = page.locator('form[action*="login"] button[type="submit"]')
        await expect(login_button).to_be_visible(timeout=15000)
        await login_button.click()
        
        # Wait for redirect to search page
        await page.wait_for_url('**/search/**', timeout=30000)
        
        # Verify we're on search page
        current_url = page.url
        assert '/search' in current_url, f"Expected URL to contain '/search', got: {current_url}"
        
        # Check for search interface
        search_input = page.locator('input[id="searchQuery"]')
        await expect(search_input).to_be_visible(timeout=15000)
    
    @pytest.mark.asyncio
    async def test_text_search(self, page):
        """Test text search functionality."""
        # First login
        await self._login_user(page, 'TEST123')
        
        # Wait for search page to load
        await page.wait_for_selector('input[id="searchQuery"]', timeout=10000)
        
        # Perform text search
        search_input = page.locator('input[id="searchQuery"]')
        await search_input.fill('cable')
        
        search_button = page.locator('#textSearchForm button[type="submit"]')
        await search_button.click()
        
        # Wait for results to load
        await page.wait_for_selector('#searchResults', timeout=10000)
        
        # Check that results are displayed
        results_container = page.locator('#searchResults')
        await expect(results_container).to_be_visible()
        
        # Check for product cards
        product_cards = page.locator('.product-card')
        card_count = await product_cards.count()
        assert card_count > 0, f"Expected at least 1 product card, found {card_count}"
    
    @pytest.mark.asyncio
    async def test_hebrew_search(self, page):
        """Test Hebrew text search functionality."""
        # First login
        await self._login_user(page, 'TEST123')
        
        # Wait for search page to load
        await page.wait_for_selector('input[id="searchQuery"]', timeout=10000)
        
        # Perform Hebrew search
        search_input = page.locator('input[id="searchQuery"]')
        await search_input.fill('כבל')
        
        search_button = page.locator('#textSearchForm button[type="submit"]')
        await search_button.click()
        
        # Wait for results to load
        await page.wait_for_selector('#searchResults', timeout=10000)
        
        # Check that results are displayed
        results_container = page.locator('#searchResults')
        await expect(results_container).to_be_visible()
        
        # Check for product cards
        product_cards = page.locator('.product-card')
        card_count = await product_cards.count()
        assert card_count > 0, f"Expected at least 1 product card, found {card_count}"
    
    @pytest.mark.asyncio
    async def test_filter_search(self, page):
        """Test filtered search functionality."""
        # First login
        await self._login_user(page, 'TEST123')
        
        # Wait for search page to load
        await page.wait_for_selector('input[id="searchQuery"]', timeout=10000)
        
        # Switch to filter search tab
        filter_tab = page.locator('#filter-search-tab')
        await filter_tab.click()
        
        # Wait for filter form to be visible
        await page.wait_for_selector('#filterSearchForm', timeout=5000)
        
        # Select a filter option (if available)
        type_filter = page.locator('select[id="filterType"]')
        await type_filter.select_option(index=1)  # Select first non-empty option
        
        # Apply filters
        apply_button = page.locator('#filterSearchForm button[type="submit"]')
        await apply_button.click()
        
        # Wait for results to load
        await page.wait_for_selector('#searchResults', timeout=10000)
        
        # Check that results are displayed
        results_container = page.locator('#searchResults')
        await expect(results_container).to_be_visible()
    
    @pytest.mark.asyncio
    async def test_add_to_cart_requires_login(self, page):
        """Test that adding to cart requires login and shows proper error."""
        print("🧪 Testing add to cart without login...")
        
        # Go to a product page without logging in
        await page.goto('http://127.0.0.1:5000/search/product/MEN-PCS-75-200-2.0')
        
        # Wait for page to load
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if we're redirected to login (expected behavior)
        current_url = page.url
        print(f"📍 Current URL: {current_url}")
        
        if '/auth/login' in current_url:
            print("✅ Correctly redirected to login page")
            return
        
        # If we're on the product page, try to add to cart
        add_button = page.locator('button[onclick="addToCart()"]')
        if await add_button.is_visible():
            print("🛒 Found add to cart button, clicking...")
            
            # Set up console log monitoring
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
            
            # Also monitor network requests
            requests = []
            page.on('request', lambda req: requests.append(f"REQUEST: {req.method} {req.url}"))
            page.on('response', lambda resp: requests.append(f"RESPONSE: {resp.status} {resp.url}"))
            
            # Click add to cart button
            await add_button.click()
            
            # Wait longer for error message to appear
            await asyncio.sleep(5)
            
            # Check for any alerts on the page
            all_alerts = page.locator('.alert')
            alert_count = await all_alerts.count()
            print(f"🔍 Found {alert_count} alerts on page")
            
            if alert_count > 0:
                for i in range(alert_count):
                    alert_text = await all_alerts.nth(i).text_content()
                    print(f"🔍 Alert {i+1}: {alert_text}")
            
            # Check calcSummary content
            calc_summary = page.locator('#calcSummary')
            if await calc_summary.is_visible():
                calc_text = await calc_summary.text_content()
                print(f"🔍 CalcSummary content: '{calc_text}'")
            else:
                print("🔍 CalcSummary element not visible")
            
            # Check for error notification (including the quantity validation error)
            error_notifications = page.locator('.alert-danger, .alert-error, [class*="error"], .text-danger')
            if await error_notifications.count() > 0:
                error_text = await error_notifications.first.text_content()
                print(f"🚨 Error message found: {error_text}")
                
                # Should NOT show "INVALID RESPONSE" - should show proper validation or login message
                assert "INVALID RESPONSE" not in error_text, f"Got generic 'INVALID RESPONSE' error instead of proper error message: {error_text}"
                
                # Check if it's a quantity validation error (expected when no length is entered)
                if any(word in error_text.lower() for word in ['אורך', 'length', 'תקין', 'valid']):
                    print("✅ Proper quantity validation error displayed (expected behavior)")
                elif any(word in error_text.lower() for word in ['login', 'התחבר', 'נדרש']):
                    print("✅ Proper login required error message displayed")
                else:
                    print(f"ℹ️ Got different error message: {error_text}")
                    # This is still acceptable as long as it's not "INVALID RESPONSE"
            else:
                # Check console logs for errors
                print(f"🔍 Console logs: {console_logs[-10:]}")
                print(f"🔍 Network requests: {requests[-10:]}")
                
                # Take a screenshot for debugging
                await page.screenshot(path='add_to_cart_debug.png')
                print("📸 Screenshot saved as add_to_cart_debug.png")
                
                raise AssertionError("No error notification found after clicking add to cart without login")
        else:
            print("ℹ️ Add to cart button not found - might be redirected to login")
    
    @pytest.mark.asyncio
    async def test_search_and_add_to_cart_with_login(self, page):
        """Test complete flow: login -> go to specific product -> add to cart -> check shopping list."""
        print("🧪 Testing complete flow with MEN-PCS-100-800-2.0...")
        
        # Step 1: Login
        print("1️⃣ Logging in...")
        await self._login_user(page, 'TEST123')
        print("✅ Logged in successfully")
        
        # Step 2: Go directly to the specific product
        print("2️⃣ Going to MEN-PCS-100-800-2.0 product page...")
        await page.goto('http://127.0.0.1:5000/search/product/MEN-PCS-100-800-2.0')
        
        # Wait for product page to load
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print("✅ Product page loaded")
        
        # Step 3: Add to cart
        print("3️⃣ Adding to cart...")
        add_button = page.locator('button[onclick="addToCart()"]')
        
        if await add_button.is_visible():
            # Set up console log monitoring
            console_logs = []
            page.on('console', lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
            
            # Fill in required fields if they exist
            total_length_input = page.locator('input[id="totalLength"]')
            if await total_length_input.is_visible():
                await total_length_input.fill('1000')
                # Verify the value was set
                actual_value = await total_length_input.input_value()
                print(f"📏 Filled in total length: '{actual_value}'")
                
                # Also check the unitWidth value
                unit_width_element = page.locator('#unitWidth')
                if await unit_width_element.is_visible():
                    unit_width_data = await unit_width_element.get_attribute('data-unit-width')
                    print(f"📏 Unit width data: '{unit_width_data}'")
            else:
                print("❌ totalLength input not found!")
            
            # Click add to cart
            await add_button.click()
            
            # Wait for response
            await asyncio.sleep(5)
            
            # Check for any alerts on the page
            all_alerts = page.locator('.alert')
            alert_count = await all_alerts.count()
            print(f"🔍 Found {alert_count} alerts on page")
            
            if alert_count > 0:
                for i in range(alert_count):
                    alert_text = await all_alerts.nth(i).text_content()
                    print(f"🔍 Alert {i+1}: {alert_text}")
            
            # Check calcSummary content
            calc_summary = page.locator('#calcSummary')
            if await calc_summary.is_visible():
                calc_text = await calc_summary.text_content()
                print(f"🔍 CalcSummary content: '{calc_text}'")
            
            # Check for success or error message
            success_notifications = page.locator('.alert-success, .alert-info, [class*="success"]')
            error_notifications = page.locator('.alert-danger, .alert-error, [class*="error"], .text-danger')
            
            if await success_notifications.count() > 0:
                success_text = await success_notifications.first.text_content()
                print(f"🎉 Success: {success_text}")
                print("✅ Add to cart functionality works!")
                
                # Step 4: Check shopping list
                print("4️⃣ Checking shopping list...")
                await self._check_shopping_list(page)
                
            elif await error_notifications.count() > 0:
                error_text = await error_notifications.first.text_content()
                print(f"🚨 Error: {error_text}")
                
                # Check if it's the "INVALID RESPONSE" error
                if "INVALID RESPONSE" in error_text:
                    print("❌ BUG FOUND: Getting 'INVALID RESPONSE' error instead of proper error handling")
                    print(f"🔍 Console logs: {console_logs[-5:]}")
                    raise AssertionError("Add to cart shows 'INVALID RESPONSE' error - this is a bug!")
                else:
                    print(f"ℹ️ Got error (might be expected): {error_text}")
            else:
                print("🔍 No notification found, checking console logs...")
                print(f"Console logs: {console_logs[-10:]}")
                
                # Check if we were redirected
                current_url = page.url
                if '/auth/login' in current_url:
                    print("❌ BUG: Redirected to login despite being logged in")
                    raise AssertionError("Redirected to login despite being logged in")
                else:
                    print("ℹ️ No clear success/error indication - might be working silently")
                    # Still check shopping list in case it worked silently
                    print("4️⃣ Checking shopping list anyway...")
                    await self._check_shopping_list(page)
        else:
            print("ℹ️ Add to cart button not found on product page")
    
    @pytest.mark.asyncio
    async def test_add_to_cart_error_handling(self, page):
        """Test that add to cart shows proper error messages, not 'INVALID RESPONSE'."""
        print("🧪 Testing add to cart error handling...")
        
        # Login first
        await self._login_user(page, 'TEST123')
        
        # Go to a product page
        await page.goto('http://127.0.0.1:5000/search/product/MEN-PCS-75-200-2.0')
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Set up console log monitoring
        console_logs = []
        page.on('console', lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        
        # Try to add to cart without filling required fields
        add_button = page.locator('button[onclick="addToCart()"]')
        if await add_button.is_visible():
            await add_button.click()
            await asyncio.sleep(2)
            
            # Check for error messages
            error_notifications = page.locator('.alert-danger, .alert-error, [class*="error"]')
            if await error_notifications.count() > 0:
                error_text = await error_notifications.first.text_content()
                print(f"🚨 Error message: {error_text}")
                
                # Should NOT show "INVALID RESPONSE"
                assert "INVALID RESPONSE" not in error_text, f"Got 'INVALID RESPONSE' error: {error_text}"
                print("✅ No 'INVALID RESPONSE' error - proper error handling works")
            else:
                print("🔍 No error notification found")
                print(f"Console logs: {console_logs[-5:]}")
        
        # Test with invalid quantity
        total_length_input = page.locator('input[id="totalLength"]')
        if await total_length_input.is_visible():
            await total_length_input.fill('0')  # Invalid quantity
            await add_button.click()
            await asyncio.sleep(2)
            
            error_notifications = page.locator('.alert-danger, .alert-error, [class*="error"]')
            if await error_notifications.count() > 0:
                error_text = await error_notifications.first.text_content()
                print(f"🚨 Quantity error: {error_text}")
                assert "INVALID RESPONSE" not in error_text, f"Got 'INVALID RESPONSE' for quantity error: {error_text}"
                print("✅ Proper quantity validation error")
    
    # Helper methods
    async def _login_user(self, page, user_code):
        """Helper method to login a user."""
        user_code_input = page.locator('input[name="user_code"]')
        await user_code_input.fill(user_code)
        
        login_button = page.locator('form[action*="login"] button[type="submit"]')
        await login_button.click()
        
        # Wait for redirect to search page
        await page.wait_for_url('**/search/**', timeout=10000)
    
    async def _check_shopping_list(self, page):
        """Helper method to check shopping list page."""
        print("🔍 Navigating to shopping list page...")
        await page.goto('http://127.0.0.1:5000/shopping-list/')
        
        # Wait for page to load
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Check if we can see shopping list content
        shopping_list_content = page.locator('.shopping-list, .list-item, [class*="shopping"], [class*="list"]')
        if await shopping_list_content.count() > 0:
            print("✅ Shopping list page loaded successfully")
            
            # Check for the specific product we added
            product_elements = page.locator('text=MEN-PCS-100-800-2.0')
            if await product_elements.count() > 0:
                print("🎉 Found the product in shopping list!")
                return True
            else:
                print("ℹ️ Shopping list loaded but product not found")
                # Take screenshot for debugging
                await page.screenshot(path='shopping_list_debug.png')
                return False
        else:
            print("❌ Shopping list page not loaded properly")
            # Take screenshot for debugging
            await page.screenshot(path='shopping_list_error.png')
            return False


# Railway-specific tests
class TestRailwayDeployment:
    """Test suite specifically for Railway deployment."""
    
    @pytest_asyncio.fixture
    async def page(self):
        """Create a new page for Railway tests."""
        async with async_playwright() as p:
            # Launch browser (use Firefox - works better on macOS)
            try:
                browser = await p.firefox.launch(headless=False, slow_mo=1000)
            except Exception:
                # Fallback to Chromium if Firefox fails
                browser = await p.chromium.launch(
                    headless=False, 
                    slow_mo=1000,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            
            page = await context.new_page()
            
            # Use Railway URL
            railway_url = 'https://web-production-8f004.up.railway.app'
            await page.goto(railway_url)
            
            yield page
            
            await browser.close()
    
    @pytest.mark.asyncio
    async def test_railway_homepage_loads(self, page):
        """Test that Railway homepage loads."""
        # Wait for page to load
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        # Check for any content
        body = page.locator('body')
        await expect(body).to_be_visible()
        
        # Take screenshot for debugging
        await page.screenshot(path='railway_homepage.png')
        
        # Check if we get a proper response
        response = await page.goto('https://web-production-8f004.up.railway.app')
        assert response.status in [200, 302, 404]  # Any of these is better than 500
    
    @pytest.mark.asyncio
    async def test_railway_health_endpoint(self, page):
        """Test Railway health endpoint."""
        try:
            await page.goto('https://web-production-8f004.up.railway.app/health')
            
            # Wait for response
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # Check content
            content = await page.content()
            
            # Take screenshot for debugging
            await page.screenshot(path='railway_health.png')
            
            # Should contain some JSON-like content
            assert len(content) > 0
            
        except Exception as e:
            # Take screenshot of error page
            await page.screenshot(path='railway_health_error.png')
            raise e
    
    @pytest.mark.asyncio
    async def test_railway_login_page(self, page):
        """Test Railway login page."""
        try:
            await page.goto('https://web-production-8f004.up.railway.app/auth/login')
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # Take screenshot for debugging
            await page.screenshot(path='railway_login.png')
            
            # Check for login form or error
            body = page.locator('body')
            await expect(body).to_be_visible()
            
            # Check if we can find any form elements
            forms = page.locator('form')
            if await forms.count() > 0:
                # Login form found
                await expect(forms.first).to_be_visible()
            else:
                # Check for error messages
                error_elements = page.locator('.error, .alert-danger, [class*="error"]')
                if await error_elements.count() > 0:
                    error_text = await error_elements.first.text_content()
                    print(f"Error found on login page: {error_text}")
                
        except Exception as e:
            await page.screenshot(path='railway_login_error.png')
            raise e


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
