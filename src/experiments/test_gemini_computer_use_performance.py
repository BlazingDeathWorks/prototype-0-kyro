
import time
from playwright.sync_api import sync_playwright

from google import genai
from google.genai import types
from google.genai.types import Content, Part
import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Constants for screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900

excluded_functions = [
  "open_web_browser", 
  "go_back", 
  "go_forward", 
  "search", 
  "navigate", 
  "hover_at", 
  "key_combination", 
  "drag_and_drop"
]

def denormalize_x(x: int, screen_width: int) -> int:
    """Convert normalized x coordinate (0-1000) to actual pixel coordinate."""
    return int(x / 1000 * screen_width)

def denormalize_y(y: int, screen_height: int) -> int:
    """Convert normalized y coordinate (0-1000) to actual pixel coordinate."""
    return int(y / 1000 * screen_height)

def execute_function_calls(candidate, page, screen_width, screen_height):
    results = []
    function_calls = []
    for part in candidate.content.parts:
        if part.function_call:
            function_calls.append(part.function_call)

    for function_call in function_calls:
        action_result = {}
        fname = function_call.name
        args = function_call.args
        print(f"  -> Executing: {fname}")

        try:
            if fname == "click_at":
                actual_x = denormalize_x(args["x"], screen_width)
                actual_y = denormalize_y(args["y"], screen_height)
                print(f"    Clicking at coordinates: ({actual_x}, {actual_y})")
                page.mouse.click(actual_x, actual_y)
            elif fname == "type_text_at":
                actual_x = denormalize_x(args["x"], screen_width)
                actual_y = denormalize_y(args["y"], screen_height)
                text = args["text"]
                press_enter = args.get("press_enter", False)
                
                print(f"    Typing '{text}' at coordinates: ({actual_x}, {actual_y})")
                page.mouse.click(actual_x, actual_y)
                # Simple clear (Command+A, Backspace for Mac)
                page.keyboard.press("Meta+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(text)
                if press_enter:
                    page.keyboard.press("Enter")
            elif fname == "scroll_document":
              # Handle scrolling if the model tries to scroll
              direction = args.get("direction", "down")
              if direction == "down":
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
              elif direction == "up":
                page.evaluate("window.scrollTo(0, 0)")
              else:
                print("Warning: No implementation for scrolling horizontally")
            elif fname == "scroll_at":
              actual_x = denormalize_x(args["x"], screen_width)
              actual_y = denormalize_y(args["y"], screen_height)
              direction = args.get("direction", "down")
              magnitude = args.get("magnitude", 400)
              if direction == "down":
                page.mouse.wheel(0, magnitude)
              elif direction == "up":
                page.mouse.wheel(0, -magnitude)
              else:
                print("Warning: No implementation for scrolling horizontally")
            else:
                print(f"Warning: Unimplemented or custom function {fname}")

            # Wait for potential navigations/renders
            page.wait_for_load_state(timeout=5000)
            time.sleep(1)

        except Exception as e:
            print(f"Error executing {fname}: {e}")
            action_result = {"error": str(e)}

        results.append((fname, action_result))

    return results


def get_function_responses(page, results):
    screenshot_bytes = page.screenshot(type="png")
    current_url = page.url
    function_responses = []
    for name, result in results:
        response_data = {"url": current_url}
        response_data.update(result)
        function_responses.append(
            types.FunctionResponse(
                name=name,
                response=response_data,
                parts=[types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png",
                            data=screenshot_bytes))
                ]
            )
        )
    return function_responses

# Setup Playwright
print("Initializing browser...")
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=False)
context = browser.new_context(viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT})
page = context.new_page()

# Define helper functions. Copy/paste from steps 3 and 4
# def denormalize_x(...)
# def denormalize_y(...)
# def execute_function_calls(...)
# def get_function_responses(...)

URL = "https://my7elevenhr.wd12.myworkdayjobs.com/Careers/job/SSC-7Next-Irving/Software-Developer-Intern_R25_0000008848"
URL = "https://gevernova.wd5.myworkdayjobs.com/en-US/only_confidential_executive_recruiting/job/Niskayuna/Software-Engineering-Intern---Summer-2026_R5022361-1"

try:
    # Go to Workday job application page
    print("Navigating to Workday job application page...")
    page.goto(URL)
    
    # Wait for the page to load completely
    time.sleep(3)
    print("Page loaded")
    
    # Wait for user input to allow manual navigation to desired page
    print("\n" + "="*80)
    print("WORKDAY GEMINI COMPUTER USE PERFORMANCE TEST")
    print("="*80)
    print("Navigate to the page you want to test form extraction on.")
    print("Press ENTER when you're ready to start the Gemini Computer Use agent...")
    input()
    
    print("\n🚀 Starting Gemini Computer Use agent for form extraction...")


    # Initialize history with comprehensive form extraction prompt
    initial_screenshot = page.screenshot(type="png")
    SYSTEM_PROMPT = """
    # Role
    You are a helpful browser agent that helps users automatically apply to job applications on the Workday platform.
    Your task is to setup the current page for job application automation by ensuring that all sections fields are visible and accessible.

    # Instructions
    - Look for a work experience section on the page
        - If a work experience section exists, count the current number of work experience containers/sections on the page
        - If there are fewer than 3 work experience containers, use the "Add" button to add more until there are exactly 3 work experience containers
    - Look for an education experience section on the page
        - If an education experience section exists, count the current number of education experience containers/sections on the page  
        - If there are fewer than 1 education experience container, use the "Add" button to add one until there is exactly 1 education experience container
    - Look for a website section on the page
        - If a website section exists, count the current number of website fields available
        - If there are fewer than 2 website fields and the website section is present, use the "Add" button to add more until there are exactly 2 website fields
    """

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.1,
        top_p=0.3,
        tools=[types.Tool(computer_use=types.ComputerUse(
            environment=types.Environment.ENVIRONMENT_BROWSER,
            excluded_predefined_functions=excluded_functions
        ))],
        thinking_config=types.ThinkingConfig(include_thoughts=True),
    )
    
    print(f"Goal: Extract and classify all form elements on the current Workday page")

    contents = [
        Content(role="user", parts=[
            Part(text="Setup job application automation on this page"),
            Part.from_bytes(data=initial_screenshot, mime_type='image/png')
        ])
    ]

    # Agent Loop with increased turn limit for comprehensive analysis
    turn_limit = 10
    start_time = time.time()
    
    for i in range(turn_limit):
        print(f"\n--- Turn {i+1} ---")
        print("Thinking...")
        
        turn_start_time = time.time()
        response = client.models.generate_content(
            model='gemini-2.5-computer-use-preview-10-2025',
            contents=contents,
            config=config,
        )
        turn_end_time = time.time()
        turn_duration = turn_end_time - turn_start_time
        
        print(f"⏱️ Turn {i+1} response time: {turn_duration:.2f} seconds")

        candidate = response.candidates[0]
        contents.append(candidate.content)

        has_function_calls = any(part.function_call for part in candidate.content.parts)
        if not has_function_calls:
            text_response = " ".join([part.text for part in candidate.content.parts if part.text])
            print("Agent finished:", text_response)
            break

        print("Executing actions...")
        action_start_time = time.time()
        results = execute_function_calls(candidate, page, SCREEN_WIDTH, SCREEN_HEIGHT)
        action_end_time = time.time()
        action_duration = action_end_time - action_start_time
        
        print(f"⏱️ Turn {i+1} action execution time: {action_duration:.2f} seconds")

        print("Capturing state...")
        function_responses = get_function_responses(page, results)

        contents.append(
            Content(role="user", parts=[Part(function_response=fr) for fr in function_responses])
        )
    
    total_time = time.time() - start_time
    print(f"\n🏁 PERFORMANCE SUMMARY:")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Total turns completed: {i+1}")
    print(f"Average time per turn: {total_time/(i+1):.2f} seconds")

finally:
    # Cleanup
    print("\nClosing browser in 30 seconds...")
    time.sleep(30)
    browser.close()
    playwright.stop()