# Prototype 0 - Kyro

An intelligent, autonomous job application agent capable of navigating, understanding, and filling out complex job application forms across various platforms (Greenhouse, Lever, Ashby, Workday). This codebase is a small subset of my production code for my upcoming AI product, Tempra that is working to automatically apply to any tech job on the internet. Tempra is already cheaper than 99% of competitors out in the market and that is the result from months of testing and figuring out accurate, reliable, consistent, and fast ways to interact with job applications. I started this project back in August, barely understanding LLMs. Now, I believe I have caught up with the modern ways of browser use.

## Demo

https://github.com/user-attachments/assets/6b831670-2da6-4044-aa04-998dd95002b5

https://github.com/user-attachments/assets/26937d97-8060-4ff4-b51d-a9efb556b5f2

## Project Summary

This project represents a cutting-edge exploration into **autonomous browser agents**. Unlike traditional scrapers that rely on brittle CSS selectors or hardcoded XPaths, Kyro uses a cognitive approach to understand web pages like a human does.

The system:
1.  **Sees** the page using computer vision and accessibility tree analysis.
2.  **Reads** the questions and context using LLMs.
3.  **Maps** semantic intent to interactive DOM elements.
4.  **Acts** on the page to fill out forms with personalized user data.

## Deep Dive: How `src/one_pager.py` was Built

The core logic for single-page applications (like Greenhouse or Lever) resides in `src/one_pager.py`. Here is the architectural breakdown of how it was engineered:

### 1. The "Vision" Layer (AgentQL & Playwright)
Instead of relying solely on standard Playwright locators, we integrated **AgentQL**. This allows us to query the DOM using semantic descriptions (e.g., `{ application_form_input_text_tags [] }`) rather than rigid code. This makes the agent resilient to layout changes and class name obfuscation.

### 2. Dual-Stream Extraction
The agent performs two distinct extraction passes:
*   **Element Extraction:** Identifies every interactive component on the page (inputs, dropdowns, radio buttons).
*   **Question Extraction:** Identifies the actual text questions being asked.

### 3. The "Noise Filter" (Accessibility Tree Analysis)
A major challenge in browser automation is "ghost elements"—DOM nodes that exist but aren't visible or interactive. To solve this, `one_pager.py` implements a **Post-Extraction Filter** (`src/post_extraction_filter.py`). It cross-references the AgentQL results with the browser's **Accessibility Tree**. If an element isn't in the accessibility tree, it's likely not relevant to the user, so we discard it. This significantly reduces hallucinations.

### 4. The "Brain" (Question-to-Element Mapper)
This is the most critical component. We have a list of questions (text) and a list of elements (locators), but we don't know which belongs to which.
*   **Slow Mode:** Uses a `GeminiQuestionMapperAgent` to iteratively reason about each question-element pair.
*   **Fast Mode:** Uses a `OnePromptQuestionMapperAgent` that sends the entire context to the LLM in a single prompt, asking it to return a JSON mapping of `Question ID -> Element ID`.

### 5. Execution
Once the mapping is established, the `ApplicationActionAgent` takes over. It uses the user's profile (resume, bio, preferences) to generate answers for each question and executes the fill actions (typing, clicking, selecting options) on the mapped elements.

## Frameworks & Technologies Tested or Used in Tempra

This project was the result of extensive R&D. We evaluated nearly every major tool in the AI and Browser Automation space to find the optimal stack.

**Browser Automation & Agents:**
*   **BrowserUse:** Used as part of our self-healing system to correct any mistakes our automation pipeline makes.
*   **AgentQL:** Selected for its reliable semantic query capabilities to fetch web elements with speed.
*   **Firecrawl:** Tested for turning websites into LLM-ready markdown, considering future use to create a custom web element locator for even more reduced cost.
*   **Browserbase:** Used for scalable, cloud-based headless browser infrastructure and are considering switching to other infrastructures like Hyperbrowser, Steel, Anchor, Brightdata, and BrowserAI.
*   **Crawl4AI:** Tested at beginning of project for decent html-to-markdown extraction.
*   **Yutori:** Experimented with n1 pixel-to-action model, planning future use to create a fully agentic loop.
*   **Mino:** Product built by the creators of AgentQL, evaluated its cost efficiency and latency on simple one pagers.

**LLMs & Inference:**
*   **OpenAI (GPT-4o):** Used for complex reasoning and reasoning-heavy mappings.
*   **Gemini (Pro/Flash):** Utilized for its massive context window and multimodal capabilities.
*   **Claude (Sonnet 4.6 Opus):** Excellent for code generation and complex instruction following.
*   **Deepseek:** Tested as a cost-effective high-performance alternative.
*   **Groq:** Tested for ultra-low latency inference.

**Computer Vision & OCR:**
*   **OCR (Tesseract/EasyOCR):** Used for extracting text from non-selectable elements.
*   **OpenCV:** Used for low-level image processing and element detection.

This comprehensive testing process ensures that Kyro is built on the most robust and capable technologies available today.
