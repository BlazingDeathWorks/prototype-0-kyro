#!/usr/bin/env python3
"""
Dropdown Extractor

This script uses AgentQL to find all dropdown elements on a job application page
and extracts the available options for each dropdown.

Usage:
    from dropdown_extractor import extract_dropdowns
    extract_dropdowns(url="https://example.com/job-application", headless=True)
"""

import json
import time
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import agentql

# Load environment variables
load_dotenv()

# Default URL for testing
DEFAULT_URL = "https://jobs.lever.co/AIFund/08af7df2-3085-4d7b-ad74-10767e2d93db/apply"
DEFAULT_URL = "https://job-boards.greenhouse.io/cloudflare/jobs/6750119?gh_jid=6750119"
DEFAULT_URL = "https://jobs.ashbyhq.com/cohere/25cc6633-614a-45e0-8632-ffd4a2475c9b/application"
DEFAULT_URL = "https://jobs.lever.co/xcimer/f53b08bc-83f0-4e34-bbfb-8213f7d25302/apply"

# AgentQL prompt for dropdown elements from agent_ql_prompts.txt
DROPDOWN_BUTTONS_PROMPT = """
{
  form {
    dropdown_buttons(application form dropdown buttons) []
  }
}
"""

# Base AgentQL prompt for dropdown elements
DROPDOWN_BUTTONS_BASE_PROMPT = """
{
  form {
    dropdown_element_trigger_buttons []
  }
}
"""

class DropdownExtractor:
    """Class to handle extraction of dropdown elements and their options from job application forms."""
    
    def __init__(self, url: str, headless: bool = True):
        """Initialize with the job URL."""
        self.url = url
        self.headless = headless
        
    def run(self):
        """Main method to extract dropdown elements and their options."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            
            # Wrap the page with AgentQL
            page = agentql.wrap(browser.new_page())
            
            # Navigate to the job application page
            print(f"Navigating to {self.url}")
            page.goto(self.url)
            
            # Wait for the page to load completely
            page.wait_for_page_ready_state()
            print("Page loaded successfully")
            
            # Extract dropdown elements using AgentQL
            dropdown_data = self.extract_dropdown_buttons(page)
            
            if dropdown_data:
                result = self.process_dropdown_buttons(dropdown_data, page)
                return result
            else:
                print("No dropdown elements found on the page.")
                return []
                 
    def run_with_existing_page(self, page, question_elements=None):
        """Extract dropdown elements using an existing page object.
        
        Args:
            page: The playwright page object
            question_elements: Optional list of QuestionElement objects to use for targeted extraction
        """
        print("Extracting dropdown options from existing page")
        
        # Extract dropdown elements using AgentQL
        if question_elements:
            dropdown_data = self.extract_dropdown_buttons_specific(page, question_elements)
        else:
            dropdown_data = self.extract_dropdown_buttons(page)
        
        if dropdown_data:
            result = self.process_dropdown_buttons(dropdown_data, page)
            return result
        else:
            print("No dropdown elements found on the page.")
            return []
    
    def extract_dropdown_buttons(self, page):
        """Extract dropdown elements using the dropdown prompt."""
        try:
            print("\n=== Extracting Dropdown Elements ===")
            result = page.query_elements(DROPDOWN_BUTTONS_PROMPT, mode="standard")
            return result
        except Exception as e:
            print(f"Error extracting dropdown elements: {e}")
            return None
    
    def extract_dropdown_buttons_specific(self, page, question_elements):
        """Extract dropdown elements using specific dropdown questions.
        
        Args:
            page: The playwright page object
            question_elements: List of QuestionElement objects
        """
        try:
            print("\n=== Extracting Dropdown Elements with Specific Questions ===")
            
            # Filter for dropdown questions only
            dropdown_questions = [qe.question for qe in question_elements if qe.question_type == 'dropdown_question']
            
            if not dropdown_questions:
                print("No dropdown questions found")
                return None
            
            print(f"Found {len(dropdown_questions)} dropdown questions:")
            for i, question in enumerate(dropdown_questions, 1):
                print(f"  {i}. {question}")
            
            # Create the specific prompt with dropdown questions
            dropdown_questions_text = "Get the dropdown trigger buttons associated with the following questions: " + ", ".join(dropdown_questions)
            
            # Simple concatenation approach - add the description before dropdown_element_trigger_buttons
            # Escape quotes in the dropdown_questions_text to prevent JSON parsing issues
            escaped_text = dropdown_questions_text.replace('"', '\"')
            specific_prompt = f"""
{{
    form {{
        dropdown_element_trigger_buttons({escaped_text}) []
    }}
}}
"""
            
            print(f"\nUsing specific AgentQL query:")
            print(specific_prompt)
            
            result = page.query_elements(specific_prompt, mode="standard")
            return result
        except Exception as e:
            print(f"Error extracting dropdown elements with specific questions: {e}")
            return None
    

    
    def process_dropdown_buttons(self, dropdown_data, page):
        """Process the extracted dropdown elements and get their options."""
        print("\n=== Processing Dropdown Elements ===")
        
        # Convert to data format for inspection
        if hasattr(dropdown_data, 'to_data'):
            data_dict = dropdown_data.to_data()
            print("\nDropdown data structure:")
            print(json.dumps(data_dict, indent=2))
        

        
        # Process each dropdown element
        dropdown_info = []
        simplified_output = []
        
        try:
            if hasattr(dropdown_data, 'form') and hasattr(dropdown_data.form, 'dropdown_element_trigger_buttons'):
                dropdown_buttons = dropdown_data.form.dropdown_element_trigger_buttons
                
                print(f"\nFound {len(dropdown_buttons)} dropdown element(s)")
                
                for i, dropdown in enumerate(dropdown_buttons, 1):
                    print(f"\n--- Dropdown {i} ---")
                    
                    # Get dropdown information
                    dropdown_info_dict = {
                        'index': i,
                        'element_info': str(dropdown),
                        'options': []
                    }
                    
                    try:
                        # Get the tag name
                        tag_name = dropdown.get_attribute('tagName')
                        print(f"Tag: {tag_name}")
                        dropdown_info_dict['tag_name'] = tag_name
                        
                        # Get the name attribute if available
                        name_attr = dropdown.get_attribute('name')
                        if name_attr:
                            print(f"Name: {name_attr}")
                            dropdown_info_dict['name'] = name_attr
                        
                        # Get the id attribute if available
                        id_attr = dropdown.get_attribute('id')
                        if id_attr:
                            print(f"ID: {id_attr}")
                            dropdown_info_dict['id'] = id_attr
                        
                        # Get class attribute to identify component type
                        class_attr = dropdown.get_attribute('class')
                        if class_attr:
                            print(f"Class: {class_attr}")
                            dropdown_info_dict['class'] = class_attr
                        
                        # Scroll dropdown into view before extraction with aggressive scrolling
                        try:
                            # First try standard scroll into view
                            dropdown.scroll_into_view_if_needed()
                            page.wait_for_timeout(300)
                            
                            # Get element position and scroll more aggressively if needed
                            bounding_box = dropdown.bounding_box()
                            if bounding_box:
                                # Calculate scroll position to center the element
                                scroll_y = bounding_box['y'] + bounding_box['height']/2 - 400  # Approximate viewport center
                                # Scroll to center the element in viewport
                                page.evaluate(f"window.scrollTo({{ top: {scroll_y}, behavior: 'smooth' }});")
                                page.wait_for_timeout(500)  # Wait for smooth scroll to complete
                            
                            print("Scrolled dropdown into view with aggressive centering")
                        except Exception as e:
                            print(f"Warning: Could not scroll dropdown into view: {e}")
                        
                        # Ensure any previous dropdowns are closed
                        try:
                            page.locator("body").click()
                            page.wait_for_timeout(300)
                        except:
                            pass
                        
                        # Use universal extraction method
                        extracted_options = self.extract_options_universal(dropdown, page)
                        dropdown_info_dict['options'] = extracted_options
                        
                        print(f"Total options extracted: {len(extracted_options)}")
                        
                        # Check if it's a multi-select
                        multiple_attr = dropdown.get_attribute('multiple')
                        if multiple_attr is not None:
                            print(f"Multiple selection: {multiple_attr}")
                            dropdown_info_dict['multiple'] = True
                        else:
                            dropdown_info_dict['multiple'] = False
                        
                    except Exception as e:
                        print(f"Error processing dropdown {i}: {e}")
                        dropdown_info_dict['error'] = str(e)
                    
                    dropdown_info.append(dropdown_info_dict)
                    
                    # Create simplified output with only options
                    options_text = [opt['text'] for opt in extracted_options if opt['text'].strip()]
                    simplified_output.append(options_text)
                    
                    # Add a small delay between processing dropdowns
                    time.sleep(0.5)
                
                # Print only the simplified JSON output
                print(json.dumps(simplified_output, indent=2))
                
                # Return the simplified output for import usage
                return simplified_output
                
            else:
                print("No dropdown elements found in the expected structure.")
                return []
                
        except Exception as e:
            print(f"Error processing dropdown elements: {e}")
            return []
    
    def limit_options(self, options):
        """If options > 15, set the 15th option to '...' and exclude the rest."""
        if len(options) <= 15:
            return options
        limited_options = options[:14]
        limited_options.append({
            'index': 15,
            'value': '...',
            'text': '...'
        })
        return limited_options
    
    def extract_options_universal(self, dropdown, page):
        """Universal method to extract options from any dropdown format."""
        extracted_options = []
        
        # Strategy 1: Standard HTML select options
        try:
            option_elements = dropdown.locator('option').all()
            if option_elements:
                print(f"Found {len(option_elements)} standard HTML options")
                for i, option in enumerate(option_elements):
                    try:
                        text = option.text_content() or option.inner_text() or ""
                        value = option.get_attribute('value') or ""
                        extracted_options.append({
                            'index': i + 1,
                            'value': value.strip(),
                            'text': text.strip()
                        })
                    except Exception as e:
                        print(f"Error extracting standard option {i}: {e}")
                return self.limit_options(extracted_options)
        except Exception as e:
            print(f"Standard HTML option extraction failed: {e}")
        
        # Strategy 2: Pre-existing options (SCOPED to specific dropdown)
        try:
            # First try to find the dropdown's parent container
            dropdown_container = dropdown
            try:
                parent_selectors = ['.select', '.react-select', '.dropdown', '[data-testid*="select"]', '.form-field']
                for parent_sel in parent_selectors:
                    parent = dropdown.locator(f'xpath=ancestor::{parent_sel.replace(".", "*[contains(@class, \"").replace("[", "*[").replace("]", "\")]") if parent_sel.startswith(".") else f"xpath=ancestor::{parent_sel}"}')
                    if parent.count() > 0:
                        dropdown_container = parent.first
                        print(f"Found dropdown container for pre-existing search: {parent_sel}")
                        break
            except:
                pass
            
            pre_existing_selectors = [
                '[role="option"]',
                '.select__option',
                '.react-select__option',
                '.dropdown-option',
                '.option',
                '.menu-item',
                'li[data-value]',
                '[data-option]'
            ]
            
            for selector in pre_existing_selectors:
                try:
                    # Look for options within the dropdown container ONLY
                    options = dropdown_container.locator(selector)
                    if options.count() > 0:
                        option_texts = options.all_text_contents()
                        option_values = []
                        
                        # Try to get values as well
                        try:
                            for i in range(options.count()):
                                option_elem = options.nth(i)
                                value = (option_elem.get_attribute('value') or 
                                        option_elem.get_attribute('data-value') or 
                                        option_elem.get_attribute('data-option-value') or "")
                                option_values.append(value)
                        except:
                            option_values = [""] * len(option_texts)
                        
                        print(f"Found {len(option_texts)} scoped pre-existing options with {selector}")
                        for i, (text, value) in enumerate(zip(option_texts, option_values)):
                            if text.strip():  # Only add non-empty options
                                extracted_options.append({
                                    'index': i + 1,
                                    'value': value.strip(),
                                    'text': text.strip()
                                })
                        
                        if extracted_options:
                            return self.limit_options(extracted_options)
                except Exception as e:
                    print(f"Scoped pre-existing option extraction failed for {selector}: {e}")
                    continue
        except Exception as e:
            print(f"Scoped pre-existing option strategy failed: {e}")
        
        # Strategy 3: Interactive dropdown opening
        try:
            print("Attempting interactive dropdown opening...")
            
            # Ensure dropdown is properly scrolled and focused
            try:
                dropdown.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
            except:
                pass
            
            # Step 1: Find and click the dropdown trigger
            click_targets = [
                dropdown.locator('input.select__input').first,
                dropdown.locator('input[role="combobox"]').first,
                dropdown.locator('.react-select__input input').first,
                dropdown.locator('input').first,
                dropdown.locator('.select__control').first,
                dropdown.locator('.react-select__control').first,
                dropdown
            ]
            
            clicked = False
            for target in click_targets:
                try:
                    if target.count() > 0 and target.is_visible():
                        # Scroll element into view before clicking
                        target.scroll_into_view_if_needed()
                        page.wait_for_timeout(300)  # Brief pause after scrolling
                        target.click(timeout=3000)
                        clicked = True
                        print(f"Successfully clicked dropdown trigger")
                        break
                except Exception as e:
                    print(f"Click attempt failed: {e}")
                    continue
            
            if not clicked:
                print("Could not click any dropdown trigger")
                return extracted_options
            
            # Step 2: Wait for menu to appear
            page.wait_for_timeout(800)  # Give more time for menu to render
            
            # Step 3: Look for menu and options - SCOPED TO SPECIFIC DROPDOWN
            menu_and_option_combinations = [
                ('.select__menu', '.select__option'),
                ('.react-select__menu', '.react-select__option'),
                ('.dropdown-menu', '.dropdown-option'),
                ('[role="listbox"]', '[role="option"]'),
                ('.menu', '.option'),
                ('.dropdown', '.dropdown-item')
            ]
            
            # First try to find options within the dropdown's parent container
            dropdown_container = dropdown
            try:
                # Try to find the parent container that might contain both trigger and menu
                parent_selectors = ['.select', '.react-select', '.dropdown', '[data-testid*="select"]', '.form-field']
                for parent_sel in parent_selectors:
                    parent = dropdown.locator(f'xpath=ancestor::{parent_sel.replace(".", "*[contains(@class, \"").replace("[", "*[").replace("]", "\")]") if parent_sel.startswith(".") else f"xpath=ancestor::{parent_sel}"}')
                    if parent.count() > 0:
                        dropdown_container = parent.first
                        print(f"Found dropdown container with {parent_sel}")
                        break
            except:
                pass
            
            # Try scoped search within dropdown container first
            for menu_selector, option_selector in menu_and_option_combinations:
                try:
                    if menu_selector:
                        # Wait for menu within the dropdown container
                        try:
                            page.wait_for_selector(menu_selector, timeout=2000)
                            # Look for options within the dropdown container's scope
                            options = dropdown_container.locator(f"{menu_selector} {option_selector}")
                            if options.count() == 0:
                                # Fallback: look for menu globally but options within container
                                menu = page.locator(menu_selector).first
                                if menu.count() > 0:
                                    options = menu.locator(option_selector)
                        except:
                            continue
                    else:
                        # Look for options within dropdown container only
                        options = dropdown_container.locator(option_selector)
                    
                    if options.count() > 0:
                        # Extract all text contents immediately
                        option_texts = options.all_text_contents()
                        option_values = []
                        
                        # Try to get values
                        try:
                            for i in range(min(options.count(), len(option_texts))):
                                option_elem = options.nth(i)
                                value = (option_elem.get_attribute('value') or 
                                        option_elem.get_attribute('data-value') or 
                                        option_elem.get_attribute('data-option-value') or "")
                                option_values.append(value)
                        except:
                            option_values = [""] * len(option_texts)
                        
                        print(f"Found {len(option_texts)} scoped options with menu: '{menu_selector}', option: '{option_selector}'")
                        
                        for i, (text, value) in enumerate(zip(option_texts, option_values)):
                            if text.strip():  # Only add non-empty options
                                extracted_options.append({
                                    'index': i + 1,
                                    'value': value.strip(),
                                    'text': text.strip()
                                })
                        
                        # Close dropdown with multiple attempts
                        try:
                            # Try clicking outside the dropdown area
                            page.locator("body").click()
                            page.wait_for_timeout(300)
                            
                            # If dropdown is still open, try pressing Escape
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)
                            
                            # Additional click to ensure closure
                            page.locator("body").click()
                            page.wait_for_timeout(200)
                        except:
                            pass
                        
                        if extracted_options:
                            return self.limit_options(extracted_options)
                            
                except Exception as e:
                    print(f"Scoped option extraction failed for {menu_selector}/{option_selector}: {e}")
                    continue
            
            # Fallback: Global search only if scoped search failed
            print("Scoped search failed, trying global search as fallback...")
            global_option_selectors = [
                '[role="option"]',
                '.select__option', 
                '.react-select__option'
            ]
            
            for option_selector in global_option_selectors:
                try:
                    options = page.locator(option_selector)
                    if options.count() > 0:
                        option_texts = options.all_text_contents()
                        option_values = []
                        
                        try:
                            for i in range(min(options.count(), len(option_texts))):
                                option_elem = options.nth(i)
                                value = (option_elem.get_attribute('value') or 
                                        option_elem.get_attribute('data-value') or 
                                        option_elem.get_attribute('data-option-value') or "")
                                option_values.append(value)
                        except:
                            option_values = [""] * len(option_texts)
                        
                        print(f"Found {len(option_texts)} global fallback options with '{option_selector}'")
                        
                        for i, (text, value) in enumerate(zip(option_texts, option_values)):
                            if text.strip():
                                extracted_options.append({
                                    'index': i + 1,
                                    'value': value.strip(),
                                    'text': text.strip()
                                })
                        
                        # Close dropdown
                        try:
                            page.locator("body").click()
                            page.wait_for_timeout(300)
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)
                            page.locator("body").click()
                            page.wait_for_timeout(200)
                        except:
                            pass
                        
                        if extracted_options:
                            return self.limit_options(extracted_options)
                            
                except Exception as e:
                    print(f"Global fallback extraction failed for {option_selector}: {e}")
                    continue
                        
                except Exception as e:
                    print(f"Menu/option combination failed for {menu_selector}/{option_selector}: {e}")
                    continue
            
            # Close dropdown if still open with robust cleanup
            try:
                page.locator("body").click()
                page.wait_for_timeout(300)
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                page.locator("body").click()
                page.wait_for_timeout(200)
            except:
                pass
                
        except Exception as e:
            print(f"Interactive dropdown strategy failed: {e}")
        
        # Strategy 4: Brute force text extraction
        try:
            print("Attempting brute force text extraction...")
            
            # Look for any elements that might contain option text
            brute_force_selectors = [
                'li',
                'div[role="option"]',
                'span[data-value]',
                '.option-text',
                '.select-item',
                '[class*="option"]',
                '[class*="item"]'
            ]
            
            for selector in brute_force_selectors:
                try:
                    elements = dropdown.locator(selector).all()
                    if elements:
                        for i, elem in enumerate(elements):
                            try:
                                text = elem.text_content() or elem.inner_text() or ""
                                if text.strip() and len(text.strip()) < 100:  # Reasonable option length
                                    extracted_options.append({
                                        'index': i + 1,
                                        'value': elem.get_attribute('value') or "",
                                        'text': text.strip()
                                    })
                            except:
                                continue
                        
                        if extracted_options:
                            print(f"Brute force found {len(extracted_options)} options with {selector}")
                            return self.limit_options(extracted_options)
                except:
                    continue
        except Exception as e:
            print(f"Brute force strategy failed: {e}")
        
        print("All extraction strategies failed")
        return self.limit_options(extracted_options)
    
    def save_dropdown_info(self, dropdown_info: List[Dict[str, Any]]):
        """Save dropdown information to a JSON file."""
        try:
            print(f"\n=== Summary ===")
            print(f"Total dropdowns found: {len(dropdown_info)}")
            
            # Print summary of each dropdown with all options
            for dropdown in dropdown_info:
                print(f"\nDropdown {dropdown['index']}:")
                if 'name' in dropdown:
                    print(f"  Name: {dropdown['name']}")
                if 'id' in dropdown:
                    print(f"  ID: {dropdown['id']}")
                print(f"  Options: {len(dropdown['options'])}")
                
                # Display all extracted options
                if dropdown['options']:
                    print(f"  Extracted Options:")
                    for option in dropdown['options']:
                        print(f"    {option['index']}. {option['text']}")
                else:
                    print(f"  No options extracted")
                    
                if dropdown.get('multiple', False):
                    print(f"  Type: Multi-select")
                else:
                    print(f"  Type: Single-select")
                    
        except Exception as e:
            print(f"Error saving dropdown information: {e}")


def extract_dropdowns(url: str = DEFAULT_URL, headless: bool = True):
    """Extract dropdown elements and their options from job application forms.
    
    Args:
        url (str): URL of the job application page. Defaults to DEFAULT_URL.
        headless (bool): Run in headless mode (no browser window). Defaults to False.
    """
    # Configure AgentQL with API key from environment if available
    api_key = os.getenv("AGENTQL_API_KEY")
    if api_key:
        agentql.configure(api_key=api_key)
        print("AgentQL configured with API key")
    else:
        print("Warning: AGENTQL_API_KEY not found in environment variables")
        print("Please set your AgentQL API key in the .env file")
    
    # Create and run the dropdown extractor
    extractor = DropdownExtractor(url)
    return extractor.run()


if __name__ == "__main__":
    # Run with default parameters when executed directly
    extract_dropdowns()