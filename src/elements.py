import json
from typing import Any, Optional, Literal

class QuestionElement:
    """Class to represent a question with its type, section, and date format context."""
    
    def __init__(
        self, 
        question: str, 
        application_form_json: str, 
        section: str = None, 
        date_format: str = None,
        page_title: str = None
    ):
        """Initialize a QuestionElement with question text and determine its type.
        
        Args:
            question: The question text
            application_form_json: JSON string containing the application form structure
            section: Optional section context (e.g., "Work Experience", "Education", "Websites")
            date_format: Optional date format hint (e.g., "MM/YYYY", "MM/DD/YYYY")
            page_title: The application page title (e.g., "My Experience", "My Information")
        """
        self.question = question
        self.options = []  # Initialize options before type determination
        self.section = section  # Section context for "My Experience" pages
        self.date_format = date_format  # Date format for date-related questions
        self.page_title = page_title  # The page title for context
        self.question_type = self._determine_question_type(question, application_form_json)
    
    def _determine_question_type(self, question: str, application_form_json: str) -> Literal["input_text_question", "dropdown_question", "radio_checkbox_question", "resume_question"]:
        """Determine the question type based on the application form JSON.
        
        Args:
            question: The question text
            application_form_json: JSON string containing the application form structure
            
        Returns:
            The question type as a literal string
        """
        try:
            form_data = json.loads(application_form_json)
            form_section = form_data.get("form", form_data)

            # Extract different question types
            input_questions = form_section.get("input_text_questions", [])
            
            # Handle dropdown_questions - they can be strings or objects
            dropdown_questions_raw = form_section.get("dropdown_questions", [])
            if dropdown_questions_raw and isinstance(dropdown_questions_raw[0], dict):
                dropdown_questions = [q["question"] for q in dropdown_questions_raw if "question" in q]
            else:
                dropdown_questions = dropdown_questions_raw  # Already strings
            
            radio_checkbox_questions = [q["question"] for q in form_section.get("radio_checkbox_questions", []) if "question" in q]
            resume_questions = [q["name"] for q in form_section.get("resume_questions", []) if "name" in q]
            
            # Check if radio_checkbox_questions is a list of strings or objects
            if isinstance(form_section.get("radio_checkbox_questions", []), list) and form_section.get("radio_checkbox_questions", []):
                first_item = form_section.get("radio_checkbox_questions", [])[0]
                if isinstance(first_item, str):
                    # It's a list of strings, use directly
                    radio_checkbox_questions = form_section.get("radio_checkbox_questions", [])
                else:
                    # It's a list of objects, extract question field
                    radio_checkbox_questions = [q["question"] for q in form_section.get("radio_checkbox_questions", []) if "question" in q]

            if question in input_questions:
                return "input_text_question"
            elif question in dropdown_questions:
                # For dropdown questions, options will be extracted separately by dropdown_extractor
                # Since dropdown_questions are now strings, we don't extract options here
                self.options = []
                return "dropdown_question"
            elif question in radio_checkbox_questions:
                return "radio_checkbox_question"
            elif question in resume_questions:
                return "resume_question"
            else:
                # Fall back if it's not found in any section
                return "input_text_question"

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"DEBUG: Error parsing JSON or accessing data: {e}")
            return "input_text_question"
    
    def __str__(self) -> str:
        """Return the string representation of the question."""
        return self.question
    
    def __repr__(self) -> str:
        """Return the string representation of the question element."""
        return f"QuestionElement(question='{self.question}', question_type='{self.question_type}')"


class WebElement:
    """Class to represent a web element with its name and locator."""
    
    def __init__(self, name: str, locator: Optional[Any] = None):
        """Initialize a WebElement with a name and optional locator.
        
        Args:
            name: The string representation or name of the element
            locator: Optional Playwright Locator object
        """
        self.name = name
        self.locator = locator
    
    def __str__(self) -> str:
        """Return the string representation of the element."""
        return self.name
    
    def __repr__(self) -> str:
        """Return the string representation of the element."""
        return f"WebElement(name='{self.name}', locator={self.locator})"