import os
import json
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from models import ElementMatchResponse
from elements import QuestionElement, WebElement

class QuestionMapperAgent:
    """
    AI-powered agent that maps job application questions to form elements.
    
    This agent takes a list of questions and form elements and determines which
    elements correspond to which questions by sequentially analyzing each element
    and determining if it should be mapped to the current question using an LLM.
    """

    def __init__(
        self,
    ) -> None:
        # Explicitly load environment variables
        load_dotenv()
        model = "gpt-4.1-mini"
        self.model = model
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        print(f"DEBUG: OPENAI_API_KEY is {'set' if openai_api_key else 'not set'}")
        if openai_api_key:
            print(f"DEBUG: API key length: {len(openai_api_key)}, first 5 chars: {openai_api_key[:5]}")
        
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        
        try:
            print(f"DEBUG: Initializing OpenAI client with model={model}")
            self.client = OpenAI(
                api_key=openai_api_key,
                timeout=60.0,  # timeout in seconds
                max_retries=2,
            )
            print("DEBUG: OpenAI client initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Error initializing OpenAI client: {e}")
            
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the question mapper agent.
        """
        from question_mapper_agent_prompt import get_system_prompt
        return get_system_prompt()

    def is_element_for_question(self, question: QuestionElement, element: Any, all_extracted_elements: List[str], application_form_json: str) -> Tuple[bool, bool]:
        """
        Determine if a form element corresponds to a specific question using the LLM.
        
        Args:
            question: The QuestionElement object containing question text and type
            element: The form element (can be string or Locator object)
            all_extracted_elements: List of all form element label/placeholder text extracted from the job application form, ordered by appearance
            application_form_json: JSON string containing a visualization of the job application form
            
        Returns:
            A tuple of (element_for_question, next_mapping)
            - element_for_question: True if the element corresponds to the question, False otherwise
            - next_mapping: True if we should end mapping for this question and move to the next one (can only be true if element_for_question is true)
        """
        # Convert element to string if it's not already
        element_str = str(element)
        
        # Format user message according to the prompt specification
        user_msg = f"Question: {question.question} (Type: {question.question_type})\nElement: {element_str}\nAll Extracted Elements: {all_extracted_elements}\nApplication Form: {application_form_json}"
        
        print(f"\nSending request to LLM for:\nQuestion: {question.question} (Type: {question.question_type})\nElement: {element_str}")
        
        try:
            # Create messages for the API call
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_msg}
            ]
            
            # Use client.responses.parse with the ElementMatchResponse Pydantic model
            # This automatically handles prompt caching
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "element_match_response",
                        "schema": ElementMatchResponse.model_json_schema()
                    }
                },
                temperature=0.1
            )
            
            # Get the parsed response
            parsed_response = response.choices[0].message.content # Gets the json
            parsed_response = ElementMatchResponse.model_validate_json(parsed_response) # Converts json to object
            
            print(f"Parsed response: {parsed_response.element_for_question}, (Next Mapping: {parsed_response.next_mapping}, Reasoning: {parsed_response.reasoning})")
            return parsed_response.element_for_question, parsed_response.next_mapping
                
        except Exception as e:
            error_msg = str(e)
            if "rate_limit_exceeded" in error_msg.lower():
                print("Error: OpenAI API rate limit exceeded. Please try again later.")
            else:
                print(f"Error calling OpenAI API: {e}")
            # Re-raise the exception to be handled by the caller
            raise e

    def map_questions_to_elements(self, questions: List[str], element_strings: List[str], element_locators: List[Any] = None, application_form_json: str = "") -> Dict[QuestionElement, List[WebElement]]:
        """
        Map questions to form elements.
        
        Args:
            questions: List of question strings.
            element_strings: List of form element HTML tag strings for comparison.
            element_locators: Optional parallel list of Playwright Locator objects corresponding to element_strings.
                             If None, element_strings will be used in the result.
            application_form_json: JSON string containing a visualization of the job application form.
            
        Returns:
            Dictionary mapping QuestionElement objects to lists of WebElement objects that contain both the element name and locator.
        """
        result = {}
        current_index = 0
        total_elements = len(element_strings)
        endpoint = False
        
        for question_str in questions:
            if endpoint:
                break
            question_element = QuestionElement(question_str, application_form_json)
            result[question_element] = []
            
            # Start from current_index and try to map elements to this question
            while current_index < total_elements:
                element_string = element_strings[current_index].strip()
                
                # Check if this element's name is the same as the submit button question on the application_form_json
                form_data = json.loads(application_form_json)
                submit_button_text = form_data.get("form", {}).get("submit_button_question")
                if submit_button_text and element_string == submit_button_text:
                    endpoint = True
                    break
                # Check if this element is already mapped to this question
                if element_string is not None and any(element_string == str(e) for e in result[question_element]):
                    break
                try:
                    element_for_question, next_mapping = self.is_element_for_question(question_element, element_string, element_strings, application_form_json)
                    # Check if this element corresponds to the current question using the string representation
                    if element_for_question:
                        # Create a WebElement with name and locator
                        locator = None if element_locators is None else element_locators[current_index]
                        web_element = WebElement(name=element_string, locator=locator)
                        result[question_element].append(web_element)
                        current_index += 1
                        if next_mapping:
                            break
                    else:
                        # If element was rejected and current question has no mapped elements,
                        # skip this element and continue to next element for this question
                        if len(result[question_element]) == 0:
                            current_index += 1
                            continue
                        else:
                            # If question already has mapped elements, move to the next question
                            break
                except Exception as e:
                    print(f"Error determining if element matches question: {e}")
                    # Move to the next element if there's an error
                    current_index += 1
        
        # Handle any remaining elements by trying to map them to the most appropriate question
        # Lets not waste money on remaining elements just make the LLM better so that all remaining elements are not needed
        # if current_index < total_elements:
        #     for i in range(current_index, total_elements):
        #         element_string = element_strings[i].strip()
        #         best_match = None
                
        #         for question in questions:
        #             try:
        #                 if element_string is not None and any(element_string == str(e) for e in result[question]):
        #                     continue
        #                 element_for_question, next_mapping = self.is_element_for_question(question, element_string, element_strings, application_form_json)
        #                 if element_for_question:
        #                     best_match = question
        #                     break
        #             except Exception as e:
        #                 print(f"Error determining if element matches question: {e}")
        #                 continue
                
        #         if best_match:
        #             # Create a WebElement with name and locator
        #             locator = None if element_locators is None else element_locators[i]
        #             web_element = WebElement(name=element_string, locator=locator)
        #             result[best_match].append(web_element)
        #         else:
        #             # If no match found, skip this element
        #             pass
        
        return result


if __name__ == "__main__":
    # Example usage
    mapper = QuestionMapperAgent()
    
    # Example data
    questions = [
      "Full Name*",
      "Email*",
      "Phone*",
      "Location*",
      "Resume*",
      "LinkedIn Profile*",
      "What pronouns would you like our team to use when addressing you?",
      "Notion is an in person company, and currently requires its employees to come to the office for two Anchor Days (Mondays & Thursdays) and requests that employees spend the majority of their week in the office (including a third day). Notion reserves the right to adjust these requirements, and wants to ensure that you understand that we prioritize your presence for the magic of in person collaboration. Notion will consider requests for accommodation to this policy, and, upon request, will work with employees to explore a reasonable accommodation for physical or mental disabilities or other reasons recognized by applicable law. Please confirm that you have read and understand Notion\u2019s in office requirements and policy.*",
      "Will you now or in the future require Notion to sponsor an immigration case in order to employ you?*",
      "How did you hear about this opportunity? (select all that apply)",
      "Gender",
      "Race",
      "Veteran Status"
    ]
    
    elements = [
      "Type here...",
      "hello@example.com...",
      "1-415-555-1234...",
      "Start typing...",
      "Upload File",
      "Type here...",
      "He/Him",
      "She/Her",
      "They/Them",
      "Prefer not to say",
      "Not represented here",
      "Yes",
      "No",
      "Yes",
      "No",
      "LinkedIn",
      "Glassdoor",
      "Notion Blog",
      "Notion Employee",
      "Notion Website",
      "Billboard/Outdoor Ads",
      "Conference or Meetup",
      "Male",
      "Female",
      "Decline to self-identify",
      "Hispanic or Latino",
      "White (Not Hispanic or Latino)",
      "Black or African American (Not Hispanic or Latino)",
      "Native Hawaiian or Other Pacific Islander (Not Hispanic or Latino)",
      "Asian (Not Hispanic or Latino)",
      "American Indian or Alaska Native (Not Hispanic or Latino)",
      "Two or More Races (Not Hispanic or Latino)",
      "Decline to self-identify",
      "I identify as one or more of the classifications of protected veteran listed above",
      "I am not a protected veteran",
      "I decline to self-identify for protected veteran status",
    ]

    application_form_json = {
        "form": {
            "application_form_questions": [
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Resume/CV",
            "LinkedIn Profile",
            "Other Website",
            "Why do you want to join Figma?",
            "Pronouns",
            "Additional Information",
            "From where do you intend to work?",
            "Preferred First Name",
            "Are you authorized to work in the country for which you applied?",
            "Have you ever worked for Figma before, as an employee or a contractor/consultant?",
            "Gender",
            "Are you Hispanic/Latino?",
            "Veteran Status",
            "Disability Status"
            ],
            "input_text_questions": [
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "LinkedIn Profile",
            "Other Website",
            "Why do you want to join Figma?",
            "Additional Information",
            "From where do you intend to work?",
            "Preferred First Name"
            ],
            "dropdown_questions": [
            "Pronouns",
            "Are you authorized to work in the country for which you applied?",
            "Have you ever worked for Figma before, as an employee or a contractor/consultant?",
            "Gender",
            "Are you Hispanic/Latino?",
            "Veteran Status",
            "Disability Status"
            ],
            "radio_checkbox_questions": [],
            "resume_questions": [
            {
                "name": "Resume/CV",
                "buttons": [
                "Attach",
                "Dropbox",
                "Google Drive",
                "Enter manually"
                ]
            }
            ],
            "submit_button_question": "Submit application"
        }
    }
    
    # Get mapping
    mapping = mapper.map_questions_to_elements(questions, elements, None, application_form_json)
    
    # Print results
    print("\nQuestion to Element Mapping:")
    for question_element, mapped_elements in mapping.items():
        print(f"\n{question_element.question} (Type: {question_element.question_type}):")
        for element in mapped_elements:
            print(f"  - {element.name} (locator: {element.locator})")