
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.getcwd())

from main import ProductMatchingAgent

def diagnostic_run():
    agent = ProductMatchingAgent()
    # Exact URL from the user's screenshot
    url = "https://www.flipkart.com/samsung-galaxy-s25-ultra-5g-titanium-black-512-gb/p/itm41aa5b7pid=MOBH8K8UZPUKTTXK"
    
    print(f"=== STARTING DIAGNOSTIC FOR AMAZON ===")
    results = agent.run(url)
    
    print("\n=== DIAGNOSTIC RESULTS ===")
    print(f"Input Title: {results['input_product']['title']}")
    print(f"Input Specs: {results['input_product']['normalized']}")
    
    amazon = results['matches'].get('amazon')
    if amazon:
        print(f"Amazon Match: FOUND")
        print(f"URL: {amazon['url']}")
        print(f"Confidence: {amazon['confidence']}")
    else:
        print(f"Amazon Match: NOT FOUND")

if __name__ == "__main__":
    diagnostic_run()
