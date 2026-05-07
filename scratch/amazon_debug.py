import time
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    from playwright_stealth import Stealth
    _stealth_obj = Stealth()
    def stealth_sync(page):
        _stealth_obj.apply_stealth_sync(page)

def debug_amazon(query):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth_sync(page)
        
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        print(f"[*] Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(5)
        
        items = page.locator('div[data-component-type="s-search-result"]').all()
        print(f"[*] Found {len(items)} items.")
        
        for i, item in enumerate(items[:3]):
            print(f"\n--- Item {i+1} ---")
            
            # Check for title using a very broad search
            all_links = item.locator('a').all()
            found_title = False
            for link in all_links:
                text = link.inner_text().strip()
                if len(text) > 30: # Likely a product title
                    print(f"  [Found Candidate Title]: {text[:100]}")
                    print(f"  [Link Tag]: {link.evaluate('node => node.tagName')}")
                    print(f"  [Link Parent Tag]: {link.evaluate('node => node.parentElement.tagName')}")
                    print(f"  [Link Classes]: {link.get_attribute('class')}")
                    found_title = True
                    break
            
            if not found_title:
                print("  [X] No title-like link found.")

        browser.close()

if __name__ == "__main__":
    debug_amazon("Samsung Galaxy S25 Ultra")
