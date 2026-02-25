import os
import sys
import io
import time
from typing import Tuple

from PIL import Image
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import Content, Part
import agentql


DEFAULT_URL = "https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal/job/Sunnyvale%2C-CA/XMLNAME-2026-Summer-Intern--Software-Engineering-II--Sunnyvale-_R-2354882/apply/applyManually"

# Use this agentql query to get the application form div
APPLICATION_FORM_DIV = """
{
    application_form_div(div that includes both application heading as well as application questions for the following page)
}
"""

def parse_size_arg(arg: str) -> Tuple[int, int]:
    try:
        s = arg.strip().lower()
        if "x" in s:
            w_str, h_str = s.split("x", 1)
        else:
            parts = [p for p in s.replace(",", " ").split() if p]
            if len(parts) < 2:
                return 0, 0
            w_str, h_str = parts[0], parts[1]
        w = int(round(float(w_str.strip())))
        h = int(round(float(h_str.strip())))
        return w, h
    except Exception:
        return 0, 0

def capture_clean_fullpage_screenshot(page, path, original_size_width=1440, original_size_height=900, max_height=8000):
    try:
        page.evaluate("window.scrollTo(0, 0)")
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        target_width = max(int(original_size_width), int(scroll_width))
        target_height = min(int(scroll_height), int(max_height))
        page.set_viewport_size({"width": target_width, "height": target_height})
        time.sleep(0.3)
        page.screenshot(type="png", path=str(path), full_page=False)
    except Exception:
        page.screenshot(type="png", path=str(path), full_page=True)
    finally:
        try:
            page.set_viewport_size({"width": int(original_size_width), "height": int(original_size_height)})
            page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass

def main():
    load_dotenv()
    api_key = os.getenv("AGENTQL_API_KEY")
    if api_key:
        agentql.configure(api_key=api_key)
    url = DEFAULT_URL
    margin = 40
    auto = False
    size_arg = ""

    for idx, a in enumerate(sys.argv[1:]):
        if a == "--url" and idx + 2 <= len(sys.argv[1:]):
            url = sys.argv[1:][idx + 1]
        elif a.startswith("--url="):
            url = a.split("=", 1)[1]
        elif a == "--margin" and idx + 2 <= len(sys.argv[1:]):
            try:
                margin = int(sys.argv[1:][idx + 1])
            except Exception:
                pass
        elif a.startswith("--margin="):
            try:
                margin = int(a.split("=", 1)[1])
            except Exception:
                pass
        elif a == "--size" and idx + 2 <= len(sys.argv[1:]):
            size_arg = sys.argv[1:][idx + 1]
        elif a.startswith("--size="):
            size_arg = a.split("=", 1)[1]
        elif a == "--auto":
            auto = True

    os.makedirs("snapshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)

        if not auto:
            input("Press ENTER to capture full-page screenshot...")

        ts = time.strftime("%Y%m%d_%H%M%S")
        full_path = os.path.join("snapshots", f"fullpage_{ts}.png")
        capture_clean_fullpage_screenshot(page, full_path, 1440, 900)
        print(f"Saved full-page screenshot: {full_path}")

        # Try AgentQL to locate the application form container and derive crop size/position
        form_rect = None
        try:
            # Wrap page for AgentQL and execute query
            page = agentql.wrap(page)
            result = page.query_elements(APPLICATION_FORM_DIV)
            app_form = getattr(result, "application_form_div", None)
            if app_form:
                # Use DOM API to get precise client rect
                rect = app_form.evaluate("el => { const r = el.getBoundingClientRect(); return {left: Math.round(r.left), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height)} }")
                if rect and rect.get("width") and rect.get("height"):
                    form_rect = rect
        except Exception:
            form_rect = None

        # Determine crop width/height
        if form_rect:
            w, h = int(form_rect["width"]), int(form_rect["height"])
        else:
            # Ask for size if not provided
            if size_arg:
                w, h = parse_size_arg(size_arg)
            else:
                entered = input("Enter desired crop size (e.g., 1280x1200): ").strip()
                w, h = parse_size_arg(entered)
            if w <= 0 or h <= 0:
                print("Invalid size provided; using viewport size as fallback.")
                vp = page.viewport_size or {"width": 1440, "height": 900}
                w, h = int(vp.get("width", 1440)), int(vp.get("height", 900))

        try:
            margin = max(0, int(margin))
        except Exception:
            margin = 40

        img = Image.open(full_path).convert("RGB")
        W, H = img.size
        if form_rect:
            left = max(0, int(form_rect["left"]) - margin)
            top = max(0, int(form_rect["top"]) - margin)
            right = min(W, int(form_rect["left"] + form_rect["width"]) + margin)
            bottom = min(H, int(form_rect["top"] + form_rect["height"]) + margin)
        else:
            cx, cy = W // 2, H // 2
            half_w, half_h = w // 2, h // 2
            left = max(0, cx - half_w - margin)
            top = max(0, cy - half_h - margin)
            right = min(W, cx + half_w + margin)
            bottom = min(H, cy + half_h + margin)

        # Ensure coordinates make sense
        if right <= left or bottom <= top:
            print("Computed crop is invalid; skipping crop.")
            crop_path = full_path
        else:
            cropped = img.crop((left, top, right, bottom))
            crop_path = os.path.join("snapshots", f"cropped_{w}x{h}_{ts}.png")
            cropped.save(crop_path)
            print(f"Saved cropped screenshot: {crop_path}")
            print(f"Crop rectangle: left={left}, top={top}, right={right}, bottom={bottom}")

        browser.close()

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        with open(crop_path, "rb") as fh:
            screenshot = fh.read()

        SYSTEM_PROMPT = """
You are an expert image processing and analysis tool that can extract job application form data from screenshots.
Your task is to identify and classify different types of elements on the job application form, such as text inputs, textareas, file uploads, dropdowns, radio/checkbox groups, and buttons based on a given screenshot of the job application form.

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

STEP 2: After extracting the data, take a closer look at the screenshot of the current page to visually verify the classification.

STEP 3: Analyze the screenshot to correct any classification mistakes by examining each form element visually:

For each question in the extracted data, look at the actual visual appearance of its associated form element in the screenshot:
- If you see a dropdown element (has triangle/arrow icon or filter icon) but it was classified as input_text_questions or radio_checkbox_questions, move it to dropdown_questions
- If you see a basic input text field (blank rectangular box with no visual indicators) but it was classified as dropdown_questions or radio_checkbox_questions, move it to input_text_questions  
- If you see radio buttons or checkboxes but they were classified as input_text_questions or dropdown_questions, move them to radio_checkbox_questions

Pay special attention to elements that may have been misclassified entirely (e.g., dropdown elements incorrectly classified as radio_checkbox_questions). Make corrections based on what you actually see in the screenshot, not what the initial extraction suggested.
Review your current structured output to see if you missed any questions while reading the screenshot. There may be a chance that a question flew over your head and you missed it. If you believe there should be a certain question in the job application form, but its not in your current structured output, review the screenshot closely to confirm.

After making corrections:
- Move incorrectly classified questions between the appropriate categories (input_text_questions, dropdown_questions, radio_checkbox_questions)
- Update the all_application_form_questions list to reflect the corrected classifications

STEP 4: Return the final corrected structured output and end the task.
"""

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
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=contents,
            config=config,
        )
        candidate = response.candidates[0] if (response and response.candidates) else None
        raw_text_parts = []
        if candidate and candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.text:
                    raw_text_parts.append(part.text)
        raw_json_text = "\n".join(raw_text_parts).strip()
        if raw_json_text:
            print(raw_json_text)


if __name__ == "__main__":
    main()
