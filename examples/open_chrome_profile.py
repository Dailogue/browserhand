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
    
    # Path to Chrome user data directory (default location on Windows)
    user_data_dir = os.path.expandvars("%LOCALAPPDATA%/Google/Chrome/User Data")
    
    print(f"Opening Chrome with profile from: {user_data_dir}")
    
    # Initialize BrowserHand with your Chrome profile
    browser = await BrowserHand.create(
        llm=llm,
        headless=False,
        user_data_dir=user_data_dir,
        use_existing_page=True  # Use existing page instead of creating a new one
    )
    
    try:
        # Navigate to a website
        await browser.goto("https://www.google.com")
        print("Successfully opened Chrome with your personal profile")
        
        # Use natural language to perform an action
        result = await browser.Act("Search for 'browserhand python'")
        print(f"Action successful: {result['success']}")
        
        # Wait a moment to see the results
        await asyncio.sleep(5)
        
    finally:
        await browser.close()
        print("Browser closed")

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
