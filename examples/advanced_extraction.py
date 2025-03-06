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
        # Navigate to a product listing page (using a real example site)
        await browser.goto("https://demo.opencart.com/index.php?route=product/category&path=20")
        
        # Example of advanced extraction
        instruction = "Extract all product names and prices from this listing page."
        schema = {
            "products": [
                {
                    "product_name": "string",
                    "price": "string"
                }
            ]
        }

        # Perform the extraction
        extracted_data = await browser.Extract(instruction, schema)

        # Print the extracted data
        print("Extracted Product Data:")
        print(json.dumps(extracted_data, indent=2))
        
    finally:
        await browser.close()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
