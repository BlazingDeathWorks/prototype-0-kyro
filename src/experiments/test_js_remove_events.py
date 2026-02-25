import os
import time
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import agentql

# Load environment variables
load_dotenv()

# Configure AgentQL
agentql.configure(api_key=os.getenv("AGENTQL_API_KEY"))

# URL to test
URL = "https://job-boards.greenhouse.io/robinhood/jobs/7239236"
URL = "https://jobs.ashbyhq.com/cohere/25cc6633-614a-45e0-8632-ffd4a2475c9b/application"
URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"

# AgentQL query for dropdown elements
DROPDOWN_QUERY = """
{
    dropdown_element_trigger_buttons(All dropdown trigger button elements on the page)[]
}
"""

def main():
    with sync_playwright() as playwright:
        try:
            # Launch browser
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Listen to console messages
            def handle_console_msg(msg):
                print(f"Browser console: {msg.text}")
            page.on("console", handle_console_msg)
            
            # Wrap page with AgentQL
            page = agentql.wrap(page)
            
            # Navigate to the URL
            print(f"Navigating to: {URL}")
            page.goto(URL)
            
            # Wait for page to load
            page.wait_for_page_ready_state()
            time.sleep(1)
            
            # Block blur and focusout events globally before interacting with dropdowns
            print("Blocking blur and focusout events...")
            block_events_js = """
            (function() { 
              function cancel(e) { 
                e.stopImmediatePropagation(); 
                e.preventDefault(); // optional: comment this out if you still want native behavior 
                console.log("Blocked", e.type, "on", e.target); 
              } 
            
              // Capture phase = true, so this runs *before* site's handlers 
              window.addEventListener("blur", cancel, true); 
              window.addEventListener("focusout", cancel, true); 
              document.addEventListener("blur", cancel, true); 
              document.addEventListener("focusout", cancel, true); 
            
              console.log("All blur/focusout events are now being intercepted."); 
            })();
            """
            page.evaluate(block_events_js)
            print("Event blocking script executed")
            
            print("Querying for dropdown elements...")
            
            # Query for dropdown elements using AgentQL
            dropdown_data = page.query_elements(DROPDOWN_QUERY)
            
            if dropdown_data and hasattr(dropdown_data, 'dropdown_element_trigger_buttons'):
                dropdowns = dropdown_data.dropdown_element_trigger_buttons
                print(f"Found {len(dropdowns)} dropdown elements")
                
                # Since we've blocked blur/focusout events globally, we can skip individual element processing
                print("Blur/focusout events are already blocked globally - skipping individual dropdown processing")
            else:
                print("No dropdown elements found")
            
            print("\nNow clicking dropdowns in reverse order...")
            # Iterate backwards through the dropdown list and click each
            for i in range(len(dropdowns) - 1, -1, -1):
                dropdown = dropdowns[i]
                tf623_id = dropdown.get_attribute("tf623_id")
                print(f"Clicking dropdown {i+1} (tf623_id: {tf623_id})")
                
                try:
                    # Get the locator and click
                    locator = page.locator(f"[tf623_id='{tf623_id}']")
                    locator.click()
                    print(f"Successfully clicked dropdown {i+1}")
                    time.sleep(0.5)  # Small delay between clicks
                except Exception as e:
                    print(f"Error clicking dropdown {i+1}: {e}")
            
            print("\nRunning AgentQL query to extract application questions...")
            # Use query_data with APPLICATION_FORM_QUESTIONS_PROMPT like in one_pager.py
            APPLICATION_FORM_QUESTIONS_PROMPT = """
            {
              form {
                dropdown_elements [] {
                  question
                  options []
                }
              }
            }
            """
            
            query_result = page.query_data(APPLICATION_FORM_QUESTIONS_PROMPT, mode="standard")
            
            print("\nAgentQL Query Result:")
            print(json.dumps(query_result, indent=2))
            
            print("\nScript completed. Browser will remain open for inspection.")
            # Keep browser open for 10 seconds
            time.sleep(10)
            
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()