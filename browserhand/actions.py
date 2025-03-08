import logging
from typing import Dict, Any
from playwright.async_api import Page
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool

from .code_executor import CodeExecutor
from .page_observer import PageObserver
from .prompts import SYSTEM_PROMPT, HUMAN_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class BrowserActions:
    def __init__(self, page: Page, llm: BaseChatModel):
        self.page = page
        self.llm = llm
        self.code_executor = CodeExecutor(page)
        self.tools = [
            StructuredTool.from_function(
                func=self._execute_code_tool,
                name="execute_playwright_code",
                description="Execute async Playwright code using the global page object."
            ),
            StructuredTool.from_function(
                func=self._ask_human_tool,
                name="ask_human",
                description="Request additional human input."
            )
        ]
        self.llm_with_tools = llm.bind_tools(self.tools)

    async def _execute_code_tool(self, code: str) -> str:
        return await self.code_executor.execute_code(code)

    async def _ask_human_tool(self, prompt: str) -> str:
        print(f"\n{'-'*50}\nAI needs your input: {prompt}\n{'-'*50}\n")
        user_input = input("Your response: ")
        return f"Human responded: {user_input}"

    async def act(self, prompt: str) -> Dict[str, Any]:
        try:
            page_title = await self.page.title()
        except Exception:
            page_title = "Unknown"
        page_url = self.page.url
        try:
            active_elements = await PageObserver.observe_page(self.page)
        except Exception as e:
            logger.error(f"Observation error: {e}")
            active_elements = []
        elements_info = "Active page elements:\n"
        for i, elem in enumerate(active_elements):
            if not elem['is_visible'] or not elem['in_viewport']:
                continue
            desc = f"{i+1}. "
            if elem['text']:
                desc += f"'{elem['text']}' "
            desc += f"({elem['tag']}"
            if elem['tag'] == 'a':
                if elem['id']:
                    desc += f", id='{elem['id']}'"
                if 'href' in elem:
                    desc += f", href='{elem['href']}'"
            else:
                if elem['id']:
                    desc += f", id='{elem['id']}'"
                elif elem['class']:
                    desc += f", class='{elem['class'][:25]}'"
                if elem['tag'] == 'input' and 'type' in elem:
                    desc += f", type='{elem['type']}'"
                if elem['tag'] in ['input', 'textarea'] and 'placeholder' in elem:
                    desc += f", placeholder='{elem['placeholder']}'"
                if elem.get("frame") and elem["frame"] != self.page.main_frame:
                    desc += f", frame='{elem['frame']}'"
            desc += ")"
            elements_info += desc + "\n"
        system_message = SystemMessage(content=SYSTEM_PROMPT)
        human_message_content = HUMAN_PROMPT_TEMPLATE.format(
            page_title=page_title,
            page_url=page_url,
            elements_info=elements_info,
            prompt=prompt
        )
        human_message = HumanMessage(content=human_message_content)
        messages = [system_message, human_message]
        action_executed = False
        final_code = ""
        max_iterations = 5
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            try:
                response = await self.llm_with_tools.ainvoke(messages)
                messages.append(response)
            except Exception as e:
                return {
                    "success": False,
                    "action": final_code,
                    "message": f"LLM error: {e}",
                    "conversation": [{"role": msg.type, "content": msg.content} for msg in messages]
                }
            tool_executed = False
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    if tool_name == "execute_playwright_code":
                        code = tool_call["args"].get("code", "")
                        final_code = code
                        tool_result = await self._execute_code_tool(code)
                        if "Error" not in tool_result:
                            action_executed = True
                    elif tool_name == "ask_human":
                        prompt_text = tool_call["args"].get("prompt", "")
                        tool_result = await self._ask_human_tool(prompt_text)
                    else:
                        tool_result = f"Unknown tool: {tool_name}"
                    messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call["id"]))
            else:
                break
        return {
            "success": action_executed,
            "action": final_code,
            "message": "Actions executed" if action_executed else "No actions executed",
            "conversation": [{"role": msg.type, "content": msg.content} for msg in messages]
        }
