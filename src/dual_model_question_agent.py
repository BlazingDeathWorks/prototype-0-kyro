import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from question_agent_prompt import build_system_prompt
from creative_agent_prompt import build_creative_system_prompt
from models import QuestionResponse
from google import genai
from google.genai import types


class DualModelApplicationQuestionAgent:
    """
    LLM-powered agent that answers job application questions using user_info.json.
    
    - Uses Gemini gemini-3-pro-preview for main question answering with structured output
    - Uses Gemini 2.5-flash-lite for creative responses
    - Temperature: 0.1 for deterministic, reproducible outputs.
    """

    def __init__(
        self,
        user_info_path: str = "user_info.json",
        main_model: str = "gemini-2.5-pro",  # Gemini model for main responses
        creative_model: str = "gemini-2.5-flash-lite",  # Gemini model for creative responses
    ) -> None:
        load_dotenv()
        self.user_info_path = user_info_path
        self.main_model = main_model
        self.creative_model = creative_model

        # Initialize Gemini client for both main and creative responses
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        self.user_info = self._load_user_info(user_info_path)
        self.system_prompt = self._build_system_prompt(self.user_info)

    def _load_user_info(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"user_info.json not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_system_prompt(self, user_info: Dict[str, Any]) -> str:
        """Use the imported build_system_prompt function."""
        return build_system_prompt(user_info)
    
    def _generate_creative_response(self, question: str, extra_context: Optional[str] = None) -> str:
        """Generate a creative response using gemini-2.5-flash-lite with higher temperature."""
        creative_prompt = build_creative_system_prompt(question, self.user_info)
        
        user_msg = (
            "Question: " + question.strip() + 
            (f"\nContext: {extra_context}" if extra_context else "")
        )
        
        try:
            response = self.gemini_client.models.generate_content(
                model=self.creative_model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=creative_prompt,
                    temperature=0.6,
                    max_output_tokens=2048,
                ),
            )
            
            if response.text is None:
                return "Unable to generate creative response"
            
            return response.text.strip()
            
        except Exception as e:
            return f"Error generating creative response: {str(e)}"

    def answer_question(self, question: str, extra_context: Optional[str] = None) -> QuestionResponse:
        """Ask the LLM to answer a form question using the user profile with structured output."""
        if not question or not question.strip():
            return QuestionResponse(
                response="",
                creative_mode=False,
                reasoning="Empty question provided"
            )
        
        qnorm = question.strip().lower().rstrip("?.!")
        if qnorm == "how did you hear about us":
            return QuestionResponse(
                response="LinkedIn",
                creative_mode=False,
                reasoning="Hard-coded response rule applied"
            )
        
        user_msg = (
            "Question: " + question.strip() + 
            (f"\nContext: {extra_context}" if extra_context else "")
        )
        
        try:
            # Use Gemini API with structured JSON output
            response = self.gemini_client.models.generate_content(
                model=self.main_model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.1,
                    max_output_tokens=2048,
                    response_mime_type='application/json',
                    response_schema=QuestionResponse,
                ),
            )
            
            # Handle case where response content might be None
            if response.text is None:
                return QuestionResponse(
                    response="",
                    creative_mode=False,
                    reasoning="LLM returned empty response"
                )
            
            # Parse the structured response
            try:
                response_text = response.text.strip()
                response_dict = json.loads(response_text)
                initial_response = QuestionResponse(**response_dict)
                
                # If creative_mode is true, generate creative response
                if initial_response.creative_mode:
                    creative_text = self._generate_creative_response(question, extra_context)
                    return QuestionResponse(
                        response=creative_text,
                        creative_mode=True,
                        reasoning=f"Creative response generated: {initial_response.reasoning}"
                    )
                
                return initial_response
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                return QuestionResponse(
                    response="Error: Unable to parse response",
                    creative_mode=False,
                    reasoning=f"LLM returned non-JSON response: {str(e)}"
                )
                
        except Exception as e:
            return QuestionResponse(
                response="",
                creative_mode=False,
                reasoning=f"Error occurred: {str(e)}"
            )


if __name__ == "__main__":
    import sys

    agent = DualModelApplicationQuestionAgent()
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        response = agent.answer_question(question)
        print(f"Response: {response.response}")
        print(f"Creative Mode: {response.creative_mode}")
        print(f"Reasoning: {response.reasoning}")
    else:
        print("Enter application questions. Type 'quit' to exit.")
        while True:
            question = input("\nQuestion: ")
            if question.lower() == "quit":
                print("Exiting...")
                break
            
            response = agent.answer_question(question)
            print(f"\nResponse: {response.response}")
            print(f"Creative Mode: {response.creative_mode}")
            print(f"Reasoning: {response.reasoning}")
