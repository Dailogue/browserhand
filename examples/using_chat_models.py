import asyncio
import os
from browserhand import BrowserHand

# Import LangChain chat models
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

async def async_main():
    # Example 1: Using OpenAI Chat model
    if os.environ.get("OPENAI_API_KEY"):
        print("Example 1: Using OpenAI Chat model")
        
        # Create the LangChain model
        chat_model = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        
        # Initialize BrowserHand with the model
        browser = await BrowserHand.create(llm=chat_model, headless=False)
        
        try:
            # Navigate to a website
            await browser.goto("https://www.example.com")
            
            # Extract data using the model
            data = await browser.Extract(
                "Extract the heading and the first paragraph text from this page",
                {"heading": "string", "paragraph": "string"}
            )
            
            # Print the results
            print("\nExtracted data using OpenAI Chat model:")
            print(data)
            
        finally:
            await browser.close()
    else:
        print("Skipping OpenAI example: OPENAI_API_KEY not set")
    
    # Example 2: Using Anthropic Claude model
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("\nExample 2: Using Anthropic Claude model")
        
        # Create the Anthropic chat model
        claude_model = ChatAnthropic(
            model="claude-3-opus-20240229",
            temperature=0,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        
        # Initialize BrowserHand with the model
        browser = await BrowserHand.create(llm=claude_model, headless=False)
        
        try:
            # Navigate to a website
            await browser.goto("https://www.wikipedia.org")
            
            # Use natural language to perform an action
            result = await browser.Act("Type 'artificial intelligence' in the search box")
            
            # Print the result
            print("\nAction result using Anthropic Claude model:", result["success"])
            
        finally:
            await browser.close()
    else:
        print("Skipping Anthropic example: ANTHROPIC_API_KEY not set")

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
