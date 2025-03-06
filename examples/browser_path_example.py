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
    
    # Specify the path to your browser executable
    # Examples for different platforms:
    browser_paths = {
        "windows_chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "mac_chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "linux_chrome": "/usr/bin/google-chrome"
    }
    
    # Choose appropriate path for your system
    browser_path = browser_paths["windows_chrome"]  # Change this for your system
    
    print(f"Using browser at: {browser_path}")
    
    # Initialize BrowserHand with browser path
    browser = await BrowserHand.create(
        llm=llm,
        headless=False,
        browser_path=browser_path
    )
    
    try:
        # Navigate to a website
        await browser.goto("https://www.example.com")
        
        # Use natural language for an action
        result = await browser.Act("Click on the 'More information...' link if it exists")
        
        print(f"Action successful: {result['success']}")
        
    finally:
        await browser.close()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
