#!/usr/bin/env python3
"""
OpenAI Image Token Calculator

This script takes an image from the snapshots folder, sends it to OpenAI's GPT-4o mini
with a question, and returns both the response and token usage information.

Usage:
    from image_token_calculator import ImageTokenCalculator
    calculator = ImageTokenCalculator()
    result = calculator.analyze_image("screenshot.png", "What do you see in this image?")

Example:
    calculator = ImageTokenCalculator()
    result = calculator.analyze_image("screenshot.png", "What do you see in this image?")
"""

import os
import sys
import base64
from pathlib import Path
from typing import Dict, Any

import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ImageTokenCalculator:
    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self.snapshots_dir = Path(__file__).parent.parent / 'snapshots'
        
    def encode_image(self, image_path: Path) -> str:
        """Encode image to base64 string."""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error encoding image: {e}")
    
    def get_image_mime_type(self, image_path: Path) -> str:
        """Get the MIME type based on file extension."""
        extension = image_path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(extension, 'image/png')
    
    def analyze_image(self, image_filename: str, question: str) -> Dict[str, Any]:
        """Send image to OpenAI GPT-4o mini and get response with token usage."""
        # Check if OpenAI API key is set
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable not set. Please set your OpenAI API key in the .env file.")

        # Construct image path
        image_path = self.snapshots_dir / image_filename
        
        if not image_path.exists():
            available_images = [f.name for f in self.snapshots_dir.iterdir() 
                              if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']]
            error_msg = f"Image not found: {image_path}\nAvailable images: {', '.join(available_images)}"
            raise FileNotFoundError(error_msg)
        
        # Encode image
        base64_image = self.encode_image(image_path)
        mime_type = self.get_image_mime_type(image_path)
        
        try:
            # Make API call to GPT-4o mini
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": question
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            # Extract response and usage information
            result = {
                'image_path': str(image_path),
                'question': question,
                'response': response.choices[0].message.content,
                'model': response.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                },
                'finish_reason': response.choices[0].finish_reason
            }
            
            return result
            
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {e}")
    
    def print_results(self, result: Dict[str, Any]):
        """Print the results in a formatted way."""
        print("=" * 60)
        print("OpenAI Image Analysis Results")
        print("=" * 60)
        print(f"Image: {result['image_path']}")
        print(f"Model: {result['model']}")
        print(f"Question: {result['question']}")
        print("\n" + "-" * 40)
        print("RESPONSE:")
        print("-" * 40)
        print(result['response'])
        print("\n" + "-" * 40)
        print("TOKEN USAGE:")
        print("-" * 40)
        print(f"Prompt tokens: {result['usage']['prompt_tokens']}")
        print(f"Completion tokens: {result['usage']['completion_tokens']}")
        print(f"Total tokens: {result['usage']['total_tokens']}")
        print(f"Finish reason: {result['finish_reason']}")
        print("=" * 60)

# Example usage
if __name__ == "__main__":
    calculator = ImageTokenCalculator()
    try:
        result = calculator.analyze_image("1_screen.png", "What HTML input element is this and what are the options for a response to this application question?")
        calculator.print_results(result)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
