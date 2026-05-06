from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    from playwright_stealth import Stealth
    _stealth_obj = Stealth()
    def stealth_sync(page):
        _stealth_obj.apply_stealth_sync(page)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    stealth_sync(page)
    print("Stealth applied successfully with fallback logic")
    browser.close()
