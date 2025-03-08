import logging
from typing import Dict, List, Any, Optional, Awaitable
import subprocess, socket, time, os, asyncio, signal
from playwright.async_api import async_playwright, Page, Browser
from langchain_core.language_models.chat_models import BaseChatModel

from .actions import BrowserActions
from .page_observer import PageObserver
from .extractors import DataExtractor

logger = logging.getLogger(__name__)

class BrowserHand:
    def __init__(self, page: Page = None, browser: Browser = None, playwright=None, llm: Optional[BaseChatModel] = None):
        self.page = page
        self.browser = browser
        self.playwright = playwright
        self.llm = llm
        if page and llm:
            self.actions = BrowserActions(page, llm)
            self.extractor = DataExtractor(page, llm)
        else:
            logger.warning("Missing page or LLM; actions and extractor not initialized")

    async def with_fallback(self, operation: Awaitable, fallback_instruction: str) -> Any:
        try:
            return await operation
        except Exception as e:
            logger.warning(f"Primary operation failed: {e}. Fallback: {fallback_instruction}")
            result = await self.Act(fallback_instruction)
            return result.get("success", False)

    @staticmethod
    def _find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]

    @classmethod
    async def create(cls, llm: BaseChatModel, headless: bool = False, browser_path: Optional[str] = None,
                     browser_type: str = "chromium", slowmo: int = 0, user_data_dir: Optional[str] = None,
                     use_existing_page: bool = True):
        if llm is None:
            raise ValueError("No LLM provided")
        playwright = await async_playwright().start()
        browser_engine = (playwright.firefox if browser_type.lower()=="firefox" 
                          else playwright.webkit if browser_type.lower()=="webkit" 
                          else playwright.chromium)
        browser_process = None
        if browser_path:
            if not os.path.isfile(browser_path):
                raise FileNotFoundError(f"Browser executable not found: {browser_path}")
            debug_port = cls._find_free_port()
            browser_url = f"http://localhost:{debug_port}"
            if "firefox" in browser_path.lower() or browser_type.lower() == "firefox":
                cmd = [browser_path, f"--remote-debugging-port={debug_port}", "--no-remote", "--new-instance"]
            else:
                user_data_dir = user_data_dir or os.path.join(os.path.expanduser("~"), ".browserhand", "user_data")
                os.makedirs(user_data_dir, exist_ok=True)
                cmd = [browser_path, f"--remote-debugging-port={debug_port}", "--no-first-run", f"--user-data-dir={user_data_dir}", "--no-default-browser-check"]
                if headless:
                    cmd.append("--headless=new")
            try:
                browser_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                max_retries = 10
                for i in range(max_retries):
                    try:
                        with socket.create_connection(("localhost", debug_port), timeout=1):
                            time.sleep(1)
                            break
                    except (socket.timeout, ConnectionRefusedError):
                        if i == max_retries - 1:
                            browser_process.terminate()
                            raise TimeoutError("Timed out waiting for browser to start")
                        time.sleep(1)
                browser = await browser_engine.connect_over_cdp(endpoint_url=browser_url, timeout=30000, slow_mo=slowmo)
                if use_existing_page:
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                    page = context.pages[0] if context.pages else await context.new_page()
                else:
                    context = await browser.new_context()
                    page = await context.new_page()
            except Exception as e:
                if browser_process:
                    browser_process.terminate()
                raise e
        else:
            browser = await browser_engine.launch(headless=headless, slow_mo=slowmo)
            page = await browser.new_page()
        instance = cls(page=page, browser=browser, playwright=playwright, llm=llm)
        instance._browser_process = browser_process
        return instance

    async def Act(self, prompt: str) -> Dict[str, Any]:
        result = await self.actions.act(prompt)
        return result

    async def Extract(self, instruction: str, schema: Dict[str, str]) -> Dict[str, Any]:
        result = await self.extractor.extract(instruction, schema)
        return result

    async def Observe(self) -> List[Dict[str, Any]]:
        return await PageObserver.observe_page(self.page)

    async def close(self) -> None:
        try:
            if self.page:
                try:
                    await self.page.close(timeout=10000)
                except Exception:
                    pass
            if self.browser:
                try:
                    await self.browser.close()
                    await asyncio.sleep(1)
                except Exception:
                    pass
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception:
                    pass
            if hasattr(self, '_browser_process') and self._browser_process:
                if self._browser_process.poll() is None:
                    self._browser_process.terminate()
                    try:
                        self._browser_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.kill(self._browser_process.pid, signal.SIGTERM)
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def goto(self, url: str) -> None:
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=60000)
        except Exception as e:
            logger.warning(f"Navigation warning: {e}")
            try:
                await self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            except Exception:
                pass

    async def scroll_to_element(self, selector: str) -> bool:
        try:
            element = await self.page.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
                return True
            return False
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return False

    async def scroll_by(self, dx: int = 0, dy: int = 400) -> bool:
        try:
            await self.page.evaluate(f"window.scrollBy({{left: {dx}, top: {dy}}});")
            return True
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return False
