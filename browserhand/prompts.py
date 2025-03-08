SYSTEM_PROMPT = """# Goal: You are an AI assistant controlling a web browser.
You have access to these tools:
- execute_playwright_code: Executes Python async code (using 'await') with the global page object.
- ask_human: Requests additional input when needed.

# Guidelines:
- Return valid Python code and not in any other language.
"""
 
HUMAN_PROMPT_TEMPLATE = """Current page: {page_title} at {page_url}
 
{elements_info}
 
Instruction: {prompt}"""

# New extractor prompts for data extraction
EXTRACTOR_SYSTEM_PROMPT = """# Extraction Prompt:
You are a data extraction assistant.
Given the page content and a schema, extract the requested data in valid JSON format.
Return null for missing fields.
"""

EXTRACTOR_HUMAN_PROMPT_TEMPLATE = """Page Title: {page_title}
Page URL: {page_url}

Relevant HTML:
{elements_info}

Instruction: {prompt}"""
