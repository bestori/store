#!/usr/bin/env python3
"""
Simple Playwright test to verify the app works.
"""

import asyncio
from playwright.async_api import async_playwright


async def test_app():
    """Simple test to verify the app loads."""
    browser = None
    try:
        async with async_playwright() as p:
            print("🚀 Launching browser...")
            
            # Try Firefox instead of Chromium (often works better on macOS)
            try:
                browser = await p.firefox.launch(headless=False, slow_mo=1000)
                print("✅ Firefox launched successfully!")
            except Exception as firefox_error:
                print(f"❌ Firefox failed: {firefox_error}")
                print("🔄 Trying Chromium with different settings...")
                
                # Fallback to Chromium with minimal args
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=1000,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                print("✅ Chromium launched successfully!")
            
            print("✅ Browser launched successfully!")
            
            # Create context and page
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            # Try different ports to find your Flask app
            ports_to_try = [5001, 5000, 8000, 3000]
            
            for port in ports_to_try:
                url = f'http://localhost:{port}'
                print(f"🌐 Trying {url}...")
                
                try:
                    await page.goto(url, timeout=10000)
                    print(f"✅ Successfully connected to {url}!")
                    break
                except Exception as e:
                    print(f"❌ {url} failed: {e}")
                    if port == ports_to_try[-1]:  # Last port
                        raise e
                    continue
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            print("✅ Page loaded successfully!")
            
            # Take a screenshot
            await page.screenshot(path='app_screenshot.png')
            print("📸 Screenshot saved as app_screenshot.png")
            
            # Check if we can see the page title
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Wait a bit so you can see the browser
            print("⏳ Waiting 5 seconds so you can see the browser...")
            await asyncio.sleep(5)
            
            print("🎉 Test completed successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        
        # Try to take screenshot of error if browser is still alive
        try:
            if browser:
                page = await browser.new_page()
                await page.screenshot(path='error_screenshot.png')
                print("📸 Error screenshot saved as error_screenshot.png")
        except Exception as screenshot_error:
            print(f"❌ Could not take error screenshot: {screenshot_error}")
    finally:
        # Clean up browser
        try:
            if browser:
                await browser.close()
                print("🧹 Browser closed")
        except Exception as close_error:
            print(f"❌ Error closing browser: {close_error}")


if __name__ == "__main__":
    print("🚀 Starting simple Playwright test...")
    asyncio.run(test_app())