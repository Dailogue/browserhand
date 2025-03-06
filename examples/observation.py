import asyncio
import json
import os
from browserhand import BrowserHand
from langchain_openai import ChatOpenAI

async def async_main():
    # Initialize chat model
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    # Initialize BrowserHand
    browser = await BrowserHand.create(llm=llm, headless=False)
    
    try:
        # Navigate to a website with interactive elements
        await browser.goto("https://www.wikipedia.org")
        
        # Get observable elements
        elements = await browser.Observe()
        
        # Print summary of elements
        print(f"Found {len(elements)} interactive elements on the page")
        
        # Print first 3 elements for brevity
        print("\nSample elements:")
        print(json.dumps(elements[:3], indent=2))
        
        # Example: Filter for just visible buttons
        visible_buttons = [e for e in elements if e["tag"] == "button" and e["is_visible"]]
        print(f"\nFound {len(visible_buttons)} visible buttons")
        
    finally:
        await browser.close()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
