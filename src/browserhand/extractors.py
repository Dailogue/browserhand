import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self, page: Page, llm: Optional[BaseChatModel] = None):
        """
        Initialize DataExtractor with a page and LangChain chat model.
        
        Args:
            page: Playwright Page object
            llm: Any LangChain chat model
        """
        self.page = page
        self.llm = llm
        if not llm:
            logger.warning("No LLM provided, will use simple extraction")

    async def extract(self, instruction: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract structured data from the page based on schema and instructions.
        
        Args:
            instruction: Natural language instructions for what data to extract
            schema: Dictionary with keys as field names and values as data types
            
        Returns:
            Dictionary of extracted data following the schema
        """
        logger.info(f"Extracting data with instruction: {instruction}")
        
        # Wait for the page to be fully loaded before extraction
        try:
            await self.page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            try:
                # Fall back to domcontentloaded if networkidle times out
                await self.page.wait_for_load_state('domcontentloaded', timeout=3000)
            except Exception:
                pass
        
        # Get page content
        page_title = await self.page.title()
        
        # If we have an LLM, use it for intelligent extraction
        if self.llm:
            # Create chat messages
            messages = [
                SystemMessage(content=f"""
                    Extract data from the webpage according to these instructions: {instruction}
                    
                    The data should match this schema:
                    {schema}
                    
                    Return valid JSON that follows the schema exactly.
                """),
                HumanMessage(content=f"""
                    Page Title: {page_title}
                    
                    Extract the requested information from this page according to the schema.
                    If a field cannot be found, set its value to null.
                    
                    For context, here is the relevant HTML:
                    ```html
                    {await self._get_relevant_html()}
                    ```
                """)
            ]
            # Get AI to extract data
            response = self.llm.invoke(messages)
            result = response.content
            
            # Parse the result as JSON
            import json
            try:
                extracted_data = json.loads(result)
                return extracted_data
            except json.JSONDecodeError:
                # Fallback to simple extraction if JSON parsing fails
                return await self._simple_extract(schema)
        else:
            # Fallback to simple extraction if no LLM is available
            return await self._simple_extract(schema)
    
    async def _simple_extract(self, schema: Dict[str, str]) -> Dict[str, Any]:
        """Simple extraction based on common selectors and schema keys."""
        extracted_data = {}
        
        for key, data_type in schema.items():
            # Generate likely selectors based on key name
            selectors = [
                f"#{key}", f".{key}", f"[name='{key}']",
                f"[data-field='{key}']", f"[aria-label='{key}']",
                f"h1:contains('{key}')", f"p:contains('{key}')"
            ]
            
            # Try each selector
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        text = text.strip()
                        
                        # Convert to appropriate type
                        if data_type == "int":
                            import re
                            numbers = re.findall(r'\d+', text)
                            if numbers:
                                extracted_data[key] = int(numbers[0])
                        elif data_type == "float":
                            import re
                            numbers = re.findall(r'\d+\.\d+|\d+', text)
                            if numbers:
                                extracted_data[key] = float(numbers[0])
                        else:
                            # Default to string
                            extracted_data[key] = text
                        
                        # Successfully found and extracted, move to next key
                        break
                except Exception:
                    continue
            
            # If we didn't find the key, set it to None
            if key not in extracted_data:
                extracted_data[key] = None
     
        return extracted_data
    
    async def _get_relevant_html(self) -> str:
        """Get only the most relevant parts of the HTML for extraction."""
        try:
            main_content = await self.page.query_selector("main, #main, .main, article, .content")
            if (main_content):
                html = await main_content.inner_html()
                return html
                
            # Fallback to body with limited size
            body = await self.page.query_selector("body")
            if body:
                html = await body.inner_html()
                # Limit size to avoid token limits
                result = html[:10000] if len(html) > 10000 else html
                return result
            
            return "<html>Failed to extract relevant HTML</html>"
        except Exception:
            return "<html>Error extracting HTML</html>"
