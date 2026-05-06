from playwright.sync_api import sync_playwright
import time
import urllib.parse

def test_croma():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://www.croma.com', wait_until='commit')
        time.sleep(2)
        api_url = f'https://api.croma.com/searchforproducts/v1/search?query=Apple%20Iphone%2016%20256GB&size=20&currentPage=0&fields=FULL'
        
        try:
            data = page.evaluate(f"""
                async () => {{
                    const res = await fetch("{api_url}");
                    return await res.json();
                }}
            """)
            print("EVAL1 (no IIFE):", type(data), data)
        except Exception as e:
            print("EVAL1 ERROR:", e)

        try:
            data = page.evaluate(f"""
                (async () => {{
                    const res = await fetch("{api_url}");
                    return await res.json();
                }})()
            """)
            print("EVAL2 (IIFE):", type(data), list(data.keys()) if isinstance(data, dict) else data)
        except Exception as e:
            print("EVAL2 ERROR:", e)

        browser.close()

if __name__ == '__main__':
    test_croma()
