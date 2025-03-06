import asyncio
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
        # Navigate to a website
        await browser.goto("https://www.google.com")
        
        # Use natural language to perform a search
        result = await browser.Act("Search for 'langchain python examples' and press Enter")
        print("Search action completed:", result["success"])
        
        # Wait a moment for results to load
        await asyncio.sleep(2)
        
        # Extract search results
        data = await browser.Extract(
            "Extract the titles and URLs of the first 3 search results",
            {"results": [{"title": "string", "url": "string"}]}
        )
        
        # Display the results
        print("\nExtracted search results:")
        print(data)
        
    finally:
        await browser.close()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
