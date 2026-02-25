from firecrawl import Firecrawl
from dotenv import load_dotenv
import os
import json
from pydantic import BaseModel
from typing import List, Optional

load_dotenv()

firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

URL = "https://job-boards.eu.greenhouse.io/nice/jobs/4654114101?gh_jid=4654114101"

# Define Pydantic models for job application questions
class JobApplicationQuestion(BaseModel):
    question_text: str
    html_element_type: str  # text_input, textarea, dropdown, radio, checkbox, file_upload, date, email, phone, url, number
    options: Optional[List[str]] = []

class JobApplicationQuestions(BaseModel):
    job_application_questions: List[JobApplicationQuestion]

# Convert Pydantic model to JSON schema for Firecrawl
schema = JobApplicationQuestions.model_json_schema()

# Define extraction prompt
prompt = """
You are analyzing a job application webpage. Extract ALL questions that job applicants need to answer to complete their application.

Look for questions in these formats:
1. Direct questions ending with "?" (e.g., "Would you need a visa / work permit for the role?")
2. Form field labels (e.g., "Full Name", "Email Address", "Phone Number")
3. Dropdown selections (e.g., "Select your location", "Choose your experience level")
4. Yes/No questions
5. Multiple choice questions
6. File upload prompts (e.g., "Upload your resume", "Attach cover letter")
7. Text areas for longer responses
8. Demographic questions (race, gender, veteran status, disability status)
9. Legal/compliance questions

For each question found, determine:
- question_text: The exact text of the question or field label
- html_element_type: Best guess based on the question type:
  * text_input: for name, address, short text fields
  * email: for email addresses
  * phone: for phone numbers
  * textarea: for long text responses, cover letters, additional info
  * dropdown: for selection lists, location choices, experience levels
  * radio: for yes/no questions, single choice options
  * checkbox: for multiple selection options, demographic categories
  * file_upload: for resume, document uploads
  * date: for date fields
  * url: for website/LinkedIn profile links
- options: List any visible options for dropdowns, radio buttons, or checkboxes

Include questions from:
- Basic application info (name, contact, location)
- Work authorization/visa questions
- Experience and qualifications
- Demographic and EEO information
- Veteran status questions
- Disability status questions
- Any other application-related questions

Do NOT include:
- Page navigation links
- Company information
- Job descriptions
- Submit buttons
- Legal disclaimers (unless they contain questions)
"""

# Extract structured data using schema and prompt
try:
    # First, scrape with both markdown and HTML to get complete content
    scrape_result = firecrawl.scrape(
        url=URL,
        formats=['markdown', 'rawHtml'],
        only_main_content=False,
        include_tags=['form', 'input', 'select', 'textarea', 'button', 'label', 'div', 'button'],
        wait_for=5000
    )
    
    # Now use extract method with the enhanced content
    result = firecrawl.extract(
        urls=[URL],
        schema=schema,
        prompt=prompt,
    )
    
    # Convert ExtractResponse to dict for JSON serialization
    if hasattr(result, '__dict__'):
        result_dict = result.__dict__
    else:
        result_dict = dict(result)
    
    # Save extracted data
    with open('job_application_questions.json', 'w') as f:
        json.dump(result_dict, f, indent=2)
    
    # Count questions
    questions = result_dict.get('data', [{}])[0].get('job_application_questions', [])
    print(f"Job application questions extracted and saved to job_application_questions.json")
    print(f"Found {len(questions)} questions")
    
except Exception as e:
    print(f"Extraction failed: {e}")
    print("Content saved as markdown and HTML for manual review")
