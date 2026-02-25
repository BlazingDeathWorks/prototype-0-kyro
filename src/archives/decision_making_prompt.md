      # Decision Making
      When deciding if an element belongs to a question:

      - Consider the **job application context**. The question is the one shown to the applicant, while the element is the label, placeholder, or visible field that captures the applicant’s response.

      - First consider if the element's text makes more sense for it to be a response or an input placeholder to the question.
      - Check if the **label/placeholder** provides natural affordance for the question (e.g., “Type here…” fits “Full Name”, “Upload File” fits “Resume”).
      - Also check if the **label/placeholder** provides uncommon but valid options for the question (e.g., “Not represented here” fits “Gender”).

      - Treat all labels, placeholders, and visible option texts appropriately based on the element type:
        - **Single input elements** (a text input or textarea where user actively types their response):
          - The displayed text is usually **placeholder or guidance**, not a candidate answer.
          - If the user is expected to type the answer to the question given all the context, the element should be treated as a single input element
          - Use the placeholder only to infer the expected type of input, not to validate an actual answer.
          - `next_mapping` can be set to true once the element is mapped, because these elements cannot have additional options.
        - **Multiple input elements** (radio buttons, checkboxes, dropdown options, button groups, and confirmation buttons/checkboxes where user has to click for a choice):
          - The displayed text represents **actual selectable options**, which are valid potential answers.
          - If the user is expected to select or act on the response rather than type, the element should be treated as a multiple input element.
          - Evaluate whether the text corresponds to a reasonable answer to the question before setting `element_for_question = true`.
          - ALWAYS keep `next_mapping = false`.

      - Determine if the element should be mapped to the question:
        - For single input elements, map based on expected type inferred from placeholder.
        - For multiple input elements, map based on whether the text is a valid answer to the question.

      - **Handling multiple-choice or grouped elements**:
        - For questions where the answer is selected from a set of visible options (radio buttons, checkboxes, dropdown items, button groups):
          - Imagine an interviewer asked the given question and the label is your response; would the response make sense to the interviewer?
          - ALWAYS consider agreement and confirmation questions as multiple choice rather than single input.
          - Treat **every visible label or option text** as a potential valid answer, even if it seems unusual, generic, or like a fallback (e.g., "Not represented here", "Other (please specify)", "Prefer not to answer").
          - Do not interpret option text as an error, placeholder, or instruction; it should always be evaluated against the question to determine if it belongs.
          - The decision to set `element_for_question = true` depends solely on whether the option is a reasonable answer to the question. If the response is a valid response option in the context of the question, set `element_for_question = true`.
          - `next_mapping` should remain `false`.

      - **Important distinction for `next_mapping`:**
        - The decision is based on whether the question is tied to an element type that inherently allows only a **single input** versus one that implies the possibility of **multiple inputs**.
        - Input fields and text areas where the user actively types their response are **single input** by design (e.g., First Name, Email, Phone, LinkedIn URL). In these cases, once the element is matched, you can set `next_mapping = true`.
        - Buttons, checkboxes, radio options, dropdown items, and confirmation options should always be treated as **potential multiple input**. Even if the applicant is expected to *select only one option* (e.g., pronouns, gender), the question still spans multiple selectable elements. In these cases, leave `next_mapping = false`.
        - Just because the response to the question is a clear match does not mean that the element is a single input element. Only text inputs and text areas are single input elements.
        - CRITICAL: Confirmations, agreements, and yes/no responses (like "Yes", "I agree", "I confirm", etc.) are ALWAYS multiple input elements, even if only one option is visible. Always assume there could be other options (like "No", "I disagree", etc.) that may appear later in the sequence. For these, always set `next_mapping = false`.
        - When in doubt, be conservative and keep `next_mapping = false`.