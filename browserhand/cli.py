import logging, argparse, os, sys, asyncio
from .core import BrowserHand

logger = logging.getLogger(__name__)

async def async_main():
    parser = argparse.ArgumentParser(description="BrowserHand - AI-powered browser automation")
    parser.add_argument("--url", required=True, help="URL to navigate to")
    parser.add_argument("--action", help="Natural language action to perform")
    parser.add_argument("--extract", help="Extraction instruction")
    parser.add_argument("--schema", help="Schema for extraction (key:type pairs comma-separated)")
    parser.add_argument("--observe", help="Observe DOM elements", action="store_true")
    parser.add_argument("--headless", help="Run in headless mode", action="store_true")
    parser.add_argument("--verbose", help="Enable verbose logging", action="store_true")
    browser_group = parser.add_argument_group("Browser Options")
    browser_group.add_argument("--browser-path", help="Path to browser executable")
    browser_group.add_argument("--browser-type", default="chromium", choices=["chromium", "firefox", "webkit"])
    browser_group.add_argument("--slowmo", type=int, default=0)
    model_group = parser.add_argument_group("LLM Options")
    model_group.add_argument("--openai-api-key", help="OpenAI API Key")
    model_group.add_argument("--openai-model", default="gpt-4", help="OpenAI Model name")
    
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger('browserhand').setLevel(logging.DEBUG)
    
    api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API Key not provided")
        print("Error: OpenAI API Key not provided.")
        sys.exit(1)
    try:
        from langchain_openai import ChatOpenAI
        chat_model = ChatOpenAI(model=args.openai_model, api_key=api_key, temperature=0.0)
    except ImportError:
        print("Error: langchain_openai package not installed. Install with: pip install langchain_openai")
        sys.exit(1)
    
    try:
        browser = await BrowserHand.create(
            llm=chat_model,
            headless=args.headless,
            browser_path=args.browser_path,
            browser_type=args.browser_type,
            slowmo=args.slowmo
        )
    except Exception as e:
        print(f"Initialization error: {e}")
        sys.exit(1)
    
    try:
        await browser.goto(args.url)
        if args.action:
            result = await browser.Act(args.action)
            print("Result:", result)
        if args.extract and args.schema:
            schema = {}
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
    asyncio.run(async_main())
        
if __name__ == "__main__":
    main()
