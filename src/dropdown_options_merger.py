#!/usr/bin/env python3
"""
Sample Dropdown Extractor Merge

This script demonstrates how to merge dropdown options from dropdown_extractor.py
with dropdown questions from the question extraction system.
"""

import json

def merge_dropdown_data(question_data, dropdown_options):
    """
    Merge dropdown questions with their corresponding options.
    
    Args:
        question_data: Dictionary containing form questions including dropdown_questions
        dropdown_options: List of lists containing options for each dropdown
    
    Returns:
        Updated question_data with dropdown_questions containing question and options
    """
    # Create a copy to avoid modifying the original
    merged_data = json.loads(json.dumps(question_data))
    
    # Get the dropdown questions
    dropdown_questions = merged_data["form"]["dropdown_questions"]
    
    # Create new dropdown structure with questions and options
    merged_dropdowns = []
    
    for i, question in enumerate(dropdown_questions):
        # Get corresponding options (if available)
        options = dropdown_options[i] if i < len(dropdown_options) else []
        
        merged_dropdown = {
            "question": question,
            "options": options
        }
        merged_dropdowns.append(merged_dropdown)
    
    # Replace the dropdown_questions with the merged structure
    merged_data["form"]["dropdown_questions"] = merged_dropdowns
    
    return merged_data

if __name__ == "__main__":
    # Hardcoded dropdown options from dropdown_extractor.py output
    dropdown_options = [
        [
            "Select ...",
            "Male",
            "Female",
            "Decline to self-identify"
        ],
        [
            "Select ...",
            "Hispanic or Latino",
            "White (Not Hispanic or Latino)",
            "Black or African American (Not Hispanic or Latino)",
            "Native Hawaiian or Other Pacific Islander (Not Hispanic or Latino)",
            "Asian (Not Hispanic or Latino)",
            "American Indian or Alaska Native (Not Hispanic or Latino)",
            "Two or More Races (Not Hispanic or Latino)",
            "Decline to self-identify"
        ],
        [
            "Select ...",
            "I am a veteran",
            "I am not a veteran",
            "Decline to self-identify"
        ]
    ]

    # Hardcoded sample JSON from question extraction system
    question_data = {
        "form": {
            "input_text_questions": [
                "Full name",
                "Email",
                "Phone",
                "Current location",
                "Current company",
                "LinkedIn URL",
                "GitHub URL",
                "Portfolio URL",
                "Other website",
                "Add a cover letter or anything else you want to share."
            ],
            "dropdown_questions": [
                "Gender",
                "Race",
                "Veteran status"
            ],
            "radio_checkbox_questions": [],
            "resume_questions": [
                {
                    "name": "Resume/CV",
                    "buttons": [
                        "ATTACH RESUME/CV"
                    ]
                }
            ]
        }
    }

    print("Original question data:")
    print(json.dumps(question_data, indent=2))
    
    print("\nDropdown options:")
    print(json.dumps(dropdown_options, indent=2))
    
    # Merge the data
    merged_result = merge_dropdown_data(question_data, dropdown_options)
    
    print("\nMerged result:")
    print(json.dumps(merged_result, indent=2))
    
    # Show just the dropdown_questions section
    print("\nDropdown questions section only:")
    print(json.dumps(merged_result["form"]["dropdown_questions"], indent=2))