
import time
import urllib.parse

import requests
import json

def search_reliance(page, query: str, raw_title: str = "") -> list:
    full_q = query if query else raw_title
    encoded_q = urllib.parse.quote(full_q)
    # The Elite API endpoint for Reliance
    api_url = f"https://www.reliancedigital.in/rcom/search/v2/productlist?q={encoded_q}&size=24&suggestions=true"
    
    results = []
    print(f"[*] Querying Reliance Elite API (via Browser): {api_url}")
    
    try:
        # Step 1: Warmup Reliance if not there
        if "reliancedigital.in" not in page.url:
            page.goto("https://www.reliancedigital.in", wait_until="commit", timeout=20000)
            time.sleep(1)

        # Step 2: Execute API call from within the page context
        data = page.evaluate(f"""
            async () => {{
                const res = await fetch("{api_url}");
                return await res.json();
            }}
        """)
        
        products = data.get("data", {}).get("results", [])
        for p in products:
            title = p.get("name", "")
            url_path = p.get("url", "")
            if title and url_path:
                full_url = "https://www.reliancedigital.in" + url_path
                results.append({"title": title, "url": full_url})
        
        if results:
            print(f"[*] Reliance Browser-API found {len(results)} products.")
            return results

    except Exception as e:
        print(f"[*] Reliance Browser-API failed: {e}. Trying fallback...")

    try:
        # Fallback to direct navigation
        page.goto(f"https://www.reliancedigital.in/products?q={encoded_q}", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        anchors = page.locator('a[href*="/product/"]').all()
        for a in anchors:
            href = a.get_attribute("href") or ""
            
            # Find the actual product title inside the anchor
            title_loc = a.locator('.sp__name, .name')
            if title_loc.count() > 0:
                title = title_loc.first.inner_text().strip()
            else:
                raw_text = a.inner_text().strip()
                lines = [line.strip() for line in raw_text.split('\n') if len(line.strip()) > 5 and line.strip() != "LIMITED_TIME_OFFER"]
                title = lines[0] if lines else ""
                
            if href and title:
                results.append({"title": title, "url": "https://www.reliancedigital.in" + href})
                
    except Exception as e:
        print(f"[-] Reliance Elite Search error: {e}")

    return results

def _clean_reliance_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, "", "", "")
    )
