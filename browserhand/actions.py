import logging
from typing import Dict, List, Any, Optional, Callable
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
import json
import asyncio
import textwrap

logger = logging.getLogger(__name__)

class BrowserActions:
	"""
	Handles AI-driven browser automation using Playwright and LangChain.
	
	This class enables natural language control of a browser by translating
	instructions into Playwright actions through an LLM.
	"""
	
	def __init__(self, page: Page, llm: BaseChatModel):
		"""
		Initialize BrowserActions with a page and LangChain chat model.
		
		Args:
			page: Playwright Page object to perform actions on
			llm: LangChain chat model for interpreting instructions
		"""
		logger.info("Initializing BrowserActions")
		self.page = page
		self.llm = llm
		
		self._action_in_progress = False  # Track the currently running action to prevent overlapping actions
		
		# Define tools for LLM to interact with the browser
		self.tools = [
			StructuredTool.from_function(
				func=self._execute_code_tool,
				name="execute_playwright_code",
				description="Executes Playwright code to automate browser actions. Provide valid Python async code using the 'page' object.",
			),
			StructuredTool.from_function(
				func=self._ask_human_tool,
				name="ask_human",
				description="Ask the human for input when you need additional information or clarification.",
			)
		]
		
		self.llm_with_tools = llm.bind_tools(self.tools)
		logger.info("BrowserActions initialized successfully")

	async def _execute_code_tool(self, code: str) -> str:
		"""
		Tool for executing Playwright code safely.
		
		Args:
			code: Playwright code to execute
			
		Returns:
			String indicating success or error message
		"""
		# Prevent overlapping actions
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
			# Clean up code
			code = code.strip()
			if code.startswith("```python"):
				code = code.replace("```python", "", 1)
			if code.endswith("```"):
				code = code[:-3]
			if code.startswith("```"):
				code = code.replace("```", "", 1)
			code = code.strip()
			
			# Wrap code with page loading safety checks
			exec_function = f"""async def _exec_function(page):
	# Enable automatic waiting for all actions
	page.set_default_timeout(30000)  # 30 seconds timeout
	
	# Helper functions for scrolling
	async def scroll_to_element(selector):
		try:
			element = await page.query_selector(selector)
			if element:
				await element.scroll_into_view_if_needed()
				return True
			return False
		except Exception as e:
			logger.error(f"Error scrolling to element: {{str(e)}}")
			return False
			
	async def scroll_by(dx=0, dy=400):
		try:
			await page.evaluate("window.scrollBy({{left:" + str(dx) + ", top: " + str(dy) + "}});")
			return True
		except Exception as e:
			logger.error(f"Error scrolling: {{str(e)}}")
			return False
	
	try:
		# Execute the actual code
{textwrap.indent(code, '        ')}
		
		# Ensure page is fully loaded after all actions
		try:
			await page.wait_for_load_state('networkidle', timeout=10000)
			logger.info("Page reached network idle state")
		except PlaywrightTimeoutError:
			logger.warning("Timeout waiting for networkidle, continuing anyway")
			
		return "Code executed successfully with proper page loading"
	except Exception as e:
		logger.error(f"Error during code execution: {{str(e)}}")
		return f"Error: {{str(e)}}"
"""
			
			# Execute the created function
			exec_globals = {"PlaywrightTimeoutError": PlaywrightTimeoutError, "logger": logger}
			exec(exec_function, exec_globals)
			
			# Run the async function
			result = await exec_globals["_exec_function"](self.page)
			
			if "Error" in result:
				logger.error(f"Code execution failed: {result}")
				return result
			
			logger.info("Code executed successfully")
			return f"Code executed successfully: {code}"
		except Exception as e:
			logger.error(f"Error executing code: {str(e)} {code}")
			return f"Error executing code: {str(e)}. Please fix the code and try again."
		finally:
			# Always release the action lock when done
			self._action_in_progress = False

	async def _ask_human_tool(self, prompt: str) -> str:
		"""
		Tool for requesting input from the human user.
		
		Args:
			prompt: Question or prompt to show to the user
			
		Returns:
			String containing the user's response
		"""
		logger.info(f"Asking human for input: {prompt}")
		print("\n" + "-"*50)
		print(f"AI needs your input: {prompt}")
		user_input = input("Your response: ")
		print("-"*50 + "\n")
		logger.info(f"Human responded to prompt")
		return f"Human responded: {user_input}"

	async def act(self, prompt: str) -> Dict[str, Any]:
		"""
		Execute actions on the page based on natural language instructions.
		
		This method translates natural language instructions into browser actions
		using the LLM and Playwright. It allows for multi-turn interactions to
		resolve complex tasks.
		
		Args:
			prompt: Natural language instruction for what to do on the page
			
		Returns:
			Dictionary containing:
				- success: Boolean indicating if the action was successful
				- action: The code that was executed
				- message: Status message
				- conversation: The full conversation history with the LLM
		"""
		logger.info(f"Acting on instruction: {prompt}")
		
		# Get current page state
		try:
			page_title = await self.page.title()
		except Exception:
			page_title = "Unknown"
			
		page_url = self.page.url
		
		# Get active elements on the page
		try:
			active_elements = await self.observe()
		except Exception as e:
			logger.error(f"Error observing page elements: {str(e)}")
			active_elements = []
		
		# Format active elements for inclusion in the prompt
		elements_info = "Active page elements:\n"
		for i, elem in enumerate(active_elements[:10]):  # Limit to first 10 elements to avoid token overflow
			elem_desc = f"{i+1}. "
			if elem['text']:
				elem_desc += f"'{elem['text']}' "
			elem_desc += f"({elem['tag']}"
			if elem['id']:
				elem_desc += f", id='{elem['id']}'"
			elif elem['class']:  # Only add class if id is not present
				elem_desc += f", class='{elem['class'][:25]}'" # Limit class length
			if elem['tag'] == 'input' and 'type' in elem:
				elem_desc += f", type='{elem['type']}'"
			elem_desc += f", visible={elem['is_visible']}"
			elem_desc += ")"
			elements_info += elem_desc + "\n"
		
		# Create initial system message
		system_message = SystemMessage(content=f"""
			You are an AI assistant that controls a web browser. 
			Analyze the instruction and use the provided tools to complete the task.
			
			You have access to these tools:
			- execute_playwright_code: Executes Python code using Playwright to control the browser
			- ask_human: Ask the human for input when you need clarification
			
			When using execute_playwright_code, return valid Python async code that can be executed.
			All Playwright commands must use 'await'. For example: 'await page.click()'
			
			IMPORTANT: The observed elements only include those currently visible in the viewport.
			If you need to interact with elements not currently visible:
			1. Use scrolling to bring them into view: 'await scroll_by(dx=0, dy=400)' scrolls down 400 pixels
			2. Or scroll directly to an element: 'await scroll_to_element("selector")'
			3. After scrolling, call 'await page.wait_for_timeout(500)' to let the page settle
		""")
		
		# Initial human message
		human_message = HumanMessage(content=f"""Current page: {page_title} at {page_url}

{elements_info}

Instruction: {prompt}""")
		
		# Set up conversation with the model
		messages = [system_message, human_message]
		
		# Track if we've executed any actions successfully
		action_executed = False
		final_code = ""
		max_iterations = 5  # Prevent infinite loops
		iteration = 0
		
		logger.info(f"Starting conversation loop (max {max_iterations} iterations)")
		while iteration < max_iterations:
			iteration += 1
			
			try:
				# Get AI response
				response = await self.llm_with_tools.ainvoke(messages)
				messages.append(response)
			except Exception as e:
				logger.error(f"Error getting LLM response: {str(e)}")
				return {
					"success": False,
					"action": final_code,
					"message": f"Failed to get AI response: {str(e)}",
					"conversation": [{"role": msg.type, "content": msg.content} for msg in messages]
				}

			# Check if the response contains tool calls
			if hasattr(response, "tool_calls") and response.tool_calls:
				for tool_call in response.tool_calls:
					tool_name = tool_call["name"]
					
					# Handle each tool call properly
					if tool_name == "execute_playwright_code":
						code = tool_call["args"].get("code", "")
						final_code = code
						tool_result = await self._execute_code_tool(code)
						if "Error" not in tool_result:
							logger.info("Code executed successfully")
							action_executed = True
						else:
							logger.warning(f"Code execution error: {tool_result}")
					elif tool_name == "ask_human":
						prompt_text = tool_call["args"].get("prompt", "")
						tool_result = await self._ask_human_tool(prompt_text)
					else:
						logger.warning(f"Unknown tool: {tool_name}")
						tool_result = f"Unknown tool: {tool_name}"
						
					# Add tool message to conversation
					messages.append(ToolMessage(content=tool_result, tool_call_id=tool_call["id"]))
			else:
				# If no tool calls and we've already done at least one iteration,
				# assume we're done or the model is confused
				if iteration > 1:
					logger.info("No tool calls after initial iteration, ending loop")
					break
				
				# If the model returned code directly (for backward compatibility)
				content = response.content
				if "```python" in content or "await page." in content:
					# Extract code and execute it
					code_lines = []
					in_code_block = False
					
					for line in content.split("\n"):
						if line.strip() == "```python":
							in_code_block = True
						elif line.strip() == "```" and in_code_block:
							in_code_block = False
						elif in_code_block:
							code_lines.append(line)
						elif "await page." in line:  # Catch standalone lines with page commands
							code_lines.append(line)
					
					if code_lines:
						final_code = "\n".join(code_lines)
						tool_result = await self._execute_code_tool(final_code)
						messages.append(ToolMessage(content=tool_result, tool_call_id="manual_extraction"))
						if "Error" not in tool_result:
							logger.info("Extracted code executed successfully")
							action_executed = True
						else:
							logger.warning(f"Error executing extracted code: {tool_result}")
					else:
						# No code found, break the loop
						break
				else:
					# No tools or code, break the loop
					break
			
			# If we've successfully executed an action and no errors were reported,
			# we can consider the task complete
			if action_executed and "Error" not in messages[-1].content:
				logger.info("Action executed successfully, ending loop")
				break
		
		logger.info(f"Action completed: {action_executed}")
		return {
			"success": action_executed,
			"action": final_code,
			"message": "Action completed successfully" if action_executed else "Failed to execute action",
			"conversation": [{"role": msg.type, "content": msg.content} for msg in messages]
		}

	async def _is_element_in_viewport(self, element) -> bool:
		"""
		Check if an element is in the viewport (visible on screen).
		
		Args:
			element: Playwright element to check
			
		Returns:
			Boolean indicating if the element is in the viewport
		"""
		try:
			is_visible = await element.is_visible()
			if not is_visible:
				return False
				
			# Check if the element is in the viewport
			is_in_viewport = await element.evaluate("""element => {
				const rect = element.getBoundingClientRect();
				return (
					rect.top >= 0 &&
					rect.left >= 0 &&
					rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
					rect.right <= (window.innerWidth || document.documentElement.clientWidth)
				);
			}""")
			
			return is_in_viewport
		except Exception as e:
			logger.error(f"Error checking if element is in viewport: {str(e)}")
			return False

	async def observe(self) -> List[Dict[str, Any]]:
		"""
		Identify and return important interactive elements on the page that are in the viewport.
		
		Locates elements like buttons, links, and form fields that are likely
		to be relevant for interaction and visible on screen.
		
		Returns:
			List of dictionaries containing element information including:
			- tag: HTML tag name
			- text: Text content of the element
			- id: Element ID attribute
			- class: Element class attribute
			- is_visible: Whether the element is visible
				- in_viewport: Whether the element is in the viewport
			- is_enabled: Whether the element is enabled (for inputs)
			- type: Input type (for input elements)
			- placeholder: Placeholder text (for input and textarea elements)
		"""
		logger.info("Observing page elements")
		# Extract important elements like buttons, links, form fields
		selectors = [
			"button", "a", "input", "select", "textarea", 
			"[role='button']", "[role='link']", "[role='checkbox']"
		]
		
		results = []
		for selector in selectors:
			logger.info(f"Querying elements with selector: {selector}")
			try:
				elements = await self.page.query_selector_all(selector)
				logger.info(f"Found {len(elements)} elements with selector: {selector}")
				
				for element in elements:
					try:
						# Check if element is visible first (basic check)
						is_visible = await element.is_visible()
						if not is_visible:
							continue
							
						# Check if element is in viewport
						in_viewport = await self._is_element_in_viewport(element)
						
						# Get useful properties of the element
						element_info = {
							"tag": await element.evaluate("el => el.tagName.toLowerCase()"),
							"text": await element.inner_text() if await element.inner_text() else "",
							"id": await element.get_attribute("id") if await element.get_attribute("id") else "",
							"class": await element.get_attribute("class") if await element.get_attribute("class") else "",
							"is_visible": is_visible,
							"in_viewport": in_viewport,
							"is_enabled": await element.is_enabled() if hasattr(element, "is_enabled") else True,
						}
						
						# Add type for input elements
						if element_info["tag"] == "input":
							element_info["type"] = await element.get_attribute("type") or "text"
						
						# Add placeholder for input and textarea elements
						if element_info["tag"] in ["input", "textarea"]:
							placeholder = await element.get_attribute("placeholder")
							if placeholder:
								element_info["placeholder"] = placeholder
						
						# Only include elements that are in the viewport
						if in_viewport:
							results.append(element_info)
						
					except Exception as e:
						logger.error(f"Error processing element: {str(e)}")
						# Skip elements that cause errors
						continue
			except Exception as e:
				logger.error(f"Error querying elements with selector {selector}: {str(e)}")
		
		logger.info(f"Observed {len(results)} elements in viewport")            
		return results
