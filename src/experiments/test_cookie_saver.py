import os
import json
import sys
from playwright.sync_api import sync_playwright

# Determine paths
# __file__ = src/experiments/test_cookie_saver.py
# root = project-kyro
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COOKIES_DIR = os.path.join(PROJECT_ROOT, "cookies")
COOKIES_FILE = os.path.join(COOKIES_DIR, "cookies.json")

# Configuration
URL = "https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal/job/Sunnyvale%2C-CA/XMLNAME-2026-Summer-Intern--Software-Engineering-II--Sunnyvale-_R-2354882/apply/applyManually"

def main():
    # Ensure cookies directory exists
    if not os.path.exists(COOKIES_DIR):
        os.makedirs(COOKIES_DIR)
        print(f"Created cookies directory at: {COOKIES_DIR}")
    else:
        print(f"Cookies directory exists at: {COOKIES_DIR}")

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)
        
        # Create context
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900}
        )
        
        # Try to load existing cookies
        if os.path.exists(COOKIES_FILE):
            print(f"\nFound existing cookies file at: {COOKIES_FILE}")
            try:
                with open(COOKIES_FILE, 'r') as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)
                    print(f"✅ Successfully loaded {len(cookies)} cookies")
            except Exception as e:
                print(f"⚠️ Failed to load existing cookies: {e}")
        else:
            print("\nNo existing cookies found. Starting fresh session.")
        
        page = context.new_page()
        
        print(f"\nNavigating to: {URL}")
        try:
            page.goto(URL)
        except Exception as e:
            print(f"Error navigating to URL: {e}")
        
        print("\n" + "="*60)
        print("INSTRUCTIONS:")
        print("1. Interact with the browser window to sign in or navigate.")
        print("2. When you are signed in and ready to save cookies...")
        print("3. Come back here and PRESS ENTER.")
        print("="*60 + "\n")
        
        input("Press ENTER to save cookies to disk...")
        
        # Get and save cookies
        cookies = context.cookies()
        try:
            with open(COOKIES_FILE, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"\n✅ Successfully saved {len(cookies)} cookies to:")
            print(f"   {COOKIES_FILE}")
        except Exception as e:
            print(f"\n❌ Failed to save cookies: {e}")
            
        print("\nClosing browser...")
        browser.close()

if __name__ == "__main__":
    main()
