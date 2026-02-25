import asyncio
import time
from playwright.async_api import async_playwright
from browser_use import Agent, BrowserSession, ChatGoogle
from dotenv import load_dotenv
import agentql
import os
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import JobApplicationForm

load_dotenv()

# Configure AgentQL
agentql.configure(api_key=os.getenv("AGENTQL_API_KEY"))

URL = "https://invesco.wd1.myworkdayjobs.com/en-US/IVZ/job/Atlanta-Georgia/Summer-2026-Internship---Security---Early-Careers_R-11801/apply"

async def extract_dropdown_options(page, dropdown_element):
    """
    Extract dropdown options using multiple strategies inspired by dropdown_extractor.py
    """
    extracted_options = []
    
    # Strategy 2: Pre-existing options (scoped to dropdown)
    try:
        # Find dropdown container
        dropdown_container = dropdown_element
        parent_selectors = ['.select', '.react-select', '.dropdown', '[data-testid*="select"]', '.form-field']
        
        for parent_sel in parent_selectors:
            try:
                if parent_sel.startswith('.'):
                    # Class selector
                    class_name = parent_sel[1:]
                    parent_element = dropdown_element.locator(f'xpath=./ancestor-or-self::*[contains(@class, "{class_name}")]').first
                else:
                    # Attribute selector
                    parent_element = dropdown_element.locator(f'xpath=./ancestor-or-self::*{parent_sel}').first
                
                if await parent_element.count() > 0:
                    dropdown_container = parent_element
                    break
            except Exception:
                continue
        
        # Look for pre-existing options in the container, but exclude role="option" if this element has role="listbox"
        element_role = await dropdown_element.get_attribute('role') or ""
        
        option_selectors = [
            '.select-option',
            '.dropdown-option',
            '[data-testid*="option"]',
            'li[data-value]',
            'div[data-value]'
        ]
        
        for selector in option_selectors:
            try:
                options = await dropdown_container.locator(selector).all()
                if options:
                    print(f"Found {len(options)} pre-existing options with selector: {selector}")
                    for i, option in enumerate(options):
                        try:
                            text = await option.text_content() or await option.inner_text() or ""
                            value = await option.get_attribute('data-value') or await option.get_attribute('value') or text
                            if text.strip():
                                extracted_options.append({
                                    'index': i + 1,
                                    'value': value.strip(),
                                    'text': text.strip()
                                })
                        except Exception as e:
                            print(f"Error extracting pre-existing option {i}: {e}")
                    if extracted_options:
                        return extracted_options[:15]  # Limit to 15 options
            except Exception as e:
                print(f"Pre-existing option extraction failed for selector {selector}: {e}")
    except Exception as e:
        print(f"Pre-existing option extraction failed: {e}")
    
    # Strategy 3: Click and extract dynamic options
    try:
        print("Attempting to click dropdown to reveal options...")
        
        # Try clicking the dropdown element
        await page.locator("body").click()
        await asyncio.sleep(0.5)
        
        await dropdown_element.click()
        await asyncio.sleep(1)  # Wait for options to appear
        
        # Look for dynamically loaded options, but exclude role="option" if this element has role="listbox"
        dynamic_selectors = [
            '.option',
            '.select-option',
            '.dropdown-option',
            '[data-testid*="option"]',
            'li[data-value]',
            'div[data-value]',
            '.react-select__option',
            '.ant-select-item-option'
        ]
        
        # Only include [role="option"] if this element doesn't have role="listbox"
        # This prevents aria-haspopup="listbox" elements from picking up options from role="listbox" elements
        if element_role != 'listbox':
            dynamic_selectors.insert(0, '[role="option"]')
        
        for selector in dynamic_selectors:
            try:
                options = await page.locator(selector).all()
                if options:
                    print(f"Found {len(options)} dynamic options with selector: {selector}")
                    for i, option in enumerate(options):
                        try:
                            text = await option.text_content() or await option.inner_text() or ""
                            value = await option.get_attribute('data-value') or await option.get_attribute('value') or text
                            if text.strip():
                                extracted_options.append({
                                    'index': i + 1,
                                    'value': value.strip(),
                                    'text': text.strip()
                                })
                        except Exception as e:
                            print(f"Error extracting dynamic option {i}: {e}")
                    if extracted_options:
                        # Click away to close dropdown
                        await page.locator("body").click()
                        return extracted_options[:15]  # Limit to 15 options
            except Exception as e:
                print(f"Dynamic option extraction failed for selector {selector}: {e}")
        
        # Click away to close dropdown
        await page.locator("body").click()
        
    except Exception as e:
        print(f"Dynamic option extraction failed: {e}")
    
    return extracted_options

async def main():
    """
    Comprehensive test: Non-agentic searching + Browser-Use with AgentQL query
    """
    print('🚀 Comprehensive Test: Non-Agentic + Browser-Use Integration')
    
    playwright = None
    browser = None
    
    try:
        # Step 1: Start Playwright browser with CDP enabled
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,  # Keep browser visible
            args=['--remote-debugging-port=9222']  # Enable CDP
        )
        
        # Create a new page to ensure browser is ready
        context = await browser.new_context()
        page = await agentql.wrap_async(context.new_page())
        
        await page.goto(URL)
        
        print('✅ Playwright browser opened with CDP on port 9222')
        
        # Wait for the page to load completely
        await asyncio.sleep(3)  # Simple wait to ensure page is loaded
        print("Page loaded")
        
        # Step 2: Create Browser-Use session connected to the same browser
        browser_session = BrowserSession(cdp_url='http://localhost:9222')

        # Wait for user to be ready to execute agent
        input("Press Enter when you're ready to start the comprehensive test...")
        
        # print("\n" + "="*80)
        # print("PART 1: NON-AGENTIC SEARCHING")
        # print("="*80)
        
        # # Step 3: Try AgentQL to find application form container
        # try:
        #     container_query = """
        #     {
        #       form {
        #         application_form_html_container
        #       }
        #     }
        #     """
            
        #     print("🔍 Trying AgentQL to find application form container...")
        #     form_result = await page.query_elements(container_query)
            
        #     if form_result and hasattr(form_result, 'form') and form_result.form.application_form_html_container:
        #         container = form_result.form.application_form_html_container
        #         print("✅ Found application form container using AgentQL")
        #     else:
        #         print("⚠️ AgentQL could not find application form container, using fallback")
        #         container = page  # Use page as fallback
                
        # except Exception as e:
        #     print(f"⚠️ Error with AgentQL query: {e}, using fallback")
        #     container = page  # Use page as fallback
        
        # # Step 4: Search for aria-haspopup=listbox within the container, click, and get dropdown options
        # aria_haspopup_elements = await container.locator('[aria-haspopup="listbox"]').all()
        # print(f'\n🔍 Found {len(aria_haspopup_elements)} elements with aria-haspopup=listbox within container')
        # aria_haspopup_results = []
        
        # for idx, el in enumerate(aria_haspopup_elements):
        #     try:
        #         print(f'\n--- Processing aria-haspopup element {idx + 1} ---')
                
        #         # Get element attributes for identification
        #         tag_name = await el.get_attribute('tagName') or 'unknown'
        #         element_id = await el.get_attribute('id') or 'no-id'
        #         element_class = await el.get_attribute('class') or 'no-class'
        #         element_name = await el.get_attribute('name') or 'no-name'
                
        #         # Extract tf623_id from the element's id attribute
        #         tf623_id = ""
        #         try:
        #             if element_id != 'no-id' and 'tf623' in element_id:
        #                 tf623_id = element_id
        #             else:
        #                 # Look for tf623_id in other attributes like name, data-*, etc.
        #                 if 'tf623' in element_name:
        #                     tf623_id = element_name
        #                 else:
        #                     # Check all attributes for tf623 pattern
        #                     all_attrs = await el.evaluate('el => Array.from(el.attributes).map(attr => `${attr.name}=${attr.value}`).join(" ")')
        #                     if 'tf623' in all_attrs:
        #                         # Extract the tf623 value from the attributes string
        #                         import re
        #                         tf623_match = re.search(r'tf623[^=]*=([^\s]+)', all_attrs)
        #                         if tf623_match:
        #                             tf623_id = tf623_match.group(1)
                
        #         except Exception as tf623_e:
        #             print(f"Error extracting tf623_id for element {idx + 1}: {tf623_e}")
                
        #         print(f'Element: <{tag_name}> id="{element_id}" name="{element_name}" class="{element_class}" tf623_id="{tf623_id}"')
                
        #         # Extract dropdown options
        #         options = await extract_dropdown_options(page, el)
                
        #         aria_haspopup_results.append({
        #             'element_index': idx + 1,
        #             'tag_name': tag_name,
        #             'id': element_id,
        #             'name': element_name,
        #             'class': element_class,
        #             'tf623_id': tf623_id,
        #             'options_count': len(options),
        #             'options': options
        #         })
                
        #         print(f'✅ Extracted {len(options)} options from aria-haspopup element {idx + 1} - tf623_id: "{tf623_id}"')
                
        #     except Exception as e:
        #         print(f'❌ Error processing aria-haspopup element {idx + 1}: {e}')
        #         aria_haspopup_results.append({
        #             'element_index': idx + 1,
        #             'error': str(e)
        #         })
        
        # # Step 5: Search for radio and checkbox elements with aria-checked within the container
        # aria_checked_elements = await container.locator('[aria-checked]').all()
        # print(f'\n🔍 Found {len(aria_checked_elements)} elements with aria-checked within container')
        # aria_checked_results = []
        
        # for idx, el in enumerate(aria_checked_elements):
        #     try:
        #         print(f'\n--- Processing aria-checked element {idx + 1} ---')
                
        #         # Get element attributes for identification
        #         tag_name = await el.get_attribute('tagName') or 'unknown'
        #         element_id = await el.get_attribute('id') or 'no-id'
        #         element_class = await el.get_attribute('class') or 'no-class'
        #         element_type = await el.get_attribute('type') or 'unknown'
        #         element_role = await el.get_attribute('role') or 'no-role'
        #         element_name = await el.get_attribute('name') or 'no-name'
        #         aria_checked_value = await el.get_attribute('aria-checked') or 'unknown'
                
        #         # Extract tf623_id from the element's id attribute
        #         tf623_id = ""
        #         try:
        #             if element_id != 'no-id' and 'tf623' in element_id:
        #                 tf623_id = element_id
        #             else:
        #                 # Look for tf623_id in other attributes like name, data-*, etc.
        #                 if 'tf623' in element_name:
        #                     tf623_id = element_name
        #                 else:
        #                     # Check all attributes for tf623 pattern
        #                     all_attrs = await el.evaluate('el => Array.from(el.attributes).map(attr => `${attr.name}=${attr.value}`).join(" ")')
        #                     if 'tf623' in all_attrs:
        #                         # Extract the tf623 value from the attributes string
        #                         import re
        #                         tf623_match = re.search(r'tf623[^=]*=([^\s]+)', all_attrs)
        #                         if tf623_match:
        #                             tf623_id = tf623_match.group(1)
                
        #         except Exception as tf623_e:
        #             print(f"Error extracting tf623_id for element {idx + 1}: {tf623_e}")
                
        #         print(f'Element: <{tag_name}> type="{element_type}" role="{element_role}" id="{element_id}" name="{element_name}" class="{element_class}" aria-checked="{aria_checked_value}" tf623_id="{tf623_id}"')
                
        #         aria_checked_results.append({
        #             'element_index': idx + 1,
        #             'tag_name': tag_name,
        #             'type': element_type,
        #             'role': element_role,
        #             'id': element_id,
        #             'name': element_name,
        #             'class': element_class,
        #             'aria_checked': aria_checked_value,
        #             'tf623_id': tf623_id
        #         })
                
        #         print(f'✅ Processed aria-checked element {idx + 1} - name: "{element_name}" tf623_id: "{tf623_id}"')
                
        #     except Exception as e:
        #         print(f'❌ Error processing aria-checked element {idx + 1}: {e}')
        #         aria_checked_results.append({
        #             'element_index': idx + 1,
        #             'error': str(e)
        #         })
        
        # # Combine all non-agentic results
        # non_agentic_results = {
        #     'aria_haspopup_elements': aria_haspopup_results,
        #     'aria_checked_elements': aria_checked_results
        # }
        
        # print(f'\n📊 NON-AGENTIC RESULTS:')
        # print(json.dumps(non_agentic_results, indent=2))

        print("\n" + "="*80)
        print("PART 2: BROWSER-USE WITH AGENTQL QUERY")
        print("="*80)
        
        # Step 6: Create and run the browser-use agent with the AgentQL query
        agent = Agent(
            task="""
            STEP 1: First, use the extract tool to get only the page title with this minimal query:

            {
              form {
                application_page_title(The heading title that describes the topic/type of information the applicant needs to provide for this specific page such as 'My Information', 'My Experience', 'Voluntary Disclosures', 'Application Questions', 'Review', etc.)
              }
            }

            STEP 2: Check if the application_page_title contains the word "Experience". If it does, perform these hardcoded Experience page tasks:
            
            EXPERIENCE PAGE TASKS:
            - Count the current number of work experience containers/sections on the page
            - If there are fewer than 3 work experience containers, use the "Add" button to add more until there are exactly 3 work experience containers
            - Count the current number of education experience containers/sections on the page  
            - If there are fewer than 1 education experience container, use the "Add" button to add one until there is exactly 1 education experience container
            - Look for a website section on the page
            - If a website section exists, count the current number of website fields available
            - If there are fewer than 2 website fields and the website section is present, use the "Add" button to add more until there are exactly 2 website fields

            STEP 3: Use the extract tool again with the full query to get all form data:

            IMPORTANT ELEMENT CLASSIFICATION DEFINITIONS:
            - INPUT ELEMENTS: Blank rectangular boxes with nothing else inside them. These are basic text input fields or text areas.
            - DROPDOWN ELEMENTS: Rectangular boxes that have visual indicators differentiating them from basic input boxes:
              * Official dropdowns: Have a triangle/arrow icon on the right side
              * Semi-dropdowns: Have a filter icon or other visual indicator inside the box
              * Both types should be classified as dropdown elements and their questions as dropdown_questions

            {
              form {
                application_form_questions(All job application form fields: text inputs, textarea, file uploads, dropdowns, buttons, and radio/checkbox groups) {
                 application_page_title(The heading title that describes the topic/type of information the applicant needs to provide for this specific page such as 'My Information', 'My Experience', 'Voluntary Disclosures', 'Application Questions', 'Review', etc.)
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

            STEP 4: After extracting the data, take a screenshot of the current page to visually verify the classification.

            STEP 5: Analyze the screenshot to correct any classification mistakes by examining each form element visually:
            
            For each question in the extracted data, look at the actual visual appearance of its associated form element in the screenshot:
            - If you see a dropdown element (has triangle/arrow icon or filter icon) but it was classified as input_text_questions or radio_checkbox_questions, move it to dropdown_questions
            - If you see a basic input text field (blank rectangular box with no visual indicators) but it was classified as dropdown_questions or radio_checkbox_questions, move it to input_text_questions  
            - If you see radio buttons or checkboxes but they were classified as input_text_questions or dropdown_questions, move them to radio_checkbox_questions
            
            Pay special attention to elements that may have been misclassified entirely (e.g., dropdown elements incorrectly classified as radio_checkbox_questions). Make corrections based on what you actually see in the screenshot, not what the initial extraction suggested.
            
            After making corrections:
            - Move incorrectly classified questions between the appropriate categories (input_text_questions, dropdown_questions, radio_checkbox_questions)
            - Update the all_application_form_questions list to reflect the corrected classifications

            STEP 6: Return the final corrected structured output and use the done tool to finish the task.
            """,
            llm=ChatGoogle(model='gemini-2.5-pro', temperature=0),
            browser_session=browser_session,
            output_model_schema=JobApplicationForm,
        )
        
        print('🎯 Starting browser-use agent with AgentQL query...')
        
        # Run the agent
        result = await agent.run()
        result = JobApplicationForm.model_validate_json(result.final_result())
        
        print(f'\n📊 BROWSER-USE RESULT:')
        # Convert Pydantic model to formatted JSON for better readability
        result_json = result.model_dump()
        print(json.dumps(result_json, indent=2, ensure_ascii=False))
        
        print("\n" + "="*80)
        print("PART 3: DYNAMIC AGENTQL QUERY WITH EXTRACTED QUESTIONS")
        print("="*80)
        
        # Step 7: Extract question names from Browser-Use result for dynamic AgentQL query
        input_text_questions = result.form.input_text_questions or []
        dropdown_questions = result.form.dropdown_questions or []
        radio_checkbox_questions = result.form.radio_checkbox_questions or []
        
        print(f"📝 Extracted {len(input_text_questions)} input text questions")
        print(f"📝 Extracted {len(dropdown_questions)} dropdown questions") 
        print(f"📝 Extracted {len(radio_checkbox_questions)} radio/checkbox questions")
        
        # Create dynamic AgentQL query sections conditionally
        query_sections = ["application_form_html_container"]
        
        if input_text_questions:
            input_text_desc = f"Get the text input or text area elements associated to the following questions: {'; '.join(input_text_questions)}"
            query_sections.append(f"application_form_input_text_tags({input_text_desc}) []")
            
        if dropdown_questions:
            dropdown_desc = f"Get the dropdown elements associated to the following questions: {'; '.join(dropdown_questions)}"
            query_sections.append(f"application_form_dropdown_questions({dropdown_desc}) []")
            
        if radio_checkbox_questions:
            radio_checkbox_desc = f"Get the button, radio, and checkbox groups associated to the following questions: {'; '.join(radio_checkbox_questions)}"
            query_sections.append(f"""application_form_radio_checkbox_questions({radio_checkbox_desc}) [] {{
      elements(Each individual button, radio, and checkbox element in the group) []
    }}""")
        
        # Always include resume questions section
        query_sections.append("application_form_resume_questions(the buttons for uploading resumes, cover letters, or transcripts) []")
        
        # Build the dynamic AgentQL query
        sections_str = "\n    ".join(query_sections)
        dynamic_query = f"""
{{
  form {{
    {sections_str}
  }}
}}
"""
        
        print(f"\n🔧 Dynamic AgentQL Query:")
        print(dynamic_query)
        
        # Step 8: Execute the dynamic AgentQL query
        print(f"\n🎯 Executing dynamic AgentQL query...")
        dynamic_result = await page.query_elements(dynamic_query, mode="standard")
        
        # Step 9: Display JSON output similar to one_pager.py
        print("\n=== Form Elements ===\n")
        if dynamic_result:
            dynamic_result_data = await dynamic_result.to_data()
            print("Raw AgentQL output from dynamic query:")
            print(json.dumps(dynamic_result_data, indent=2))
            print()
        
        # Step 10: Extract individual elements for interactive menu (inspired by one_pager.py)
        if dynamic_result and hasattr(dynamic_result, 'form'):
            print(f"\n🖱️ Extracting individual elements for interactive menu...")
            
            # Collect all raw locators from the dynamic result
            raw_locators = []
            element_names = []
            
            # Extract input text elements - only if they exist
            if input_text_questions and hasattr(dynamic_result.form, 'application_form_input_text_tags'):
                for i, element in enumerate(dynamic_result.form.application_form_input_text_tags):
                    raw_locators.append(element)
                    try:
                        # Try to get meaningful name from element attributes
                        name = (await element.get_attribute('placeholder') or 
                               await element.get_attribute('aria-label') or 
                               await element.get_attribute('name') or 
                               f'input_element_{i+1}')
                        element_names.append(name)
                    except Exception:
                        element_names.append(f'input_element_{i+1}')
            
            # Extract dropdown elements - only if they exist
            if dropdown_questions and hasattr(dynamic_result.form, 'application_form_dropdown_questions'):
                for i, element in enumerate(dynamic_result.form.application_form_dropdown_questions):
                    raw_locators.append(element)
                    try:
                        # Try to get meaningful name from element attributes
                        name = (await element.get_attribute('aria-label') or 
                               await element.get_attribute('name') or 
                               f'dropdown_element_{i+1}')
                        element_names.append(name)
                    except Exception:
                        element_names.append(f'dropdown_element_{i+1}')
            
            # Extract radio/checkbox elements - only if they exist
            if radio_checkbox_questions and hasattr(dynamic_result.form, 'application_form_radio_checkbox_questions'):
                for group_i, group in enumerate(dynamic_result.form.application_form_radio_checkbox_questions):
                    if hasattr(group, 'elements'):
                        for i, element in enumerate(group.elements):
                            raw_locators.append(element)
                            try:
                                # Try to get meaningful name from element attributes
                                name = (await element.text_content() or 
                                       await element.get_attribute('value') or 
                                       await element.get_attribute('aria-label') or 
                                       f'radio_checkbox_element_{group_i+1}_{i+1}')
                                element_names.append(name)
                            except Exception:
                                element_names.append(f'radio_checkbox_element_{group_i+1}_{i+1}')
            
            # Extract resume elements - only if they exist
            if hasattr(dynamic_result.form, 'application_form_resume_questions'):
                for i, element in enumerate(dynamic_result.form.application_form_resume_questions):
                    raw_locators.append(element)
                    try:
                        # Try to get meaningful name from element attributes
                        name = (await element.text_content() or 
                               await element.get_attribute('aria-label') or 
                               f'resume_element_{i+1}')
                        element_names.append(name)
                    except Exception:
                        element_names.append(f'resume_element_{i+1}')
            
            print(f"\n✓ Total clickable elements found: {len(raw_locators)}")
            
            # Interactive element clicking menu (inspired by one_pager.py)
            print("\n=== Interactive Element Testing ===\n")
            print(f"You can click on any of the {len(raw_locators)} valid elements by entering its index (0-{len(raw_locators)-1})")
            print("Enter 'q' or 'quit' to exit\n")
            
            # Display element list for reference
            for i, name in enumerate(element_names):
                print(f"  [{i}]: {name}")
            print()
            
            while True:
                try:
                    user_input = input("Enter element index to click (or 'q' to quit): ").strip()
                    
                    if user_input.lower() in ['q', 'quit']:
                        break
                    
                    index = int(user_input)
                    
                    if 0 <= index < len(raw_locators):
                        locator = raw_locators[index]
                        element_name = element_names[index] if index < len(element_names) else f"element_{index}"
                        
                        print(f"\nClicking on element [{index}]: {element_name}")
                        try:
                            await locator.click({'force': True})
                            print(f"✓ Successfully clicked on element [{index}]: {element_name}")
                        except Exception as e:
                            print(f"✗ Failed to click on element [{index}]: {element_name} - {e}")
                    else:
                        print(f"Invalid index. Please enter a number between 0 and {len(raw_locators)-1}")
                
                except ValueError:
                    print("Invalid input. Please enter a number or 'q' to quit.")
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"Error: {e}")
            
            print(f"\n✅ Interactive menu session completed")
        else:
            print("❌ No dynamic result or form found for interactive menu")
        
    except Exception as e:
        print(f'❌ Error: {e}')
        raise
        
    finally:
        # Clean up
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        print('✅ Cleanup complete')


if __name__ == '__main__':
    asyncio.run(main())
