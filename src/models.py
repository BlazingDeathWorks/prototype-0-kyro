from pydantic import BaseModel, Field
from typing import Literal, Optional


class ElementMatchResponse(BaseModel):
    """Pydantic model for structured LLM response"""
    element_for_question: bool = Field(description="Whether the element corresponds to the question")
    next_mapping: bool = Field(description="Whether we should end mapping for this question and move to the next one (can only be true if element_for_question is true)")
    reasoning: str = Field(description="Reasoning behind the decision for why the element is or is not a match for the question and why we should or should not continue finding new mappings for this question")

class QuestionResponse(BaseModel):
    """Pydantic model for question agent response with creative mode"""
    response: str = Field(description="The response to the question")
    creative_mode: bool = Field(description="Whether creative mode is needed for this response")
    reasoning: str = Field(description="The reasoning behind the response and why creative_mode is true or false")

class QuestionMapping(BaseModel):
    """Individual question to elements mapping"""
    question: str = Field(description="The question text")
    elements: list[str] = Field(description="List of web element names that correspond to this question")

class OnePromptMappingResponse(BaseModel):
    """Pydantic model for one-prompt question to element mapping response"""
    mappings: list[QuestionMapping] = Field(description="List of question to element mappings")
    reasoning: str = Field(description="Detailed reasoning explaining every mapping decision made")

# class QuestionVariableResponse(BaseModel):
#     """Pydantic model for question agent structured output"""
#     suggestions: list[str] = Field(description="List of string suggestions or ideas")
#     reasoning: str = Field(description="Reasoning behind the provided suggestions")
#     creative_mode: bool = Field(description="Whether creative mode is enabled for this response")
    
# class SecurityTemplateType(BaseModel):
#     """Pydantic model for determining which security template to use"""
#     template_type: Literal["secured_question", "non_secured_question"] = Field(
#         description="Specifies whether to use secured or non-secured template for answering questions"
#     )

# Job Application Form Models
class ResumeQuestion(BaseModel):
    """Pydantic model for resume/cover letter upload questions"""
    name: str = Field(description="The name or text of the resume question")
    buttons: list[str] = Field(description="List of buttons associated with the question")

class ExtractedQuestion(BaseModel):
    """Pydantic model for a question with metadata"""
    question_name: str = Field(description="The question text/label")
    section: Optional[str] = Field(
        default=None,
        description="The section this question belongs to (e.g., 'Work Experience', 'Education', 'Websites'). Only for 'My Experience' pages."
    )
    date_format: Optional[str] = Field(
        default=None,
        description="The expected date format for date-related questions (e.g., 'MM/YYYY', 'MM/DD/YYYY', 'YYYY'). Only populated for date, from, to, or similar date input questions."
    )

class ApplicationFormQuestions(BaseModel):
    """Pydantic model for all job application form questions"""
    application_page_title: Optional[str] = Field(
        default="Application",
        description="The heading title that describes the topic/type of information the applicant needs to provide for this specific page such as 'My Information', 'My Experience', 'Voluntary Disclosures', 'Application Questions', 'Review', etc."
    )
    
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        # Ensure null values are converted to default
        super().__pydantic_init_subclass__(**kwargs)
    
    def model_post_init(self, __context) -> None:
        # Convert None to default value
        if self.application_page_title is None:
            self.application_page_title = "Application"
    all_application_form_questions: list[ExtractedQuestion] = Field(
        description="All form questions with metadata including section and date format"
    )
    input_text_questions: list[str] = Field(
        description="Questions that are tied to the application form text input or text area elements"
    )
    dropdown_questions: list[str] = Field(
        description="Questions tied to dropdown elements"
    )
    radio_checkbox_questions: list[str] = Field(
        description="Questions tied to radio or checkbox button groups"
    )
    resume_questions: list[ResumeQuestion] = Field(
        description="Questions about uploading resume or cover letter with associated buttons"
    )

class JobApplicationForm(BaseModel):
    """Pydantic model for the complete job application form structure"""
    form: ApplicationFormQuestions = Field(
        description="All job application form fields: text inputs, textarea, file uploads, dropdowns, buttons, and radio/checkbox groups"
    )