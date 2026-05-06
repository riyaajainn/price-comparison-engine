import time
import urllib.parse
import re
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# All CSS selectors used for product cards and titles on Croma.
# Having them in one place makes future layout updates easy to patch.
# ---------------------------------------------------------------------------
_CARD_SELECTORS = [
    ".product-item",
    ".plp-card-main",
    'li[class*="product"]',
    ".cp-product",
    '[class*="product-list"] li',
    '[class*="plp"] li',
    ".grid-item",
]

_TITLE_SELECTORS = [
    ".plp-product-title",
    ".product-title",
    ".product-name",
    "h3",
    "h4",
    ".plp-product-title a",
    'a[href*="/p/"] h3',
    '[class*="title"]',
    '[class*="name"]',
]

_GRID_READY_SELECTORS = (
    ".product-item, .plp-card-main, .cp-product, "
    ".product-list-container, [class*='product-list'], "
    "[class*='plp-grid'], [class*='grid-item']"
)


def _try_search_bar(page, base_query: str) -> bool:
    """
    Attempt to type into Croma's search bar.
    Returns True if submitted via bar, False otherwise.
    """
    search_selectors = [
        'input[id="searchV2"]',
        'input[placeholder*="Search"]',
        'input[name="text"]',
        'input[type="search"]',
        'input[class*="search"]',
    ]
    for sel in search_selectors:
        try:
            bar = page.wait_for_selector(sel, timeout=8000)
            if bar:
                bar.click()
                time.sleep(0.4)
                bar.fill("")
                bar.type(base_query, delay=120)
                page.keyboard.press("Enter")
                return True
        except Exception:
            continue
    return False


def _extract_items(page, base_query: str) -> list:
    """Pull product title + URL from all matching card elements on the current page."""
    results = []
    seen_pids: set = set()
    known_brands = ["apple", "samsung", "oneplus", "xiaomi",
                    "realme", "oppo", "vivo", "motorola", "google"]
    query_lower = base_query.lower()

    # Try each card selector and use the first one that yields results
    items = []
    for card_sel in _CARD_SELECTORS:
        try:
            found = page.locator(card_sel).all()
            if found:
                items = found
                print(f"[*] Croma: card selector '{card_sel}' → {len(found)} items")
                break
        except Exception:
            continue

    if not items:
        print("[!] Croma: no product cards found with any known selector")
        return []

    for item in items:
        try:
            # Find product link
            link_el = None
            for link_sel in ['a[href*="/p/"]', 'a[href*="croma.com"]', "a"]:
                try:
                    el = item.locator(link_sel).first
                    if el.count():
                        link_el = el
                        break
                except Exception:
                    continue

            if not link_el:
                continue

            href = link_el.get_attribute("href") or ""
            if not href or "/search" in href or "/category" in href:
                continue

            full_url = urllib.parse.urljoin("https://www.croma.com", href)

            pid_match = re.search(r'/p/(\d+)', full_url)
            pid = pid_match.group(1) if pid_match else full_url
            if pid in seen_pids:
                continue
            seen_pids.add(pid)

            # Extract title
            title = ""
            for t_sel in _TITLE_SELECTORS:
                try:
                    t_el = item.locator(t_sel).first
                    if t_el.count():
                        title = t_el.inner_text().strip()
                        if title:
                            break
                except Exception:
                    continue

            if not title:
                title = link_el.get_attribute("title") or link_el.inner_text().strip()

            if not title:
                continue

            title = re.sub(r'^Buy\s+', '', title, flags=re.I)
            title = title.split('\n')[0].strip()

            # Inject brand if missing (helps matcher)
            has_brand = any(b in title.lower() for b in known_brands)
            if not has_brand:
                for b in known_brands:
                    if b in query_lower:
                        title = b.capitalize() + " " + title
                        break

            results.append({"title": title, "url": full_url})
        except Exception:
            continue

        if len(results) >= 25:
            break

    return results


def _google_fallback(page, base_query: str) -> list:
    """Discover Croma product links via a Google site: search as last resort."""
    print(f"[*] Croma: trying Google fallback for '{base_query}'")
    results = []
    seen_pids: set = set()
    try:
        encoded = urllib.parse.quote_plus(f"site:croma.com {base_query} mobile")
        page.goto(f"https://www.google.com/search?q={encoded}",
                  wait_until="domcontentloaded", timeout=30000)
        time.sleep(1)

        for l in page.locator('a').all():
            href = l.get_attribute("href") or ""
            if "/url?q=" in href:
                href = href.split("/url?q=")[1].split("&")[0]
                href = urllib.parse.unquote(href)

            if "croma.com/p/" in href or re.search(r'croma\.com/[^/]+/p/\d+', href):
                pid_m = re.search(r'/p/(\d+)', href)
                pid = pid_m.group(1) if pid_m else href
                if pid in seen_pids:
                    continue
                seen_pids.add(pid)
                title = l.inner_text().strip() or base_query
                title = re.sub(r'^Buy\s+', '', title, flags=re.I).strip()
                results.append({"title": title or base_query, "url": href})

            if len(results) >= 5:
                break
    except Exception as e:
        print(f"[-] Croma Google fallback failed: {e}")

    return results


import requests
import json

def search_croma(page, query: str, raw_title: str = "") -> list:
    base_query = query if query else raw_title
    encoded_q = urllib.parse.quote(base_query)
    # The Elite API endpoint for Croma
    api_url = f"https://api.croma.com/searchforproducts/v1/search?query={encoded_q}&size=20&currentPage=0&fields=FULL"
    
    results = []
    print(f"[*] Querying Croma Elite API (via Browser): {api_url}")
    
    try:
        # Step 1: Navigate to Croma home if not there to get cookies
        if "croma.com" not in page.url:
            page.goto("https://www.croma.com", wait_until="commit", timeout=20000)
            time.sleep(1)

        # Step 2: Execute API call from within the page context to bypass 403
        data = page.evaluate(f"""
            async () => {{
                const res = await fetch("{api_url}");
                return await res.json();
            }}
        """)
        
        products = data.get("products", [])
        for p in products:
            title = p.get("name", "")
            url_path = p.get("url", "")
            if title and url_path:
                full_url = "https://www.croma.com" + url_path
                results.append({"title": title, "url": full_url})
        
        if results:
            print(f"[*] Croma Browser-API found {len(results)} products.")
            return results

    except Exception as e:
        print(f"[*] Croma Browser-API failed: {e}. Trying fallback...")

    try:
        # Fallback to direct navigation and surgical extraction
        search_url = f"https://www.croma.com/searchB?q={encoded_q}:relevance&text={encoded_q}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        
        # Surgical extraction from INITIAL_STATE
        content = page.content()
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', content, re.DOTALL)
        if match:
            state = json.loads(match.group(1))
            # Try to find products in state
            search_data = state.get('search', {})
            prods = search_data.get('products', [])
            if not prods:
                # Try another path in state
                prods = state.get('product', {}).get('productList', [])
            
            for p in prods:
                name = p.get('name')
                p_url = p.get('url')
                if name and p_url:
                    results.append({"title": name, "url": "https://www.croma.com" + p_url})

        # Final fallback: legacy selector-based extraction
        if not results:
            results = _extract_items(page, base_query)

    except Exception as e:
        print(f"[-] Croma Full Fallback error: {e}")

    return results


# ---------------------------------------------------------------------------
# Standalone test runner
# ---------------------------------------------------------------------------
def run_example():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        query = "Samsung Galaxy S25 256 GB"
        data = search_croma(page, query)

        print("\n--- RESULTS ---")
        for i, item in enumerate(data, 1):
            print(f"{i}. {item['title']}\n   {item['url']}\n")

        browser.close()


if __name__ == "__main__":
    run_example()
