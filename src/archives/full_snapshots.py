import os
import argparse
from playwright.sync_api import sync_playwright

def take_screenshot(url, output_path=None):
    """Take a screenshot of the entire webpage at the given URL.
    
    Args:
        url (str): The URL of the webpage to screenshot
        output_path (str, optional): Path where the screenshot should be saved.
                                     Defaults to 'snapshots/screenshot.png'.
    """
    # Set default output path if not provided
    if output_path is None:
        # Ensure snapshots directory exists
        os.makedirs('snapshots', exist_ok=True)
        output_path = 'snapshots/screenshot.png'
    else:
        # Ensure the directory for the output path exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Taking screenshot of {url}")
    print(f"Saving to {output_path}")
    
    with sync_playwright() as playwright:
        # Launch browser (headless by default)
        browser = playwright.chromium.launch()
        
        # Create a new page
        page = browser.new_page()
        
        # Navigate to the URL
        page.goto(url, wait_until="networkidle")
        
        # Take a screenshot of the full page
        page.screenshot(path=output_path, full_page=True)
        
        # Close the browser
        browser.close()
    
    print(f"Screenshot saved to {output_path}")
    return output_path

def main():
    # Take the screenshot
    URL = "https://jobs.ashbyhq.com/notion/4ebcc11d-4d32-4cef-9001-190c0156188f/application"
    take_screenshot(URL)

if __name__ == "__main__":
    main()