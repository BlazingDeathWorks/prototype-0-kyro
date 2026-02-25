import os
import json
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types
import tiktoken
from models import OnePromptMappingResponse, QuestionMapping
from elements import QuestionElement, WebElement

class OnePromptQuestionMapperAgent:
    """
    Experimental AI-powered agent that maps ALL job application questions to form elements in a single LLM call.
    
    This agent takes complete lists of questions and form elements and determines the full mapping
    between them using a single comprehensive LLM analysis to reduce costs and improve efficiency.
    """

    def __init__(self) -> None:
        # Explicitly load environment variables
        load_dotenv()
        model = "gemini-2.5-flash"
        self.model = model
        
        # Get Google API key
        google_api_key = os.getenv("GEMINI_API_KEY")
        print(f"DEBUG: GOOGLE_API_KEY is {'set' if google_api_key else 'not set'}")
        if google_api_key:
            print(f"DEBUG: API key length: {len(google_api_key)}, first 5 chars: {google_api_key[:5]}")
        
        if not google_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
        try:
            print(f"DEBUG: Initializing Google Gemini client with model={model}")
            self.client = genai.Client(api_key=google_api_key)
            print("DEBUG: Google Gemini client initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Error initializing Google Gemini client: {e}")
            
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the one-prompt question mapper agent.
        """
        from one_prompt_agent_prompt import get_system_prompt
        return get_system_prompt()

    def map_all_questions_to_elements(self, question_elements: List[QuestionElement], web_elements: List[str], element_locators: List[Any] = None) -> Dict[QuestionElement, List[WebElement]]:
        """
        Map all questions to form elements in a single LLM call.
        
        Args:
            question_elements: List of QuestionElement objects with question text and types
            web_elements: List of web element names/labels
            element_locators: Optional parallel list of Playwright Locator objects corresponding to web_elements.
                             If None, web_elements will be used in the result.
            
        Returns:
            Dictionary mapping QuestionElement objects to lists of WebElement objects that contain both the element name and locator.
        """
        # Format user message with question types
        questions_text = "\n".join([
            f"{i+1}. {qe.question} (Type: {qe.question_type})"
            for i, qe in enumerate(question_elements)
        ])
        elements_text = "\n".join([f"{i+1}. {e}" for i, e in enumerate(web_elements)])
        
        user_msg = f"""List of questions with their types:
{questions_text}

List of web elements:
{elements_text}"""
        
        # Calculate token usage
        encoding = tiktoken.encoding_for_model("gpt-4")  # Use GPT-4 encoding as approximation for Gemini
        system_tokens = len(encoding.encode(self.system_prompt))
        user_tokens = len(encoding.encode(user_msg))
        total_tokens = system_tokens + user_tokens
        
        print(f"\n📊 TOKEN USAGE ANALYSIS:")
        print(f"System prompt tokens: {system_tokens:,}")
        print(f"User message tokens: {user_tokens:,}")
        print(f"Total input tokens: {total_tokens:,}")
        print(f"\n📋 USER MESSAGE SAMPLE:")
        print(f"First 500 characters of user input:")
        print(f"{user_msg}...")
        
        print(f"\nSending request to LLM for mapping {len(question_elements)} questions to {len(web_elements)} elements")
        
        try:
            # Use Gemini's generate_content method
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=OnePromptMappingResponse,
                    system_instruction=self.system_prompt,
                )
            )
            
            # Get the parsed response
            response_text = response.text
            parsed_response = OnePromptMappingResponse.model_validate_json(response_text)
            
            print(f"\nReceived mapping for {len(parsed_response.mappings)} questions")
            print(f"Reasoning: {parsed_response.reasoning}")
            
            # Convert list of QuestionMapping to dictionary format with QuestionElement keys and WebElement values
            mappings_dict = {}
            # Track element name occurrences to handle duplicates
            element_name_counts = {}
            
            for question_element in question_elements:
                # Find the mapping for this question
                question_mapping = None
                for mapping in parsed_response.mappings:
                    if mapping.question == question_element.question:
                        question_mapping = mapping
                        break
                
                # Create WebElement objects for the mapped elements
                web_element_list = []
                if question_mapping:
                    for element_name in question_mapping.elements:
                        # Track occurrence count for this element name
                        if element_name not in element_name_counts:
                            element_name_counts[element_name] = 1
                        else:
                            element_name_counts[element_name] += 1
                        
                        # Find the correct index based on occurrence count
                        locator = None
                        if element_locators is not None:
                            try:
                                # Find all indices where this element name appears
                                matching_indices = [i for i, elem in enumerate(web_elements) if elem == element_name]
                                
                                # Select the appropriate occurrence based on count
                                occurrence_index = element_name_counts[element_name] - 1
                                if occurrence_index < len(matching_indices):
                                    element_index = matching_indices[occurrence_index]
                                    locator = element_locators[element_index]
                                    print(f"Mapping element '{element_name}' occurrence {element_name_counts[element_name]} to index {element_index}")
                                else:
                                    print(f"Warning: Not enough occurrences of '{element_name}' found. Requested occurrence {element_name_counts[element_name]}, but only {len(matching_indices)} found.")
                            except Exception as e:
                                print(f"Error finding element '{element_name}': {e}")
                        
                        web_element = WebElement(name=element_name, locator=locator)
                        web_element_list.append(web_element)
                
                mappings_dict[question_element] = web_element_list
            
            return mappings_dict
                
        except Exception as e:
            error_msg = str(e)
            if "rate_limit_exceeded" in error_msg.lower() or "quota" in error_msg.lower():
                print("Error: Google Gemini API rate limit exceeded. Please try again later.")
            else:
                print(f"Error calling Google Gemini API: {e}")
            # Re-raise the exception to be handled by the caller
            raise e


if __name__ == "__main__":
    # Sample application form JSON structure for QuestionElement initialization
    sample_form_json = json.dumps({
        "form": {
            "application_form_questions": [
            "Name*",
            "Email*",
            "Resume*",
            "Portfolio or additional information",
            "LinkedIn URL",
            "Why do you believe you are well-suited to assist Reframe System in accomplishing its mission?*",
            "Anything else you would like to tell us?"
            ],
            "input_text_questions": [
            "Name*",
            "Email*",
            "LinkedIn URL",
            "Why do you believe you are well-suited to assist Reframe System in accomplishing its mission?*",
            "Anything else you would like to tell us?"
            ],
            "dropdown_questions": [],
            "radio_checkbox_questions": [],
            "resume_questions": [
            {
                "name": "Resume*",
                "buttons": [
                "Upload File"
                ]
            },
            {
                "name": "Portfolio or additional information",
                "buttons": [
                "Upload File"
                ]
            }
            ],
            "submit_button_question": "Submit Application"
        }
    })
    
    # Test data from user input
    web_elements = [
      "First Name", 
      "Last Name",
      "Email",
      "Toggle flyout",
      "Select",
      "Toggle flyout",
      "Select",
      "Toggle flyout",
      "Select",
      "Toggle flyout",
      "Select"
    ]
    
    # Create QuestionElement objects with proper question types
    question_strings = [
      "First Name",
      "Last Name",
      "Email",
      "Requesting visa?",
      "How did you find us?",
      "Which company are you affiliated with?",
      "Location"
    ]
    
    # Create QuestionElement objects
    question_elements = [QuestionElement(q, sample_form_json) for q in question_strings]
    
    # Create agent and get mapping
    agent = OnePromptQuestionMapperAgent()
    mapping = agent.map_all_questions_to_elements(question_elements, web_elements)
    
    # Print results
    print("\n" + "="*80)
    print("QUESTION TO ELEMENT MAPPING RESULTS:")
    print("="*80)
    
    for question_element, web_element_list in mapping.items():
        print(f"\n📋 {question_element.question}:")
        if web_element_list:
            for web_element in web_element_list:
                print(f"  ✓ {web_element.name}")
        else:
            print(f"  ❌ No elements mapped")
    
    print(f"\n📊 SUMMARY:")
    print(f"Total questions: {len(question_elements)}")
    print(f"Total web elements: {len(web_elements)}")
    print(f"Questions with mappings: {len([q for q, e in mapping.items() if e])}")
    print(f"Total element mappings: {sum(len(e) for e in mapping.values())}")