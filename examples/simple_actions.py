import asyncio
import os
from browserhand import BrowserHand
from langchain_openai import ChatOpenAI

async def async_main():
    # Initialize chat model
    llm = ChatOpenAI(
        model="gpt-4o",  # Use GPT-4 for better results
        temperature=0,
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    # Initialize BrowserHand
    browser = await BrowserHand.create(
        llm=llm,
        headless=False
    )
    
    try:
        # Navigate to a website
        await browser.goto("https://www.example.com")
        
        # Use natural language to control the browser
        result = await browser.Act("Click on the first link on the page")
        print("Action result:", result["success"])
        
        # Wait a moment to see the page change
        await asyncio.sleep(2)
        
        # Try another action
        result = await browser.Act("Go back and then scroll down 50% of the page")
        print("Action result:", result["success"])
    
    finally:
        await browser.close()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
