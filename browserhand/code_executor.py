import logging
import asyncio
import textwrap
from typing import Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

class CodeExecutor:
    """Handles safe execution of Playwright code."""
    
    def __init__(self, page: Page):
        """
        Initialize the CodeExecutor with a page.
        
        Args:
            page: Playwright Page object to perform actions on
        """
        self.page = page
        self._action_in_progress = False
        
    async def execute_code(self, code: str) -> str:
        """
        Executes Playwright code safely.
        
        Args:
            code: Playwright code to execute
            
        Returns:
            String indicating success or error message
        """
        if self._action_in_progress:
            logger.warning("Another action is still in progress, waiting for it to complete")
            for _ in range(30):  # Wait up to 30 seconds
                if not self._action_in_progress:
                    break
                await asyncio.sleep(0.5)
                
            if self._action_in_progress:
                return "Error: Previous action is still running. Please try again later."
        
        self._action_in_progress = True
        logger.info("Executing Playwright code")
        
        try:
            result = await self.execute_safely(code)
            
            if "Error" in result:
                logger.error(f"Code execution failed: {result}")
                return result
            
            logger.info("Code executed successfully")
            return f"Code executed successfully: {code}"
        except Exception as e:
            logger.error(f"Error executing code: {str(e)} {code}")
            return f"Error executing code: {str(e)}. Please fix the code and try again."
        finally:
            self._action_in_progress = False

    async def execute_safely(self, code: str) -> str:
        try:
            async def find_element(selector: str):
                element = await self.page.query_selector(selector)
                if element:
                    return element
                for frame in self.page.frames:
                    if frame != self.page.main_frame:
                        element = await frame.query_selector(selector)
                        if element:
                            return element
                return None
            
            exec_globals = {
                "page": self.page,
                "find_element": find_element,
                "PlaywrightTimeoutError": PlaywrightTimeoutError, 
                "logger": logger,
                "asyncio": asyncio
            }
            
            self.page.set_default_timeout(30000)
            code = self._normalize_code(code)
                    
            wrapped_code = f"""
async def _execute_wrapper():
    async def _user_code():
        try:
{textwrap.indent(code, ' ' * 12)}
            return "Code executed successfully"
        except Exception as e:
            logger.error(f"Error in user code: {{e}}")
            return f"Error: {{e}}"
    return await _user_code()
"""
            compiled_code = compile(wrapped_code, "<string>", "exec")
            exec(compiled_code, exec_globals)
            execute_wrapper = exec_globals["_execute_wrapper"]
            result = await execute_wrapper()
            
            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except PlaywrightTimeoutError:
                logger.warning("Timeout waiting for networkidle; continuing")
                
            return result if "Error" in result else "Code executed successfully with proper page loading"
            
        except Exception as e:
            logger.error(f"Safe code wrapper error: {e}")
            return f"Error: {e}"
    
    def _normalize_code(self, code: str) -> str:
        code = code.strip()
        if code.startswith("```") and code.endswith("```"):
            code = code.strip("```").strip()
            if code.lower().startswith("python"):
                code = code[6:].strip()
        return code
