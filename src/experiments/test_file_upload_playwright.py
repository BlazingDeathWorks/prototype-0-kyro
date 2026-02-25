import os
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import agentql

# Load environment variables
load_dotenv()

# Default test URL (can be overridden via command line)
DEFAULT_URL = "https://jobs.ashbyhq.com/zip/83c0a4d8-7a88-4921-be8e-347ba3f3bedd/application"

# Simplified AgentQL query to find only upload buttons
RESUME_UPLOAD_QUERY = """
{
  upload_button(Upload button for resume or CV files)
}
"""

# Alternative query for more specific resume upload elements
RESUME_UPLOAD_SPECIFIC_QUERY = """
{
  form {
    resume_question(Questions about uploading resume or cover letter) {
      upload_button(Upload File button or similar)
    }
  }
}
"""

class FileUploadTester:
    """
    Test script for uploading resume files using Playwright and AgentQL.
    """
    
    def __init__(self, url: str, headless: bool = False, resume_path: str = None):
        """
        Initialize the FileUploadTester.
        
        Args:
            url: The job application URL to test
            headless: Whether to run browser in headless mode
            resume_path: Path to the resume file to upload
        """
        self.url = url
        self.headless = headless
        self.resume_path = resume_path or self._get_default_resume_path()
        
        # Validate resume file exists
        if not os.path.exists(self.resume_path):
            raise FileNotFoundError(f"Resume file not found at: {self.resume_path}")
    
    def _get_default_resume_path(self) -> str:
        """
        Get the default resume file path.
        
        Returns:
            Path to the default resume file
        """
        # Look for resume files in the resume folder
        resume_dir = Path(__file__).parent.parent / "resume"
        
        # Common resume file extensions
        extensions = ["*.pdf", "*.doc", "*.docx", "*.txt"]
        
        for ext in extensions:
            resume_files = list(resume_dir.glob(ext))
            if resume_files:
                return str(resume_files[0])  # Return first found resume
        
        # Fallback to sample resume
        return str(resume_dir / "sample_resume.pdf")
    
    def run(self):
        """
        Run the file upload test.
        """
        print(f"Starting file upload test for: {self.url}")
        print(f"Resume file: {self.resume_path}")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=self.headless)
            
            try:
                # Create new page with AgentQL
                page = agentql.wrap(browser.new_page())
                
                # Navigate to the job application page
                print(f"Navigating to: {self.url}")
                page.goto(self.url)
                
                # Wait for page to load
                time.sleep(3)
                
                # Try to find resume upload button
                print("Searching for resume upload button...")
                
                # First attempt with general query
                try:
                    upload_elements = page.query_elements(RESUME_UPLOAD_QUERY)
                    print(f"Found upload elements: {upload_elements}")
                    
                    if upload_elements and upload_elements.upload_button:
                        self._handle_upload_button(page, upload_elements.upload_button)
                    else:
                        print("No upload button found with general query, trying specific query...")
                        self._try_specific_query(page)
                        
                except Exception as e:
                    print(f"Error with general query: {e}")
                    print("Trying specific query...")
                    self._try_specific_query(page)
                
                # Keep browser open for inspection if not headless
                if not self.headless:
                    print("\nBrowser will stay open for inspection. Press Enter to close...")
                    input()
                    
            except Exception as e:
                print(f"Error during test: {e}")
            finally:
                browser.close()
    
    def _try_specific_query(self, page):
        """
        Try the specific resume upload query.
        
        Args:
            page: The Playwright page object
        """
        try:
            specific_elements = page.query_elements(RESUME_UPLOAD_SPECIFIC_QUERY)
            print(f"Found specific elements: {specific_elements}")
            
            if specific_elements and specific_elements.form:
                form = specific_elements.form
                if hasattr(form, 'resume_question') and form.resume_question:
                    self._handle_resume_question(page, form.resume_question)
                else:
                    print("No resume question found in form")
            else:
                print("No form elements found with specific query")
                
        except Exception as e:
            print(f"Error with specific query: {e}")
    
    def _handle_upload_button(self, page, upload_button):
        """
        Handle the upload button found by AgentQL.
        
        Args:
            page: The Playwright page object
            upload_button: The upload button element
        """
        print("Processing upload button...")
        
        # Try upload button click with file chooser handling
        try:
            print("Attempting upload via upload button...")
            
            # Set up file chooser event handler before clicking
            with page.expect_file_chooser() as fc_info:
                upload_button.click()
            
            # Handle the file chooser dialog
            file_chooser = fc_info.value
            file_chooser.set_files(self.resume_path)
            print("✓ File uploaded successfully via upload button!")
            return True
                
        except Exception as e:
            print(f"Upload button method failed: {e}")
            # Fallback: try to find file input after button click
            try:
                page.wait_for_timeout(1000)
                file_inputs = page.locator('input[type="file"]')
                if file_inputs.count() > 0:
                    file_inputs.first.set_input_files(self.resume_path)
                    print("✓ File uploaded successfully via upload button (fallback)!")
                    return True
            except Exception as fallback_e:
                print(f"Upload button fallback also failed: {fallback_e}")
        
        print("❌ Upload button method failed")
        return False
    
    def _handle_resume_question(self, page, resume_question):
        """
        Handle resume question elements.
        
        Args:
            page: The Playwright page object
            resume_question: The resume question elements
        """
        print("Processing resume question elements...")
        
        # Try to upload via resume question upload button
        if hasattr(resume_question, 'upload_button') and resume_question.upload_button:
            try:
                print("Clicking resume question upload button...")
                
                # Handle file chooser dialog
                with page.expect_file_chooser() as fc_info:
                    resume_question.upload_button.click()
                
                file_chooser = fc_info.value
                file_chooser.set_files(self.resume_path)
                print("✓ Resume uploaded via button click!")
                return True
                    
            except Exception as e:
                print(f"Resume question upload button failed: {e}")
                # Fallback: try to find file input after button click
                try:
                    page.wait_for_timeout(1000)
                    file_inputs = page.locator('input[type="file"]')
                    if file_inputs.count() > 0:
                        file_inputs.first.set_input_files(self.resume_path)
                        print("✓ Resume uploaded via button click (fallback)!")
                        return True
                except Exception as fallback_e:
                    print(f"Resume question upload button fallback failed: {fallback_e}")
        
        print("❌ Resume question upload methods failed")
        return False


def main():
    """
    Main function to run the file upload test.
    """
    parser = argparse.ArgumentParser(description="Test file upload functionality with Playwright and AgentQL")
    parser.add_argument("--url", default=DEFAULT_URL, help="Job application URL to test")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--resume", help="Path to resume file to upload")
    
    args = parser.parse_args()
    
    try:
        tester = FileUploadTester(
            url=args.url,
            headless=args.headless,
            resume_path=args.resume
        )
        tester.run()
    except Exception as e:
        print(f"Error running file upload test: {e}")


if __name__ == "__main__":
    main()