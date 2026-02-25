import os
import time
import json
import re
import pathlib
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from google import genai
from google.genai import types
from google.genai.types import Content, Part
from PIL import Image
from pydantic import BaseModel, RootModel, Field
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / 'src'))
from models import JobApplicationForm


load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900


SYSTEM_PROMPT = """
STEP 1: Use the extract tool with this exact query to extract job application form data:


IMPORTANT ELEMENT CLASSIFICATION DEFINITIONS:
- INPUT ELEMENTS: Blank rectangular boxes with nothing else inside them. These are basic text input fields or text areas.
- DROPDOWN ELEMENTS: Rectangular boxes that have visual indicators differentiating them from basic input boxes:
    * Official dropdowns: Have a triangle/arrow icon on the right side
    * Semi-dropdowns: Have a filter icon or other visual indicator inside the box
    * Both types should be classified as dropdown elements and their questions as dropdown_questions


{
    form {
    application_form_questions(All job application form fields: text inputs, textarea, file uploads, dropdowns, buttons, and radio/checkbox groups) {
        application_page_title(The heading that describes the current application page contents)
        all_application_form_questions(Combined group from input_text_questions, dropdown_questions, radio_checkbox_questions, resume_questions) []
        input_text_questions(the questions that are tied to the application form text input or text area elements - these are BLANK rectangular boxes with NO visual indicators) []
        dropdown_questions(the questions tied to dropdown elements - these have visual indicators like triangles, arrows, or filter icons that differentiate them from basic input boxes) []
        radio_checkbox_questions(the questions tied to radio or checkbox button groups) []
        resume_questions(questions about uploading resume or cover letter) [] {
        name
        buttons(buttons associated to the question) []
        }
    }
    }
}


STEP 2: After extracting the data, take a screenshot of the current page to visually verify the classification.


STEP 3: Analyze the screenshot to correct any classification mistakes by examining each form element visually:

For each question in the extracted data, look at the actual visual appearance of its associated form element in the screenshot:
- If you see a dropdown element (has triangle/arrow icon or filter icon) but it was classified as input_text_questions or radio_checkbox_questions, move it to dropdown_questions
- If you see a basic input text field (blank rectangular box with no visual indicators) but it was classified as dropdown_questions or radio_checkbox_questions, move it to input_text_questions  
- If you see radio buttons or checkboxes but they were classified as input_text_questions or dropdown_questions, move them to radio_checkbox_questions

Pay special attention to elements that may have been misclassified entirely (e.g., dropdown elements incorrectly classified as radio_checkbox_questions). Make corrections based on what you actually see in the screenshot, not what the initial extraction suggested.

After making corrections:
- Move incorrectly classified questions between the appropriate categories (input_text_questions, dropdown_questions, radio_checkbox_questions)
- Update the all_application_form_questions list to reflect the corrected classifications


STEP 4: Return the final corrected structured output and use the done tool to finish the task.

Return ONLY a JSON object that matches this structure:
{
  "form": {
    "application_page_title": string,
    "all_application_form_questions": string[],
    "input_text_questions": string[],
    "dropdown_questions": string[],
    "radio_checkbox_questions": string[],
    "resume_questions": [{"name": string, "buttons": string[]}]
  }
}
"""



def capture_clean_fullpage_screenshot(page, path, original_size_width=SCREEN_WIDTH, original_size_height=SCREEN_HEIGHT, max_height=8000):
    """
    Attempt to capture a seam-free full-page screenshot by temporarily enlarging
    the viewport to the document's scroll height, then taking a single capture.
    Falls back to Playwright's full_page capture if needed.

    Args:
        page: Playwright Page instance
        path: Output file path for the PNG
        original_size_width: Original viewport width to restore after
        original_size_height: Original viewport height to restore after
        max_height: Upper cap for temporary viewport height to avoid extremes
    """
    try:
        page.evaluate("window.scrollTo(0, 0)")
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        # Use at least original width; allow wider if content requires
        target_width = max(int(original_size_width), int(scroll_width))
        target_height = min(int(scroll_height), int(max_height))

        # Temporarily expand viewport to fit full content height
        page.set_viewport_size({"width": target_width, "height": target_height})
        time.sleep(0.3)
        page.screenshot(type="png", path=str(path), full_page=False)
    except Exception:
        # Fallback to standard full_page capture
        page.screenshot(type="png", path=str(path), full_page=True)
    finally:
        # Restore original viewport and scroll to top
        try:
            page.set_viewport_size({"width": int(original_size_width), "height": int(original_size_height)})
            page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass


def main():
    print("Initializing browser...")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT})
    page = context.new_page()

    # Default Workday job application URL (can be changed as needed)
    URL = "https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal/job/Sunnyvale%2C-CA/XMLNAME-2026-Summer-Intern--Software-Engineering-II--Sunnyvale-_R-2354882/apply/applyManually"

    def input_queue():
        print("\n" + "="*80)
        print("INPUT QUEUE — Navigate before starting extraction")
        print("="*80)
        print("Commands:")
        print("  - Press ENTER to start extraction on current page")
        print("  - goto <url>   → Navigate to a new URL")
        print("  - back | forward | reload")
        print("  - url          → Show current URL")
        print("  - screenshot   → Save a PNG in snapshots/")
        print("  - wait <sec>   → Sleep for given seconds")
        print("  - q | quit     → Exit without extracting")
        while True:
            cmd = input("\nCommand: ").strip()
            if cmd == "" or cmd.lower() in {"start", "run", "go"}:
                return True
            if cmd.lower() in {"q", "quit"}:
                return False
            if cmd.lower().startswith("goto "):
                url = cmd[5:].strip()
                try:
                    page.goto(url)
                    time.sleep(2)
                    print(f"✅ Navigated to: {page.url}")
                except Exception as e:
                    print(f"❌ Navigation error: {e}")
                continue
            if cmd.lower() in {"back", "b"}:
                page.go_back()
                time.sleep(1.5)
                print(f"⬅️ Back → {page.url}")
                continue
            if cmd.lower() in {"forward", "f"}:
                page.go_forward()
                time.sleep(1.5)
                print(f"➡️ Forward → {page.url}")
                continue
            if cmd.lower() in {"reload", "r"}:
                page.reload()
                time.sleep(2)
                print(f"🔄 Reloaded → {page.url}")
                continue
            if cmd.lower() == "url":
                print(f"🌐 Current URL: {page.url}")
                continue
            if cmd.lower().startswith("wait "):
                try:
                    secs = float(cmd.split(" ", 1)[1])
                    print(f"⏳ Waiting {secs} seconds...")
                    time.sleep(secs)
                except Exception:
                    print("⚠️ Usage: wait <seconds>")
                continue
            if cmd.lower() == "screenshot":
                snapshots_dir = ROOT / 'snapshots'
                os.makedirs(snapshots_dir, exist_ok=True)
                filename = time.strftime("gemini_image_analysis_%Y%m%d_%H%M%S.png")
                path = snapshots_dir / filename
                capture_clean_fullpage_screenshot(page, path, SCREEN_WIDTH, SCREEN_HEIGHT)
                print(f"📸 Saved screenshot: {path}")
                continue
            print("⚠️ Unknown command. Try: goto <url>, back, forward, reload, url, screenshot, wait <sec>, ENTER, or quit")

    try:
        print(f"Navigating to Workday job application page...")
        page.goto(URL)
        time.sleep(3)
        print("Page loaded")

        print("\n" + "="*80)
        print("WORKDAY GEMINI IMAGE ANALYSIS TEST")
        print("="*80)
        print("Use the input queue to reach the exact page (e.g., Experience/My Information).")
        proceed = input_queue()
        if not proceed:
            print("Exiting without extraction.")
            return

        # Capture full-page screenshot for multimodal analysis and save to snapshots/
        snapshots_dir = ROOT / 'snapshots'
        os.makedirs(snapshots_dir, exist_ok=True)
        screenshot_filename = time.strftime("gemini_fullpage_%Y%m%d_%H%M%S.png")
        screenshot_path = snapshots_dir / screenshot_filename
        capture_clean_fullpage_screenshot(page, screenshot_path, SCREEN_WIDTH, SCREEN_HEIGHT)
        with open(screenshot_path, 'rb') as fh:
            screenshot = fh.read()
        print(f"📸 Full-page screenshot saved: {screenshot_path}")

        # Prepare content for Gemini (system prompt + screenshot)
        contents = [
            Content(role="user", parts=[
                Part(text="Extract and correct job application form questions as specified. Return ONLY JSON."),
                Part.from_bytes(data=screenshot, mime_type='image/png')
            ])
        ]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            top_p=0.1,
            thinking_config=types.ThinkingConfig(include_thoughts=False),
            response_mime_type='application/json'
        )

        print("\n🚀 Sending full-page screenshot to Gemini for image-verified extraction...")
        start = time.time()
        response = client.models.generate_content(
            model='gemini-3-pro-preview',
            contents=contents,
            config=config,
        )
        duration = time.time() - start
        print(f"⏱️ Response time: {duration:.2f} seconds")

        # Attempt to report token usage from the API response
        try:
            usage = getattr(response, 'usage_metadata', None) or getattr(response, 'usage', None)
            if usage:
                # Support multiple possible field names across library versions
                input_tokens = getattr(usage, 'input_token_count', None) or getattr(usage, 'prompt_token_count', None) or getattr(usage, 'promptTokenCount', None)
                output_tokens = getattr(usage, 'output_token_count', None) or getattr(usage, 'candidates_token_count', None) or getattr(usage, 'candidatesTokenCount', None)
                total_tokens = getattr(usage, 'total_token_count', None) or getattr(usage, 'totalTokenCount', None)
                print("🔢 Token usage (reported by API):")
                if input_tokens is not None:
                    print(f"- Input tokens: {input_tokens}")
                if output_tokens is not None:
                    print(f"- Output tokens: {output_tokens}")
                if total_tokens is not None:
                    print(f"- Total tokens: {total_tokens}")
            else:
                print("⚠️ Token usage metadata not provided by the API response.")
        except Exception as e:
            print(f"⚠️ Unable to read token usage metadata: {e}")

        # Keep assistant message in history for verification pass
        candidate = response.candidates[0] if (response and response.candidates) else None
        if candidate and candidate.content:
            contents.append(candidate.content)

        # Collect JSON text from first pass response
        raw_text_parts = []
        if candidate and candidate.content.parts:
            for part in candidate.content.parts:
                if part.text:
                    raw_text_parts.append(part.text)
        raw_json_text = "\n".join(raw_text_parts).strip()

        if not raw_json_text:
            raise RuntimeError("No JSON output received from Gemini (extraction pass).")

        # Parse first pass JSON
        try:
            initial_parsed = json.loads(raw_json_text)
        except json.JSONDecodeError as e:
            print("⚠️ First pass did not return valid JSON. Raw output:")
            print(raw_json_text)
            raise e

        # Optional: try to validate first pass to inspect quality
        initial_result = None
        try:
            initial_result = JobApplicationForm.model_validate(initial_parsed)
            print("\n📋 Initial JobApplicationForm (validated):")
            print(json.dumps(initial_result.model_dump(), indent=2, ensure_ascii=False))
        except Exception:
            print("⚠️ First pass JSON did not match JobApplicationForm schema. Verification step is disabled; using first pass output.")

        # Final output without verification: use first pass results
        if initial_result is not None:
            print("\n✅ Final JobApplicationForm (validated):")
            print(json.dumps(initial_result.model_dump(), indent=2, ensure_ascii=False))
        else:
            print("⚠️ Final JSON does not match JobApplicationForm schema. Parsed JSON:")
            print(json.dumps(initial_parsed, indent=2, ensure_ascii=False))
            raise ValueError("First pass JSON did not match JobApplicationForm schema and verification is disabled.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()