import asyncio
import os
import random
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import time

load_dotenv()

# URL variables from main.py
url = "https://schnucks.wd5.myworkdayjobs.com/en-US/SchnucksCareers/job/IT-Intern--Year--Round-_R-0034916"

# Generate a random email to avoid existing account issues
random_num = random.randint(1000, 9999)
email_adress = f"unitysolostudios{random_num}@gmail.com"
password = "d0^nD*aYcJ$U93"

# Personal information for form filling
first_name = "John"
last_name = "Doe"

async def fill_form_with_playwright():
    """Use Playwright directly to fill and submit the form with enhanced handling for reCAPTCHA"""
    apply_url = f"{url.rstrip('/')}/apply/applyManually"

    if os.path.exists("browser_state.json"):
        return
    
    async with async_playwright() as p:
        # Launch browser with larger viewport to ensure all elements are visible
        browser = await p.chromium.launch(headless=False)
        # Use a persistent context to save cache if the file exists
        try:
            context = await browser.new_context(viewport={'width': 1280, 'height': 800}, storage_state="browser_state.json")
            print("Loaded browser state from browser_state.json")
        except Exception as e:
            print(f"Could not load browser state, creating new context: {e}")
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        # Enable more verbose console logging
        page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
        
        # Navigate to the form page
        print(f"Navigating to {apply_url}")
        await page.goto(apply_url, wait_until="networkidle")
        
        # Wait for the form to be visible and fully loaded
        await page.wait_for_selector('form', state='visible')
        print("Form is visible")
        
        # Wait a bit to ensure the page is fully loaded and stable
        await page.wait_for_timeout(2000)
        
        # Check if there are any existing accounts with this email
        existing_account = await page.query_selector_all('text=already exists')
        if existing_account:
            print("WARNING: Account with this email may already exist")
        
        # Fill the form fields with explicit waits between actions
        # Use a more methodical approach with clear feedback
        
        # 1. Fill email field
        print("Filling email field")
        email_field = await page.query_selector('input[data-automation-id="email"]')
        if email_field:
            # Clear and fill using more reliable methods
            await email_field.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(500)
            
            # Type the email character by character with random delays
            for char in email_adress:
                await page.keyboard.type(char)
                # Random delay between 50-150ms
                await page.wait_for_timeout(100)
            
            # Trigger events to ensure validation
            await page.evaluate('''
                (element) => {
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('blur', { bubbles: true }));
                }
            ''', email_field)
            await page.wait_for_timeout(1000)
            
            # Verify the value was set correctly
            email_value = await page.evaluate('(element) => element.value', email_field)
            print(f"Email field value: {email_value}")
        else:
            print("Email field not found")
        
        # 2. Fill password field
        print("Filling password field")
        password_field = await page.query_selector('input[data-automation-id="password"]')
        if password_field:
            await password_field.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(500)
            
            # Type the password character by character with random delays
            for char in password:
                await page.keyboard.type(char)
                await page.wait_for_timeout(100)
            
            # Trigger events
            await page.evaluate('''
                (element) => {
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('blur', { bubbles: true }));
                }
            ''', password_field)
            await page.wait_for_timeout(1000)
            
            # Verify password field has a value (don't print actual password)
            has_value = await page.evaluate('(element) => element.value.length > 0', password_field)
            print(f"Password field has value: {has_value}")
        else:
            print("Password field not found")
        
        # 3. Fill verify password field
        print("Filling verify password field")
        verify_field = await page.query_selector('input[data-automation-id="verifyPassword"]')
        if verify_field:
            await verify_field.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await page.wait_for_timeout(500)
            
            # Type the password character by character with random delays
            for char in password:
                await page.keyboard.type(char)
                await page.wait_for_timeout(100)
            
            # Trigger events
            await page.evaluate('''
                (element) => {
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new Event('blur', { bubbles: true }));
                }
            ''', verify_field)
            await page.wait_for_timeout(1000)
            
            # Verify verify password field has a value
            has_value = await page.evaluate('(element) => element.value.length > 0', verify_field)
            print(f"Verify password field has value: {has_value}")
        else:
            print("Verify password field not found")
        
        # Check for any validation errors before proceeding
        validation_errors = await page.query_selector_all('[aria-invalid="true"]')
        if validation_errors:
            print(f"WARNING: Found {len(validation_errors)} validation errors before submission")
            for i, error in enumerate(validation_errors):
                field_id = await page.evaluate('(element) => element.id || element.name || "unknown"', error)
                print(f"Validation error on field {i+1}: {field_id}")
        
        # Wait a moment before attempting to submit
        await page.wait_for_timeout(2000)
        
        # Handle potential reCAPTCHA
        recaptcha_frame = await page.query_selector('iframe[title*="recaptcha"]')
        if recaptcha_frame:
            print("reCAPTCHA detected - this requires manual intervention")
            print("Waiting 45 seconds for manual reCAPTCHA solving...")
            
            # Get more information about the reCAPTCHA
            recaptcha_info = await page.evaluate('''
            () => {
                const recaptchaElements = document.querySelectorAll('iframe[title*="recaptcha"], div.g-recaptcha, div[class*="recaptcha"]');
                return Array.from(recaptchaElements).map(el => ({
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    src: el.tagName === 'IFRAME' ? el.src : null,
                    dataAttributes: {
                        sitekey: el.getAttribute('data-sitekey'),
                        callback: el.getAttribute('data-callback'),
                        size: el.getAttribute('data-size')
                    }
                }));
            }
            ''')
            
            if recaptcha_info and len(recaptcha_info) > 0:
                print(f"Found {len(recaptcha_info)} reCAPTCHA elements:")
                for i, info in enumerate(recaptcha_info):
                    print(f"reCAPTCHA {i+1}: {info}")
            
            # Give user time to solve the CAPTCHA manually
            await page.wait_for_timeout(45000)
        
        # Try to click the filter div first, as it's intercepting clicks
        print("Looking for click filter div")
        filter_div = await page.query_selector('div[data-automation-id="click_filter"]')
        if filter_div:
            print("Found click filter div, clicking it")
            # Try multiple click strategies for the filter div
            try:
                # Strategy 1: Direct click
                await filter_div.click(force=True)
                print("Direct click on filter div")
            except Exception as e:
                print(f"Direct click on filter div failed: {e}")
                
                # Strategy 2: JavaScript click
                await page.evaluate('''
                    (element) => {
                        // Remove any blocking styles
                        if (element.style) {
                            element.style.pointerEvents = 'auto';
                            element.style.opacity = '1';
                        }
                        
                        // Create and dispatch click event
                        const clickEvent = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        element.dispatchEvent(clickEvent);
                    }
                ''', filter_div)
                print("Dispatched click event to filter div")
            
            # Wait for any reactions
            await page.wait_for_timeout(2000)
            
            # Check if reCAPTCHA appeared after clicking filter div
            recaptcha_after_click = await page.query_selector('iframe[title*="recaptcha"], div.g-recaptcha, div[class*="recaptcha"]')
            if recaptcha_after_click:
                print("reCAPTCHA detected after clicking filter div")
                print("Waiting 45 seconds for manual reCAPTCHA solving...")
                await page.wait_for_timeout(45000)  # Wait 45 seconds for manual solving
        else:
            print("Click filter div not found")
            
        # Debug: Check if there are any captcha elements
        captcha_elements = await page.query_selector_all('iframe[src*="recaptcha"], iframe[src*="captcha"], div[class*="captcha"], div[class*="recaptcha"]')
        if captcha_elements and len(captcha_elements) > 0:
            print(f"Found {len(captcha_elements)} potential captcha elements")
            print("Waiting 45 seconds for manual captcha solving...")
            await page.wait_for_timeout(45000)
        
        # Now try to find and click the actual submit button
        print("Looking for submit button")
        
        # Try multiple selectors for the submit button
        submit_button_selectors = [
            'button[data-automation-id="createAccountSubmitButton"]',
            'button:has-text("Create Account")',
            'button.css-a9u6na',  # Updated class from the HTML
            'button[type="submit"]',
            'input[type="submit"]'
        ]
        
        submit_button = None
        for selector in submit_button_selectors:
            button = await page.query_selector(selector)
            if button:
                submit_button = button
                print(f"Found submit button with selector: {selector}")
                break
        
        if submit_button:
            # Check if button is visible and enabled
            is_visible = await submit_button.is_visible()
            is_enabled = await submit_button.is_enabled()
            print(f"Submit button visible: {is_visible}, enabled: {is_enabled}")
            
            # Try multiple submission strategies
            
            # Strategy 1: JavaScript click with enhanced button preparation
            await page.evaluate('''
                (element) => {
                    // Make sure the button is enabled and visible
                    element.disabled = false;
                    element.style.opacity = '1';
                    element.style.pointerEvents = 'auto';
                    element.setAttribute('aria-hidden', 'false');
                    element.tabIndex = 0;
                    
                    // Scroll into view
                    element.scrollIntoView({behavior: 'smooth', block: 'center'});
                    
                    // Log button state before clicking
                    console.log('Button state before click:', {
                        disabled: element.disabled,
                        ariaHidden: element.getAttribute('aria-hidden'),
                        display: element.style.display,
                        visibility: element.style.visibility,
                        opacity: element.style.opacity,
                        pointerEvents: element.style.pointerEvents
                    });
                    
                    // Create and dispatch click event
                    const clickEvent = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    element.dispatchEvent(clickEvent);
                    console.log('JavaScript click dispatched to submit button');
                    
                    // Try to trigger form submission directly
                    const form = element.closest('form');
                    if (form) {
                        console.log('Found parent form, attempting direct submission');
                        setTimeout(() => {
                            try {
                                form.submit();
                                console.log('Form submitted programmatically');
                            } catch (e) {
                                console.log('Form submit error:', e.message);
                            }
                        }, 1000);
                    }
                }
            ''', submit_button)
            print("Dispatched click event to submit button")
            
            # Wait a moment for the click to take effect
            await page.wait_for_timeout(3000)
            
            # Strategy 2: Direct Playwright click
            try:
                await submit_button.click(force=True, timeout=5000)
                print("Clicked submit button directly")
            except Exception as e:
                print(f"Direct click failed: {e}")
                
                # Strategy 3: Try to find the form and submit it directly
                form = await page.query_selector('form')
                if form:
                    await page.evaluate("""
                        (params) => {
                            const form = params.form;
                            try {
                                form.submit();
                                console.log('Form submitted via form.submit()'); 
                            } catch (e) {
                                console.log('Form.submit failed: ' + e.message);
                                try {
                                    // Try to dispatch a submit event
                                    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                                    form.dispatchEvent(submitEvent);
                                    console.log('Submit event dispatched');
                                } catch (e2) {
                                    console.log('Submit event dispatch failed: ' + e2.message);
                                }
                            }
                        }
                    """, {"form": form})
                    print("Attempted to submit form directly")
        else:
            print("Submit button not found, trying to find and submit form")
            
            # Try to find the form and submit it
            form = await page.query_selector('form')
            if form:
                await page.evaluate("""
                    (params) => {
                        const form = params.form;
                        try {
                            form.submit();
                            console.log('Form submitted via form.submit()'); 
                        } catch (e) {
                            console.log('Form.submit failed: ' + e.message);
                            try {
                                // Try to dispatch a submit event
                                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                                form.dispatchEvent(submitEvent);
                                console.log('Submit event dispatched');
                            } catch (e2) {
                                console.log('Submit event dispatch failed: ' + e2.message);
                            }
                        }
                    }
                """, {"form": form})
                print("Attempted to submit form")
            else:
                print("Form not found, trying to click any visible button")
                # Last resort: try to click any button that might be the submit button
                buttons = await page.query_selector_all('button')
                for button in buttons:
                    text = await button.text_content()
                    is_visible = await button.is_visible()
                    if is_visible and ('submit' in text.lower() or 'create' in text.lower() or 'account' in text.lower()):
                        print(f"Trying to click button with text: {text}")
                        try:
                            await button.click(force=True)
                            print(f"Clicked button with text: {text}")
                            break
                        except Exception as e:
                            print(f"Failed to click button: {e}")
        
        # Wait for a moment to ensure the form submission has time to process
        await page.wait_for_timeout(5000)
        
        # Check if we've reached the personal information page (indicates successful account creation)
        personal_info_selector = 'h3:has-text("Legal Name")'
        try:
            await page.wait_for_selector(personal_info_selector, timeout=10000)
            print("Detected personal information page via selector: h3:has-text(\"Legal Name\")")
            print("We are on the personal information page")
            
            # Save browser state to a file for future use
            await context.storage_state(path="browser_state.json")
            print("Browser state saved to browser_state.json")
            print("SUCCESS: Account creation successful and reached personal information page")
            # Exit immediately after successful browser state creation
            return
        except Exception as e:
            print(f"Could not detect personal information page: {e}")
            print("Account creation may have failed or redirected to an unexpected page")
            
            # Still save the browser state in case it's useful
            try:
                await context.storage_state(path="browser_state.json")
                print("Browser state saved to browser_state.json despite possible failure")
            except Exception as save_error:
                print(f"Failed to save browser state: {save_error}")
        
        print("Account creation process completed!")


if __name__ == "__main__":
    asyncio.run(fill_form_with_playwright())