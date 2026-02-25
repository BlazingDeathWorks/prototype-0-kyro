import os
from typing import Dict, List
from pathlib import Path
from dual_model_question_agent import DualModelApplicationQuestionAgent as ApplicationQuestionAgent
from models import QuestionResponse
from elements import QuestionElement, WebElement
import time

class ApplicationActionAgent:
    """
    Action agent that processes the question-element mapping and performs actions
    based on question types. Uses the existing ApplicationQuestionAgent for LLM guidance.
    """
    
    def __init__(self, question_element_mapping: Dict[QuestionElement, List[WebElement]] = None):
        """
        Initialize the ActionAgent with the question-element mapping.
        
        Args:
            question_element_mapping: Dictionary mapping QuestionElement to list of WebElement objects
        """
        self.question_element_mapping = question_element_mapping or {}
        self.question_agent = ApplicationQuestionAgent()
    
    def process_all_questions(self):
        """
        Process all questions in the mapping and perform actions based on their types.
        """
        print("Starting to process all questions...")
        print(f"Total questions to process: {len(self.question_element_mapping)}")
        
        question_count = 0
        for question_element, web_elements in self.question_element_mapping.items():
            question_count += 1
            print(f"\n[{question_count}/{len(self.question_element_mapping)}] Processing question: {question_element.question}")
            
            # Build extra context with dropdown options if available
            extra_context = f"Question type: {question_element.question_type}\nElements: {[str(elem) for elem in web_elements]}"
            if question_element.question_type == "dropdown_question" and hasattr(question_element, 'options') and question_element.options:
                extra_context += f"\nAvailable options: {question_element.options}"
            
            # Get LLM guidance for this question
            llm_response = self.question_agent.answer_question(
                question=question_element.question,
                extra_context=extra_context
            )
            
            print(f"LLM Response: {llm_response.response}")
            print(f"Creative Mode: {llm_response.creative_mode}")
            print(f"Reasoning: {llm_response.reasoning}")
            print(f"Question type: {question_element.question_type}")
            print(f"Associated elements: {[str(elem) for elem in web_elements]}")
            if question_element.question_type == "dropdown_question" and hasattr(question_element, 'options') and question_element.options:
                print(f"Available options: {question_element.options}")
            
            # Process based on question type
            if question_element.question_type == "input_text_question":
                self._handle_input_text_question(question_element, web_elements, llm_response)
            elif question_element.question_type == "dropdown_question":
                self._handle_dropdown_question(question_element, web_elements, llm_response)
            elif question_element.question_type == "radio_checkbox_question":
                self._handle_radio_checkbox_question(question_element, web_elements, llm_response)
            elif question_element.question_type == "resume_question":
                self._handle_resume_question(question_element, web_elements, llm_response)
            else:
                print(f"Unknown question type: {question_element.question_type}")
    
    def _handle_input_text_question(self, question_element: QuestionElement, web_elements: List[WebElement], llm_response: QuestionResponse):
        """
        Handle input text questions by typing the LLM guidance.
        
        Args:
            question_element: The QuestionElement instance
            web_elements: List of WebElement objects associated with this question
            llm_response: QuestionResponse object containing the LLM's structured response
        """
        if web_elements and web_elements[0].locator:
            web_elements[0].locator.fill(llm_response.response)
            print(f"✓ Filled text input with: {llm_response.response}")
        else:
            print("No web elements found for text input handling")
        pass
    
    def _handle_dropdown_question(self, question_element: QuestionElement, web_elements: List[WebElement], llm_response: QuestionResponse):
        """
        Handle dropdown questions with options selection.
        
        Args:
            question_element: The QuestionElement instance
            web_elements: List of WebElement objects associated with this question
            llm_response: QuestionResponse object containing the LLM's structured response
        """
        if web_elements and web_elements[0].locator:
            try:
                # Click the dropdown element
                web_elements[0].locator.click()
                time.sleep(0.5)  # Wait for dropdown to open
                
                # Type the entire response using page keyboard to avoid refocusing
                page = web_elements[0].locator.page
                page.keyboard.type(llm_response.response)
                time.sleep(0.5)  # Wait for filtering to complete
                
                # Press Enter to select the filtered option
                page.keyboard.press("Enter")
                time.sleep(0.3)
                print(f"✓ Selected dropdown option: {llm_response.response}")
                
                # Cleanup: Close dropdown by pressing Escape or clicking elsewhere
                time.sleep(0.5)  # Wait for selection to register
                try:
                    # First try pressing Escape to close dropdown
                    web_elements[0].locator.press("Escape")
                    time.sleep(0.3)
                    
                    # If dropdown is still open, click on body to close it
                    page = web_elements[0].locator.page
                    page.locator('body').click(position={'x': 10, 'y': 10})
                    time.sleep(0.3)
                    
                except Exception as cleanup_error:
                    print(f"Warning: Dropdown cleanup failed: {cleanup_error}")
                    
            except Exception as e:
                print(f"Error handling dropdown: {e}")
        else:
            print("No web elements found for dropdown handling")
        time.sleep(0.2)
    
    def _handle_radio_checkbox_question(self, question_element: QuestionElement, web_elements: List[WebElement], llm_response: QuestionResponse):
        """
        Handle radio button and checkbox questions.
        
        Args:
            question_element: The QuestionElement instance
            web_elements: List of WebElement objects associated with this question
            llm_response: QuestionResponse object containing the LLM's structured response
        """
        # Find and click elements matching LLM response
        for element in web_elements:
            if element.name.lower() == llm_response.response.lower() and element.locator:
                element.locator.click()
                print(f"✓ Selected option: {element.name}")
                break
        else:
            print(f"No matching option found for: {llm_response.response}")
        pass
    
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

    def _handle_resume_question(self, question_element: QuestionElement, web_elements: List[WebElement], llm_response: QuestionResponse):
        """
        Handle resume upload questions using file chooser technique.
        
        Args:
            question_element: The QuestionElement instance
            web_elements: List of WebElement objects associated with this question
            llm_response: QuestionResponse object containing the LLM's structured response
        """
        # Skip cover letter questions
        if "cover letter" in question_element.question.lower():
            print(f"⏭️ Skipping cover letter question: {question_element.question}")
            return
            
        resume_path = self._get_default_resume_path()
        
        # Validate resume file exists
        if not os.path.exists(resume_path):
            print(f"Resume file not found at: {resume_path}")
            return
        
        print(f"Using resume file: {resume_path}")
        
        # Try to upload resume using each web element
        for element in web_elements:
            if self._try_upload_with_element(element, resume_path):
                print(f"✓ Resume uploaded successfully via: {element.name}")
                print("Waiting for auto-fill processing...")
                # Wait for potential auto-fill after resume upload
                if element.locator:
                    element.locator.page.wait_for_timeout(10000)  # Wait 10 seconds
                return
        
        print("❌ Failed to upload resume with any available elements")

    def _try_upload_with_element(self, element: WebElement, resume_path: str) -> bool:
        """
        Try to upload resume using a specific web element.
        
        Args:
            element: The WebElement to use for upload
            resume_path: Path to the resume file
            
        Returns:
            True if upload was successful, False otherwise
        """
        try:
            # Method 1: Try upload button click with file chooser handling
            if element.locator:
                print(f"Attempting upload via element: {element.name}")
                
                # Get the page from the locator
                page = element.locator.page
                
                # Set up file chooser event handler before clicking
                with page.expect_file_chooser() as fc_info:
                    element.locator.click()
                
                # Handle the file chooser dialog
                file_chooser = fc_info.value
                file_chooser.set_files(resume_path)
                print("✓ File uploaded successfully via file chooser!")
                return True
                
        except Exception as e:
            print(f"File chooser method failed: {e}")
            
            # Fallback: try to find file input after button click
            try:
                if element.locator:
                    page = element.locator.page
                    page.wait_for_timeout(1000)
                    file_inputs = page.locator('input[type="file"]')
                    if file_inputs.count() > 0:
                        file_inputs.first.set_input_files(resume_path)
                        print("✓ File uploaded successfully via file input (fallback)!")
                        return True
            except Exception as fallback_e:
                print(f"Fallback method also failed: {fallback_e}")
        
        return False


def main():
    """
    Main function to run the ActionAgent.
    """
    try:
        agent = ApplicationActionAgent()
        agent.process_all_questions()
    except Exception as e:
        print(f"Error running ActionAgent: {e}")


if __name__ == "__main__":
    main()