# BrowserHand

BrowserHand is an AI-powered Python library that allows you to control web browsers using natural language. Built on top of Playwright, it provides a simple and intuitive API to automate web interactions without having to write complex automation code.

## Features

- 🧠 **Natural Language Control**: Control browsers using plain English instructions
- 🔍 **Smart Data Extraction**: Extract structured data from web pages with simple prompts
- 🔎 **DOM Observation**: Intelligently identify interactive elements on a page
- ⚡ **Fast & Reliable**: Built on Playwright for cross-browser support and reliability
- 🔗 **Works with existing Playwright code**: Integrate with your existing Playwright automation

## Installation

```bash
pip install browserhand
```

BrowserHand requires Python 3.7+.

After installing, you'll need to install the Playwright browsers:

```bash
playwright install
```

## Quick Start

```python
from browserhand import BrowserHand
from langchain_openai import ChatOpenAI

# Initialize a chat model
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key="your-openai-api-key")

# Initialize BrowserHand with the model
browser = BrowserHand(llm=llm)

try:
    # Navigate to a website
    browser.goto("https://www.example.com")
    
    # Use natural language to perform actions
    browser.Act("Click on the 'Learn more' button and then scroll down")
    
    # Extract data using natural language
    data = browser.Extract(
        "Find the main heading and the first paragraph of text", 
        {"heading": "string", "paragraph": "string"}
    )
    print(data)
    
    # Get interactive elements
    elements = browser.Observe()
    print(f"Found {len(elements)} interactive elements")
    
finally:
    browser.close()
```

## API Reference

### BrowserHand Class

The main class for browser automation with natural language.

```python
browser = BrowserHand(
    llm=None,              # Any LangChain chat model (required)
    headless=False          # Run browser in headless mode
)
```

#### Core Methods

- **goto(url: str) -> None**: Navigate to the specified URL.
- **Act(prompt: str) -> Dict[str, Any]**: Perform actions described in natural language.
- **Extract(instruction: str, schema: Dict[str, str]) -> Dict[str, Any]**: Extract data from the page.
- **Observe() -> List[Dict[str, Any]]**: Get interactive elements on the page.
- **close() -> None**: Close the browser and clean up resources.

## Supported LLM Providers

BrowserHand supports any chat model from the LangChain ecosystem, including:

- OpenAI (via `langchain_openai`)
- Azure OpenAI (via `langchain_openai`)
- Anthropic (via `langchain_anthropic`)

## Command Line Interface

BrowserHand includes a command line interface:

```bash
# Navigate and perform an action
browserhand --url "https://www.example.com" --action "Click on the first button"

# Extract data
browserhand --url "https://www.example.com" --extract "Get the main heading" --schema "heading:string"
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
