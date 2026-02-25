import json
import argparse
import os
from typing import Dict, Any
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import agentql
from gpt_question_mapper_agent import QuestionMapperAgent as GPTQuestionMapperAgent
from gemini_question_mapper_agent import QuestionMapperAgent as GeminiQuestionMapperAgent
from one_prompt_gemini_question_mapper_agent import OnePromptQuestionMapperAgent
from action_agent import ApplicationActionAgent
from browserbase import Browserbase
from post_extraction_filter import process_form_elements

# Load environment variables
load_dotenv()

# URL for testing
URL = "https://job-boards.greenhouse.io/fiveringsllc/jobs/4806713008"
URL = "https://jobs.ashbyhq.com/zip/83c0a4d8-7a88-4921-be8e-347ba3f3bedd/application"
URL = "https://jobs.lever.co/AIFund/08af7df2-3085-4d7b-ad74-10767e2d93db/apply"
URL = "https://jobs.ashbyhq.com/netic/1242d448-bce2-4328-81ac-4b1080460b00/application"
URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"
URL = "https://jobs.ashbyhq.com/realitydefender/39bb3911-38f3-4db6-9537-0ec90bfb7440/application"
URL = "https://job-boards.greenhouse.io/vast/jobs/4594952006"
URL = "https://jobs.lever.co/bumbleinc/b21c0c9d-b805-4b82-ab4a-1a1d4c2b2ed8/apply"
URL = "https://jobs.ashbyhq.com/reframesystems/ea0a6ec8-939f-40cb-9377-a7da31b91a53/application"
URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"
URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"
URL = "https://jobs.lever.co/xcimer/f53b08bc-83f0-4e34-bbfb-8213f7d25302/apply"
URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"
URL = "https://jobs.ashbyhq.com/ramp/c50962b5-c641-4d44-bbe5-7f1d6e7ce51f/application" #Submitted
URL = "https://job-boards.greenhouse.io/samsungsemiconductor/jobs/7478636003" #Very impressed
URL = "https://jobs.ashbyhq.com/cohere/25cc6633-614a-45e0-8632-ffd4a2475c9b/application" #Submitted
URL = "https://job-boards.greenhouse.io/lucidsoftware/jobs/5596689004" #Submitted
URL = "https://job-boards.greenhouse.io/lucidsoftware/jobs/5596677004" #Submitted
URL = "https://www.zipline.com/careers/open-roles/7561786003"
URL = "https://jobs.ashbyhq.com/ramp/43ac03c8-65f5-4522-ab3d-6d496ae7d925/application"
URL = "https://www.8am.com/openings/?gh_jid=4622069006"

WEB_ELEMENT_PROMPT = """
{
  form {
    application_form_html_container
    application_form_input_text_tags(the text input or text area elements in the application form) []
    application_form_dropdown_questions(the dropdown elements in the application form) []
    application_form_radio_checkbox_questions(the button, radio, and checkbox groups in the application form)[] {
      elements(Each individual button, radio, and checkbox element in the group) []
    }
    application_form_resume_questions(the buttons for uploading resumes, cover letters, or transcripts) []
  }
}
"""

APPLICATION_FORM_QUESTIONS_PROMPT = """
{
  form {
    application_form_questions(All job application form fields: text inputs, textarea, file uploads, dropdowns, buttons, and radio/checkbox groups) []
    input_text_questions(the questions that are tied to the application form text input or text area elements) []
    dropdown_questions(the questions that are tied to the application form dropdown elements) []
    radio_checkbox_questions(the questions tied to button, radio, or checkbox groups) []
    resume_questions(questions about uploading resume or cover letter) [] {
      name
      buttons(buttons associated to the question) []
    }
    submit_button_question(the label on the submit button)
  }
}
"""

class OnePagerApplicant:
    """Class to handle extraction of job application form elements and questions."""
    
    def __init__(self, url: str, headless: bool = False, production: bool = False, slow_mode: bool = False, debug_menu: bool = False):
        """Initialize with the job URL."""
        self.url = url
        self.headless = headless
        self.production = production
        self.slow_mode = slow_mode
        self.debug_menu = debug_menu
        
        # Choose question mapper based on slow_mode
        if self.slow_mode:
            # Use traditional one-by-one mapping for slow mode
            self.question_mapper = GeminiQuestionMapperAgent()
        else:
            # Use efficient one-prompt mapping for default mode
            self.question_mapper = OnePromptQuestionMapperAgent()
        
        # Only initialize Browserbase if in production mode
        if self.production:
            self.bb = Browserbase(api_key=os.getenv("BROWSERBASE_API_KEY"))
            self.session = self.bb.sessions.create(project_id=os.getenv("BROWSERBASE_PROJECT_ID"))
        
    def run(self):
        """Main method to extract form elements and questions, then map them."""
        with sync_playwright() as playwright:
            if self.production:
                # Connect to Browserbase remote browser
                browser = playwright.chromium.connect_over_cdp(self.session.connect_url)
                context = browser.contexts[0]
                page = context.pages[0]
            else:
                # Use local browser for development
                browser = playwright.chromium.launch(headless=self.headless)
                context = browser.new_context(viewport={'width': 1280, 'height': 800})
                page = context.new_page()
            
            # Wrap the page with AgentQL
            page = agentql.wrap(page)
            
            # Navigate to the job application page
            print(f"Navigating to {self.url}")
            page.goto(self.url)
            
            # Wait for the page to load completely
            page.wait_for_page_ready_state()
            print("Page loaded")
            
            # Extract form elements using AgentQL
            form_elements = self.extract_form_elements(page)
            print("\n=== Form Elements ===\n")
            
            # Print raw AgentQL output for WEB_ELEMENT_PROMPT
            if form_elements:
                form_elements_data = form_elements.to_data()
                print("Raw AgentQL output from WEB_ELEMENT_PROMPT:")
                print(json.dumps(form_elements_data, indent=2))
                print()
            
            # Process form elements
            if form_elements and hasattr(form_elements, 'form'):
                # Get raw locators and JSON string from all 4 AgentQL query variables
                raw_locators = []
                
                # Collect all locators from the 4 different query variables
                raw_locators.extend(form_elements.form.application_form_input_text_tags)
                raw_locators.extend(form_elements.form.application_form_dropdown_questions)
                
                # Handle radio/checkbox groups - extract individual elements
                for group in form_elements.form.application_form_radio_checkbox_questions:
                    raw_locators.extend(group.elements)
                    
                raw_locators.extend(form_elements.form.application_form_resume_questions)
                
                # Create JSON string by concatenating str() of each of the 4 variables
                json_parts = []
                json_parts.append(str(form_elements.form.application_form_input_text_tags))
                json_parts.append(str(form_elements.form.application_form_dropdown_questions))
                
                # Handle radio/checkbox groups
                for group in form_elements.form.application_form_radio_checkbox_questions:
                    json_parts.append(str(group.elements))
                    
                json_parts.append(str(form_elements.form.application_form_resume_questions))
                
                # Combine all parts into a single container
                json_string = '[' + ','.join(json_parts) + ']'
                last_accessibility_tree = page.get_last_accessibility_tree()
                
                # Save accessibility tree to file for debugging
                if last_accessibility_tree:
                    with open('accessibility_tree_debug.json', 'w') as f:
                        json.dump(last_accessibility_tree, f, indent=2)
                    print(f"✅ Accessibility tree saved to accessibility_tree_debug.json")
                
                print("\n=== EXTRACTION COMPLETE ===")
                print(f"Raw locators count: {len(raw_locators)}")
                print(f"Accessibility tree keys: {list(last_accessibility_tree.keys()) if last_accessibility_tree else 'None'}")
                print("=== END EXTRACTION ===\n")
                
                # Note: json_string now contains string representations, not parseable JSON
                # Skip JSON parsing since we're using string concatenation approach
                
                # Extract container tf623_id
                container_tf623_id = None
                if hasattr(form_elements.form, 'application_form_html_container'):
                    try:
                        container_tf623_id = form_elements.form.application_form_html_container.get_attribute("tf623_id")
                        print(f"✅ Found container tf623_id: {container_tf623_id}")
                    except Exception as e:
                        print(f"❌ Could not extract container tf623_id: {e}")
                
                # Get original AgentQL names for question mapping
                agentql_names = []
                for item in form_elements.form.application_form_input_text_tags:
                  try:
                    # Try to get text content, placeholder, or aria-label
                    label = item.get_attribute('placeholder') or item.get_attribute('aria-label') or item.get_attribute('name') or ''
                    agentql_names.append(label)
                  except Exception:
                    agentql_names.append('')
                        
                for item in form_elements.form.application_form_dropdown_questions:
                  try:
                    # Try to get aria-label, name, or nearby label text
                    label = item.get_attribute('aria-label') or item.get_attribute('name') or ''
                    agentql_names.append(label)
                  except Exception:
                    agentql_names.append('')
                        
                for group in form_elements.form.application_form_radio_checkbox_questions:
                  for item in group.elements:
                    try:
                      # Try to get text content, value, or aria-label
                      label = item.text_content() or item.get_attribute('value') or item.get_attribute('aria-label') or ''
                      agentql_names.append(label)
                    except Exception:
                      agentql_names.append('')
                            
                for item in form_elements.form.application_form_resume_questions:
                  try:
                    # Try to get text content or aria-label
                    label = item.text_content() or item.get_attribute('aria-label') or ''
                    agentql_names.append(label)
                  except Exception:
                    agentql_names.append('')
                
                if not container_tf623_id:
                    print("❌ No container tf623_id found, using original filtering")
                    # Fallback to original AgentQL names
                    element_string_list = agentql_names
                    element_json_list = []  # No JSON elements since we're using string representations
                    raw_locator_list = raw_locators[:len(agentql_names)]
                else:
                    # Use post-extraction filter
                    print("\n=== POST-EXTRACTION FILTERING ===")
                    
                    # Show original element names before filtering
                    # Note: json_string now contains str() representations, not individual elements
                    print(f"\n📋 Original raw_locators count: {len(raw_locators)} items")
                    print(f"📋 JSON string length: {len(json_string)} characters")
                    
                    # Show the agentql_names for reference
                    print(f"\n📋 AgentQL names ({len(agentql_names)} items):")
                    for i, name in enumerate(agentql_names):
                        print(f"  {i}: '{name}'")
                    
                    filtered_elements, element_names = process_form_elements(
                        raw_locators,
                        last_accessibility_tree,
                        container_tf623_id
                    )
                    
                    if not filtered_elements:
                        print("❌ No valid elements found after filtering")
                        element_json_list = []
                        element_string_list = []
                        raw_locator_list = []
                    else:
                        # Use filtered results directly
                        element_json_list = filtered_elements
                        element_string_list = element_names
                        
                        # Align raw_locator_list with filtered elements
                        # Map filtered elements back to original raw_locators by tf623_id
                        raw_locator_list = []
                        
                        for filtered_elem in filtered_elements:
                            filtered_tf623_id = filtered_elem.get('tf623_id')
                            # Find matching raw_locator by tf623_id
                            for raw_locator in raw_locators:
                                try:
                                    if raw_locator.get_attribute('tf623_id') == filtered_tf623_id:
                                        raw_locator_list.append(raw_locator)
                                        break
                                except Exception:
                                    continue
                        
                        print(f"\n📋 Final element names list ({len(element_string_list)} items):")
                        for i, name in enumerate(element_string_list):
                            print(f"  {i}: '{name}'")
                        
                        print("\n✅ Post-extraction filtering complete:")
                        print(f"   - Filtered elements: {len(element_json_list)}")
                        print(f"   - Element names: {len(element_string_list)}")
                        print(f"   - Raw locators: {len(raw_locator_list)}")
                        
                        # Verify all lists have same length
                        if len(element_json_list) == len(element_string_list) == len(raw_locator_list):
                            print("✅ All lists are properly aligned")
                        else:
                            print(f"❌ List length mismatch: elements={len(element_json_list)}, names={len(element_string_list)}, locators={len(raw_locator_list)}")
                
                print(f"\n✓ Total raw clickable locators: {len(raw_locator_list)}")
                
                # Interactive element clicking loop if not headless and debug_menu is enabled
                if not self.headless and self.debug_menu:
                    print("\n=== Interactive Element Testing ===\n")
                    print(f"You can click on any of the {len(raw_locator_list)} valid elements by entering its index (0-{len(raw_locator_list)-1})")
                    print("Enter 'q' or 'quit' to exit\n")
                    
                    while True:
                        try:
                            user_input = input("Enter element index to click (or 'q' to quit): ").strip()
                            
                            if user_input.lower() in ['q', 'quit']:
                                break
                            
                            index = int(user_input)
                            
                            if 0 <= index < len(raw_locator_list):
                                locator = raw_locator_list[index]
                                element_name = element_string_list[index] if index < len(element_string_list) else f"element_{index}"
                                
                                print(f"\nClicking on element [{index}]: {element_name}")
                                try:
                                    locator.click()
                                    print(f"✓ Successfully clicked on element [{index}]: {element_name}")
                                except Exception as e:
                                    print(f"✗ Failed to click on element [{index}]: {element_name} - {e}")
                            else:
                                print(f"Invalid index. Please enter a number between 0 and {len(raw_locator_list)-1}")
                        
                        except ValueError:
                            print("Invalid input. Please enter a number or 'q' to quit.")
                        except KeyboardInterrupt:
                            print("\nExiting...")
                            break
                        except Exception as e:
                            print(f"Error: {e}")
            else:
                print("No form elements found or invalid response format.")
                return
            
            # Extract application questions using AgentQL
            application_questions_data = self.extract_application_questions(page)
            print("\n=== Application Questions ===\n")

            # Process application questions
            question_list = []
            if application_questions_data and isinstance(application_questions_data, dict):
                print(json.dumps(application_questions_data, indent=2))
                
                # Extract the questions into a list
                if 'form' in application_questions_data and 'application_form_questions' in application_questions_data['form']:
                    question_list = application_questions_data['form']['application_form_questions']
            else:
                print("No application questions found or invalid response format.")

            # Create question elements for dropdown extraction (if available)
            question_elements = None
            if question_list:
                from elements import QuestionElement
                question_elements = [QuestionElement(q, json.dumps(application_questions_data, indent=2)) for q in question_list]
            
            # Extract dropdown options with specific questions for better accuracy
            from dropdown_extractor import DropdownExtractor
            dropdown_extractor = DropdownExtractor(URL)
            dropdown_options = dropdown_extractor.run_with_existing_page(page, question_elements)
            
            # Map questions to form elements using the QuestionMapperAgent
            if element_string_list and question_list:
                print("\n=== Mapping Questions to Form Elements ===\n")
                
                # Use different mapping methods based on slow_mode
                if self.slow_mode:
                    # Traditional one-by-one mapping
                    mapping = self.question_mapper.map_questions_to_elements(question_list, element_string_list, raw_locator_list, json.dumps(application_questions_data, indent=2))
                else:
                    # Efficient one-prompt mapping
                    mapping = self.question_mapper.map_all_questions_to_elements(question_elements, element_string_list, raw_locator_list)
                
                # Merge dropdown options into mapped QuestionElements
                print("\n=== Merging Dropdown Options ===\n")
                dropdown_option_index = 0
                for question_element, elements in mapping.items():
                    if question_element.question_type == 'dropdown_question' and elements:
                        # Only assign options to dropdown questions that have mapped elements
                        if dropdown_option_index < len(dropdown_options):
                            question_element.options = dropdown_options[dropdown_option_index]
                            print(f"Assigned options to '{question_element.question}': {len(question_element.options)} options")
                            dropdown_option_index += 1
                        else:
                            print(f"No more dropdown options available for '{question_element.question}'")
                    elif question_element.question_type == 'dropdown_question':
                        print(f"Skipping dropdown question '{question_element.question}' - no mapped elements")
                
                # Print the mapping
                for question_element, elements in mapping.items():
                    print(f"\n{question_element.question} (Type: {question_element.question_type}):")
                    for element in elements:
                        # WebElement objects contain both name and locator
                        has_locator = element.locator is not None
                        print(f"  - {element.name} {'(has Locator)' if has_locator else ''}")
                    # Show options for dropdown questions
                    if question_element.question_type == 'dropdown_question' and hasattr(question_element, 'options') and question_element.options:
                        print(f"  Options: {question_element.options}")
            
                
                # Create and run ApplicationActionAgent with the mapping
                print("\n=== Processing Questions with Action Agent ===\n")
                try:
                    action_agent = ApplicationActionAgent(mapping)
                    action_agent.process_all_questions()
                    print("\nAction agent processing completed.")
                except Exception as e:
                    print(f"Error running action agent: {e}")
                
            else:
                print("\nCannot create mapping: missing elements or questions.")
            
            # Wait for user to review if not headless
            if not self.headless:
                input("\nPress Enter to close the browser...")
            
            # Close the browser
            browser.close()
    
    def extract_form_elements(self, page):
        """Extract form elements using the web element prompt."""
        try:
            # Use the AgentQL query_elements method
            result = page.query_elements(WEB_ELEMENT_PROMPT, mode="standard", include_hidden=False)
            return result
        except Exception as e:
            print(f"Error extracting form elements: {e}")
            return None
    
    def extract_application_questions(self, page) -> Dict[str, Any]:
        """Extract application questions using the application form prompt."""
        try:
            # Use the AgentQL query_data method
            result = page.query_data(APPLICATION_FORM_QUESTIONS_PROMPT, mode="standard")
            return result
        except Exception as e:
            print(f"Error extracting application questions: {e}")
            return {}


def main():
    """Main function to run the application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Extract and map job application form elements and questions.')
    parser.add_argument('--url', type=str, default=URL, help='URL of the job application page')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--production', action='store_true', help='Use Browserbase remote browser for production testing (default: local browser)')
    parser.add_argument('--debug-menu', action='store_true', help='Enable interactive debug menu for clicking elements (requires headless=False)')
    parser.add_argument('--slow-mode', action='store_true', help='Use traditional one-by-one question mapping instead of efficient one-prompt mapping')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Configure AgentQL with API key from environment if available
    api_key = os.getenv("AGENTQL_API_KEY")
    if api_key:
        agentql.configure(api_key=api_key)
    
    applicant = OnePagerApplicant(args.url, args.headless, production=False, slow_mode=False, debug_menu=False)
    applicant.run()

if __name__ == "__main__":
    main()