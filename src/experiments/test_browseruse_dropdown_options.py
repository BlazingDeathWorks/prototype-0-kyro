from browser_use import Agent, ChatGoogle
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import asyncio
import time

load_dotenv()

# Keep commented code for reference
# ---------------------------------
# agent = Agent(
#     task="""Goto this url: https://jobs.lever.co/hermeus/1ce52371-c210-49b5-9a2b-5af6706137bc/apply, 
#     then use extract_structured_data: all dropdown elements and their options""",
#     llm=ChatGoogle(model="gemini-2.5-flash"),
# )
# agent = Agent(
#     task="""Goto this url: https://jobs.ashbyhq.com/exegy/6ae2d836-21a3-4132-bd85-722177ab5cf5/application,
#     then use extract_structured_data: all radio_checkbox questions and their options""",
#     llm=ChatGoogle(model="gemini-2.5-flash"),
# )
# agent = Agent(
#     task="""
#     Goto this url: https://job-boards.greenhouse.io/radiant/jobs/4606581005,
#     then use extract_structured_data: all dropdown elements and their options
#     """,
#     llm=ChatGoogle(model="gemini-2.5-flash"),
# )
# ---------------------------------

async def main():
    # Launch Playwright browser with CDP enabled
    playwright_instance = await async_playwright().start()
    chromium = await playwright_instance.chromium.launch(
        headless=False,
        args=['--remote-debugging-port=9222']  # Enable CDP on port 9222
    )
    
    context = await chromium.new_context(viewport={'width': 1280, 'height': 800})
    page = await context.new_page()
    
    print("Browser launched! Navigate manually to where you want to test.")
    print("Press Enter when you're ready to execute the browser-use agent...")
    
    # Wait for user input
    input("Press Enter to continue...")
    
    # Get the current URL for the agent
    current_url = page.url
    print(f"Current URL: {current_url}")
    
    # Close the Playwright browser to allow browser-use to connect via CDP
    await context.close()
    await chromium.close()
    await playwright_instance.stop()
    
    # Now create browser-use agent that connects to the existing browser via CDP
    agent = Agent(
        task=f"""
        You are already on the page: {current_url}
        Use extract_structured_data to extract all dropdown elements and their options from the current page.
        Print out all the dropdown data in a structured format.
        """,
        llm=ChatGoogle(model="gemini-2.5-flash"),
        browser_config={
            "cdp_url": "http://localhost:9222",  # Connect to CDP
            "headless": False
        }
    )
    
    print("Executing browser-use agent...")
    result = agent.run_sync()
    print("Agent execution completed!")
    return result

def run_with_manual_navigation():
    """
    Alternative synchronous version that keeps the browser open for manual navigation
    """
    # Launch Playwright browser with CDP enabled
    playwright_instance = sync_playwright().start()
    browser = playwright_instance.chromium.launch(
        headless=False,
        args=['--remote-debugging-port=9222']
    )
    
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    
    print("Browser launched! Navigate manually to where you want to test.")
    print("The browser is running with CDP enabled on port 9222")
    print("Press Enter when you're ready to execute the browser-use agent...")
    
    # Wait for user input
    input("Press Enter to continue...")
    
    # Get the current URL
    current_url = page.url
    print(f"Current URL: {current_url}")
    
    print("Keeping browser open and executing browser-use agent...")
    
    # Create browser-use agent that connects via CDP
    agent = Agent(
        task="""
        Connect to the existing browser session and work with the current page.
        Use extract_structured_data to extract all dropdown elements and their options from the current page.
        Print out all the dropdown data in a structured format.
        """,
        llm=ChatGoogle(model="gemini-2.5-flash"),
        browser_config={
            "cdp_url": "http://localhost:9222",
            "headless": False
        }
    )
    
    try:
        # Use asyncio.create_task to run the async agent in the sync context
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()  # Allow nested event loops
        
        # Run the agent asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(agent.run())
        loop.close()
        
        print("Agent execution completed!")
    except Exception as e:
        print(f"Error during agent execution: {e}")
    finally:
        # Clean up
        print("Closing browser...")
        context.close()
        browser.close()
        playwright_instance.stop()

if __name__ == "__main__":
    # Use the synchronous version for easier manual testing
    run_with_manual_navigation()
    
    # Uncomment below to use the async version instead
    # asyncio.run(main())