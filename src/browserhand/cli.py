import logging
import argparse
import os
import sys
import asyncio
from .core import BrowserHand

logger = logging.getLogger(__name__)

async def async_main():
    """Async implementation of the command line interface."""
    parser = argparse.ArgumentParser(
        description="BrowserHand - AI-powered browser automation"
    )
    
    parser.add_argument("--url", help="URL to navigate to", required=True)
    parser.add_argument("--action", help="Natural language action to perform")
    parser.add_argument("--extract", help="Natural language extraction instruction")
    parser.add_argument("--schema", help="Schema for extraction (comma-separated key:type pairs)")
    parser.add_argument("--observe", help="Observe DOM elements", action="store_true")
    parser.add_argument("--headless", help="Run in headless mode", action="store_true")
    parser.add_argument("--verbose", help="Enable verbose logging", action="store_true")
    
    # Browser options
    browser_group = parser.add_argument_group("Browser Options")
    browser_group.add_argument("--browser-path", help="Path to browser executable")
    browser_group.add_argument("--browser-type", help="Browser type to use (chromium, firefox, webkit)", 
                               default="chromium", choices=["chromium", "firefox", "webkit"])
    browser_group.add_argument("--slowmo", help="Slow down operations by specified milliseconds", 
                               type=int, default=0)
    
    # LLM model options
    model_group = parser.add_argument_group("LLM Options")
    model_group.add_argument("--openai-api-key", help="OpenAI API Key")
    model_group.add_argument("--openai-model", help="OpenAI Model name", default="gpt-4")
    
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger('browserhand').setLevel(logging.DEBUG)
    
    # Get API key from environment if not provided
    api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API Key not provided")
        print("Error: OpenAI API Key not provided. Please provide it with --openai-api-key or set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    try:
        # Import OpenAI chat model
        try:
            from langchain_openai import ChatOpenAI
            
            # Create the chat model
            chat_model = ChatOpenAI(
                model=args.openai_model,
                api_key=api_key,
                temperature=0.0
            )
            
        except ImportError:
            print("Error: Could not import the langchain_openai package.")
            print("Please install it with: pip install langchain_openai")
            sys.exit(1)
        
        # Initialize BrowserHand with the chat model
        browser = await BrowserHand.create(
            llm=chat_model,
            headless=args.headless,
            browser_path=args.browser_path,
            browser_type=args.browser_type,
            slowmo=args.slowmo
        )
        
    except Exception as e:
        print(f"Error: Failed to initialize BrowserHand: {str(e)}")
        sys.exit(1)
    
    try:
        # Navigate to the URL
        await browser.goto(args.url)
        
        # Perform the requested operation
        if args.action:
            result = await browser.Act(args.action)
            print("Result:", result)
            
        if args.extract and args.schema:
            schema = {}
            # Parse schema from format key1:type1,key2:type2
            for item in args.schema.split(","):
                key, type_name = item.split(":")
                schema[key.strip()] = type_name.strip()
                
            result = await browser.Extract(args.extract, schema)
            import json
            print("Extracted data:", json.dumps(result, indent=2))
            
        if args.observe:
            elements = await browser.Observe()
            import json
            print(f"Found {len(elements)} elements")
            print("First 3 elements:", json.dumps(elements[:3], indent=2))
            
    finally:
        await browser.close()

def main():
    """Command line interface for BrowserHand."""
    asyncio.run(async_main())
        
if __name__ == "__main__":
    main()
