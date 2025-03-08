import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from .prompts import EXTRACTOR_SYSTEM_PROMPT, EXTRACTOR_HUMAN_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class DataExtractor:
    def __init__(self, page: Page, llm: Optional[BaseChatModel] = None):
        self.page = page
        self.llm = llm
        if not llm:
            logger.warning("No LLM provided; using simple extraction")

    async def extract(self, instruction: str, schema: Dict[str, str]) -> Dict[str, Any]:
        logger.info(f"Extracting data: {instruction}")
        try:
            await self.page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            try:
                await self.page.wait_for_load_state('domcontentloaded', timeout=3000)
            except Exception:
                pass
        page_title = await self.page.title()
        if self.llm:
            human_prompt = EXTRACTOR_HUMAN_PROMPT_TEMPLATE.format(
                page_title=page_title,
                page_url=self.page.url,
                elements_info=await self._get_relevant_html(),
                prompt=instruction
            )
            messages = [
                SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT + f"\nSchema: {schema}"),
                HumanMessage(content=human_prompt)
            ]
            response = self.llm.invoke(messages)
            result = response.content
            import json
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return await self._simple_extract(schema)
        else:
            return await self._simple_extract(schema)
    
    async def _simple_extract(self, schema: Dict[str, str]) -> Dict[str, Any]:
        extracted_data = {}
        for key, data_type in schema.items():
            selectors = [f"#{key}", f".{key}", f"[name='{key}']", f"[data-field='{key}']", f"[aria-label='{key}']", f"h1:contains('{key}')", f"p:contains('{key}')"]
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = (await element.inner_text()).strip()
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
                            extracted_data[key] = text
                        break
                except Exception:
                    continue
            if key not in extracted_data:
                extracted_data[key] = None
        return extracted_data
    
    async def _get_relevant_html(self) -> str:
        main_content = await self.page.query_selector("main, #main, .main, article, .content")
        if main_content:
            return await main_content.inner_html()
        body = await self.page.query_selector("body")
        html = await body.inner_html() if body else ""
        return html[:10000] if len(html) > 10000 else html
