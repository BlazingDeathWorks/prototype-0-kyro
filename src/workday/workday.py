import asyncio
import os
import random
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from playwright_account import fill_form_with_playwright

load_dotenv()

url = "https://dexcom.wd1.myworkdayjobs.com/en-US/Dexcom/job/Remote---United-States/Intern-I---Software-Engineering_JR115298/apply/applyManually"

SESSION_ID = "apply_session"

async def fetch_and_save_html(target_url: str, output_path: str = "output.txt") -> None:
    """Navigate to the /apply page, click 'Apply Manually' via js_code using the same session, wait ~10 seconds, then fetch all <a> elements and save to a file."""
    # Force the /apply variant of the URL
    apply_url = target_url if target_url.rstrip("/").endswith("/apply/applyManually") else f"{target_url.rstrip('/')}/apply/applyManually"

    browser_conf = BrowserConfig(
        headless=False, 
        verbose=True,
    )
    
    # Use the browser state if it exists
    if os.path.exists("browser_state.json"):
        browser_conf.storage_state = "browser_state.json"
        print("Using browser state from browser_state.json")

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        test_run_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id=SESSION_ID,
            process_iframes=True,
        )

        result = await crawler.arun(url=apply_url, config=test_run_conf)
        print(result.html)
            
        time.sleep(10) # KEEP THIS LINE OF CODE AT THE END OF OUR CODE


def main() -> None:
    try:
        # Check if browser_state.json exists, if not create a new account
        if not os.path.exists("browser_state.json"):
            print("No browser state found. Creating a new account...")
            asyncio.run(fill_form_with_playwright())
            print("Account creation completed. Browser state saved.")
        else:
            print("Using existing browser state from browser_state.json")
        
        # Now use the browser state with crawl4ai
        asyncio.run(fetch_and_save_html(url, "output.txt"))
        print("Saved final page state after login automation to output.txt")
        
    except Exception as e:
        # Provide a helpful hint for common environment/setup issues
        hint = (
            "If this error relates to browser setup, try running 'playwright install' "
            "or 'crawl4ai-setup' to install the required browsers, then retry."
        )
        print(f"Error: {e}\n{hint}")


if __name__ == "__main__":
    main()
