import logging
from typing import Dict, List, Any, Optional, Union
import subprocess
import socket
import time
import os
import asyncio
from playwright.async_api import async_playwright, Page, Browser
from langchain_core.language_models.chat_models import BaseChatModel
import signal

from .actions import BrowserActions
from .extractors import DataExtractor

logger = logging.getLogger(__name__)

class BrowserHand:
	"""
	A high-level wrapper over Playwright that uses AI to control the browser using natural language.
	"""
	
	def __init__(self, 
				 page: Page = None,
				 browser: Browser = None,
				 playwright = None,
				 llm: Optional[BaseChatModel] = None):
		"""
		Initialize BrowserHand with necessary components.
		
		Note: This constructor should not be called directly. Use the create() classmethod instead.
		"""
		logger.info("Initializing BrowserHand")
		self.page = page
		self.browser = browser
		self.playwright = playwright
		self.llm = llm
		
		if page is not None and llm is not None:
			logger.info("Creating BrowserActions and DataExtractor")
			self.actions = BrowserActions(page, llm)
			self.extractor = DataExtractor(page, llm)
		else:
			logger.warning("Missing page or LLM - BrowserActions and DataExtractor not initialized")

	@staticmethod
	def _find_free_port():
		"""Find a free port to use for browser debugging."""
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.bind(('localhost', 0))
			return s.getsockname()[1]

	@classmethod
	async def create(cls, 
				 llm: BaseChatModel,
				 headless: bool = False,
				 browser_path: Optional[str] = None,
				 browser_type: str = "chromium",
				 slowmo: int = 0,
				 user_data_dir: Optional[str] = None,
				 use_existing_page: bool = True):
		"""
		Create and initialize a BrowserHand instance asynchronously.
		
		Args:
			llm: Any LangChain chat model
			headless: Whether to run browser in headless mode
			browser_path: Path to browser executable. If provided, launches the browser with remote debugging.
			browser_type: Type of browser to use ("chromium", "firefox", or "webkit")
			slowmo: Slow down operations by the specified amount of milliseconds (useful for debugging)
			user_data_dir: Path to Chrome user data directory containing profiles (to use existing profiles)
			use_existing_page: If True, will try to use an existing page rather than creating a new one
			
		Returns:
			Initialized BrowserHand instance
		"""
		logger.info(f"Creating BrowserHand instance (headless: {headless}, browser_type: {browser_type})")
		
		if llm is None:
			logger.error("No LLM provided. Please provide a LangChain chat model.")
			raise ValueError("No LLM provided. Please provide a LangChain chat model.")
		
		# Initialize playwright
		playwright = await async_playwright().start()
		
		# Determine which browser engine to use
		if browser_type.lower() == "firefox":
			browser_engine = playwright.firefox
		elif browser_type.lower() == "webkit":
			browser_engine = playwright.webkit
		else:
			browser_engine = playwright.chromium
		
		# If browser_path is provided, launch the browser with remote debugging
		browser_process = None
		if browser_path:
			logger.info(f"Launching browser from path: {browser_path}")
			if not os.path.isfile(browser_path):
				logger.error(f"Browser executable not found: {browser_path}")
				raise FileNotFoundError(f"Browser executable not found: {browser_path}")
				
			# Find a free port for debugging
			debug_port = cls._find_free_port()
			browser_url = f"http://localhost:{debug_port}"
			
			# Prepare browser launch command with debugging flags
			if "firefox" in browser_path.lower() or browser_type.lower() == "firefox":
				cmd = [
					browser_path, 
					f"--remote-debugging-port={debug_port}",
					"--no-remote",
					"--new-instance"
				]
			else:  # Chrome/Chromium/Edge
				# Use provided user_data_dir if specified, otherwise create a default one
				if not user_data_dir:
					user_data_dir = os.path.join(os.path.expanduser("~"), ".browserhand", "user_data")
					os.makedirs(user_data_dir, exist_ok=True)
					
				cmd = [
					browser_path,
					f"--remote-debugging-port={debug_port}",
					"--no-first-run",
					f"--user-data-dir={user_data_dir}",
					"--no-default-browser-check"
				]
				if headless:
					cmd.append("--headless=new")
			
			# Launch the browser
			try:
				browser_process = subprocess.Popen(
					cmd, 
					stdout=subprocess.PIPE, 
					stderr=subprocess.PIPE
				)
				
				# Wait for the browser to start and be ready
				max_retries = 10
				for i in range(max_retries):
					try:
						with socket.create_connection(("localhost", debug_port), timeout=1):
							time.sleep(1)  # Give browser a bit more time to fully initialize
							break
					except (socket.timeout, ConnectionRefusedError):
						if i == max_retries - 1:
							if browser_process:
								browser_process.terminate()
							raise TimeoutError("Timed out waiting for browser to start")
						time.sleep(1)
				
				# Connect to the launched browser
				try:
					browser = await browser_engine.connect_over_cdp(
						endpoint_url=browser_url,
						timeout=30000,
						slow_mo=slowmo
					)
					
					if use_existing_page:
						contexts = browser.contexts
						if contexts:
							context = contexts[0]
							pages = context.pages
							if pages:
								page = pages[0]
							else:
								page = await context.new_page()
						else:
							context = await browser.new_context()
							page = await context.new_page()
					else:
						context = await browser.new_context()
						page = await context.new_page()
						
				except Exception as e:
					if browser_process:
						browser_process.terminate()
					raise e
			except Exception as e:
				if browser_process:
					browser_process.terminate()
				raise e
		else:
			# Launch new browser instance
			browser = await browser_engine.launch(
				headless=headless, 
				slow_mo=slowmo
			)
			page = await browser.new_page()
		
		# Create instance
		instance = cls(page=page, browser=browser, playwright=playwright, llm=llm)
		
		# Store the browser process if we launched it
		if browser_process:
			instance._browser_process = browser_process
		else:
			instance._browser_process = None
			
		return instance
	
	async def goto(self, url: str) -> None:
		"""Navigate to a URL and wait for the page to fully load."""
		logger.info(f"Navigating to URL: {url}")
		
		try:
			# Wait for both navigation and network idle
			await self.page.goto(url, wait_until='networkidle', timeout=60000)
		except Exception as e:
			logger.warning(f"Navigation may not be fully complete: {str(e)}")
			# If networkidle times out, at least wait for domcontentloaded
			try:
				await self.page.wait_for_load_state('domcontentloaded', timeout=10000)
			except Exception:
				pass
	
	async def Act(self, prompt: str) -> Dict[str, Any]:
		"""
		Perform actions on the current page based on a natural language prompt.
		
		Args:
			prompt: Natural language instruction for what to do on the page
			
		Returns:
			Dictionary containing action results
		"""
		logger.info(f"Performing action: {prompt}")
		result = await self.actions.act(prompt)
		return result
	
	async def Extract(self, instruction: str, schema: Dict[str, str]) -> Dict[str, Any]:
		"""
		Extract structured data from the current page based on instructions.
		
		Args:
			instruction: Natural language description of what to extract
			schema: Dictionary defining the structure of data to extract
			
		Returns:
			Dictionary containing extracted data according to schema
		"""
		logger.info(f"Extracting data: {instruction}")
		result = await self.extractor.extract(instruction, schema)
		return result
	
	async def Observe(self) -> List[Dict[str, Any]]:
		"""
		Get candidate DOM elements for actions.
		
		Returns:
			List of dictionaries representing important DOM elements
		"""
		logger.info("Observing DOM elements")
		elements = await self.actions.observe()
		return elements
	
	async def close(self) -> None:
		"""Close the browser and clean up resources."""
		logger.info("Closing BrowserHand and releasing resources")
		
		try:
			# Close page and browser gracefully with timeouts
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
			
			# Terminate browser process if we launched it
			if hasattr(self, '_browser_process') and self._browser_process:
				if self._browser_process.poll() is None:  # Check if process is still running
					self._browser_process.terminate()
					try:
						self._browser_process.wait(timeout=10)
					except subprocess.TimeoutExpired:
						if os.name == 'nt':
							self._browser_process.kill()
						else:
							os.kill(self._browser_process.pid, signal.SIGTERM)
		except Exception as e:
			logger.error(f"Error during BrowserHand shutdown: {e}")
		finally:
			logger.info("BrowserHand closed successfully")
