import urllib.parse
import re
import time


def search_amazon(page, query: str, raw_title: str = "") -> list:
    """
    Role: Amazon DNA Bridge & Validation Agent
    Phase 1-3: Surgical Extraction, Hard-Stop Purge, and Native Formatting
    """
    # 1. Surgical Extraction & Identity Anchor
    brand_m = re.search(r'^(Samsung|Apple|OnePlus|Realme|Xiaomi|Motorola|Google|Nothing)', query, re.I)
    brand = brand_m.group(1) if brand_m else ""
    
    # 2. Hard-Stop Noise Purge (Anti-Poison Filter)
    dna = query
    purge_list = [
        r'\b(5g|4g|lte|volte|5 g|4 g)\b', 
        r'\b(ai|smartphone|phone|mobile|200mp|camera|s pen|battery|included|fast|super)\b',
        r'\b(big billion days|bbd|sale|exclusive|discount|offer|latest|deal|special|launch|new)\b'
    ]
    for pattern in purge_list:
        dna = re.sub(pattern, '', dna, flags=re.I)
    
    # 3. Amazon-Native Formatting (Absolute Identity Anchor)
    # Force [Brand] [Model] to the front, even if they were moved by the purge
    clean_model = re.sub(brand, '', dna, flags=re.I).strip()
    # Enforce mandatory space for units
    clean_model = re.sub(r'(\d+)\s*(GB|TB|RAM)', r'\1 \2', clean_model, flags=re.I).upper()
    clean_model = re.sub(r'RAM', '', clean_model, flags=re.I).strip()
    
    # Reconstruct the Surgical String
    base_query = f"{brand.title()} {clean_model}".strip()
    if not brand: base_query = dna # Fallback if brand extraction failed
    
    # PHASE 4: Verification Key Generation
    # Extract must-have specs for final validation
    must_haves = []
    if brand: must_haves.append(brand.lower())
    storage_m = re.search(r'(\d+)\s*GB', dna, re.I)
    if storage_m: must_haves.append(f"{storage_m.group(1)} GB".lower())
    ram_m = re.search(r'(\d+)\s*GB', re.sub(r'\d+\s*GB', '', dna, 1), re.I) # Second GB is usually RAM
    if ram_m: must_haves.append(f"{ram_m.group(1)} GB".lower())
    
    strategies = [
        base_query, 
        re.sub(r'\d+\s*GB.*', '', base_query, flags=re.I).strip()
    ]
    
    results = []
    seen_asins = set()

    # Set High-Reputation Stealth Headers (mimicking a visit from Google)
    page.context.clear_cookies() # Start with a clean slate
    page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    })

    # Strategy 0: Human-Mimicry (Navigate to home + Type) - HIGHEST STEALTH
    try:
        print("[*] Amazon Strategy 0: Human-Mimicry (Search Bar Typing)")
        page.goto("https://www.amazon.in", wait_until="commit", timeout=30000)
        time.sleep(1)
        
        # Check for search bar
        search_box = page.locator('#twotabsearchtextbox')
        search_box.wait_for(timeout=10000)
        if search_box.count() > 0:
            search_box.click()
            time.sleep(0.5)
            search_box.fill("")
            # Type with human-like delay
            search_box.press_sequentially(base_query, delay=100)
            page.keyboard.press("Enter")
            
            # Wait for results or robot check
            try:
                page.wait_for_selector('[data-component-type="s-search-result"], .s-result-item', timeout=15000)
            except:
                pass
    except Exception as e:
        print(f"[-] Amazon Strategy 0 failed: {e}")

    for i, search_term in enumerate(strategies):
        if not search_term or len(search_term.strip()) < 5: continue
        # Check if Strategy 0 already found results
        if results: break 
        
        encoded_q = urllib.parse.quote_plus(search_term.strip())
        search_url = f"https://www.amazon.in/s?k={encoded_q}&ref=nb_sb_noss"
        
        print(f"[*] Amazon Strategy {i+1}: {search_url}")
        
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            
            # Layer 1: Robot Check Detection & Recovery
            for _ in range(3):
                try:
                    content = page.content().lower()
                except:
                    time.sleep(2)
                    continue

                if any(kw in content for kw in ["robot check", "enter the characters", "verify you are human", "unusual traffic", "px-captcha"]):
                    print(f"  [⚠️] Amazon Robot Check detected. Strategy {i+1} refreshing...")
                    time.sleep(3)
                    page.reload(wait_until="domcontentloaded")
                else:
                    break
            
            # Final check and wait for results
            try:
                page.wait_for_selector('[data-component-type="s-search-result"], .s-result-item', timeout=15000)
            except:
                content_now = page.content().lower()
                title_now = page.title().lower()
                if "no results" in content_now:
                    print(f"  [-] Strategy {i+1}: Zero results found.")
                elif any(kw in title_now for kw in ["robot check", "captcha"]) or "robot check" in content_now:
                    print(f"  [!] Strategy {i+1} permanently blocked by Robot Check.")
                continue # Try next strategy or exit loop if done

            # Scroll to load
            page.mouse.wheel(0, 2000)
            time.sleep(1)

            # Extract from all possible containers
            items = page.locator('[data-component-type="s-search-result"], .s-result-item[data-asin], .sg-col-inner').all()
            
            for item in items:
                try:
                    # Find title and link
                    title_link = item.locator('h2 a, a.a-link-normal.s-underline-text').first
                    if not title_link.count(): continue
                    
                    href = title_link.get_attribute("href") or ""
                    title = title_link.inner_text().strip()
                    
                    if not title or len(title) < 10: continue
                    
                    # ULTRA-AGGRESSIVE ASIN EXTRACTION
                    asin = None
                    # 1. From standard data-asin attribute
                    asin = item.get_attribute("data-asin")
                    
                    # 2. From ANY link inside the card
                    if not asin or len(asin) != 10:
                        all_links = item.locator('a[href*="/dp/"], a[href*="/gp/product/"]').all()
                        for link in all_links:
                            h = link.get_attribute("href") or ""
                            m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', h)
                            if m:
                                asin = m.group(1)
                                break
                    
                    if not asin or len(asin) != 10 or asin in seen_asins:
                        continue
                        
                    seen_asins.add(asin)
                    results.append({
                        "title": title,
                        "url": f"https://www.amazon.in/dp/{asin}",
                        "verification_key": must_haves # Phase 4 Verification Key
                    })
                    print(f"  [✓] Link Snipped: {asin}")
                except:
                    continue
                
                if len(results) >= 5: break
                
        except Exception as e:
            print(f"[-] Amazon Strategy {i+1} failed: {e}")
            continue

    # Strategy 3: Google Discovery (Broadened)
    if not results:
        print(f"[*] Search failed. Broadening Discovery via Google for '{base_query}'...")
        try:
            # Broaden the query by removing storage if necessary to ensure a link is found
            broad_query = re.sub(r'\d+\s*GB.*', '', base_query, flags=re.I).strip()
            google_url = f"https://www.google.com/search?q=site:amazon.in+dp+{urllib.parse.quote_plus(broad_query)}"
            page.goto(google_url, wait_until="load", timeout=30000)
            
            # Extract ANY Amazon product link from Google results
            links = page.locator('a[href*="amazon.in/dp/"], a[href*="amazon.in/gp/product/"]').all()
            for l in links:
                href = l.get_attribute("href") or ""
                if "/url?q=" in href:
                    href = href.split("/url?q=")[1].split("&")[0]
                    href = urllib.parse.unquote(href)
                
                asin_m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', href)
                if asin_m:
                    asin = asin_m.group(1)
                    if asin not in seen_asins:
                        seen_asins.add(asin)
                        results.append({
                            "title": base_query, 
                            "url": f"https://www.amazon.in/dp/{asin}",
                            "verification_key": must_haves # Phase 4 Verification Key
                        })
                        print(f"  [✓] Broad Discovery Found Link: {asin}")
                if len(results) >= 3: break
        except Exception as e:
            print(f"[-] Broad Discovery failed: {e}")

    return results


def search_amazon_via_api(query: str, raw_title: str = "", model_number: str = "") -> list:
    """
    High-Precision Rainforest API Bridge.
    Uses 'Model Number' fallback and Accessory filtering.

    FIX: No longer blindly takes first 5 words (which broke on verbose Flipkart/Croma
    titles). Instead strips color + RAM, leaving Brand + Model + Storage.
    FIX: verification_key now contains brand + storage + RAM digits so _best_match
    can properly reject wrong-storage results.
    """
import requests
import os

_RAINFOREST_EXHAUSTED = False

def search_amazon_via_api(query: str, raw_title: str = "", model_number: str = "") -> list:
    """
    High-Precision Rainforest API Bridge.
    """
    global _RAINFOREST_EXHAUSTED
    if _RAINFOREST_EXHAUSTED:
        return []

    api_key = os.getenv("RAINFOREST_API_KEY", "39B0C71D833D442CB1AB3F45008BC2A4")

    # --- Smart query cleaning: keep Brand + Model + Storage, drop Color & RAM ---
    # build_search_query already produces: "Samsung Galaxy S25 Ultra 12 GB 256 GB Titanium Black"
    # We want:                             "Samsung Galaxy S25 Ultra 256 GB"
    clean_query = query

    # Strip trailing color words & RAM noise
    color_pattern = re.compile(
        r'\b(black|white|silver|gold|blue|red|green|violet|gray|grey|titanium|'
        r'graphite|midnight|starlight|cream|coral|lavender|pink|purple|orange|teal)\b.*$',
        re.IGNORECASE
    )
    clean_query = color_pattern.sub('', clean_query).strip()

    # Clean redundant RAM specs if present twice
    gb_matches = re.findall(r'\d+\s*(?:GB|TB)', clean_query, re.IGNORECASE)
    if len(gb_matches) >= 2:
        # Keep the larger one as storage, drop the smaller one as RAM
        # Usually they are in order: [RAM] [Storage] in build_search_query
        clean_query = re.sub(re.escape(gb_matches[0]), '', clean_query, count=1)
    
    clean_query = re.sub(r'\s+', ' ', clean_query).strip()

    # --- Build verification_key: brand + storage number + RAM number ---
    must_haves = []
    brand_m = re.search(r'^(\w+)', clean_query)
    if brand_m:
        must_haves.append(brand_m.group(1).lower())
    storage_m = re.search(r'(\d+)\s*(?:GB|TB)', clean_query, re.IGNORECASE)
    if storage_m:
        must_haves.append(storage_m.group(1))   # e.g. "256"
    # Pull RAM from original query (first GB value when two exist)
    all_gb = re.findall(r'(\d+)\s*(?:GB|TB)', query, re.IGNORECASE)
    if len(all_gb) >= 2:
        must_haves.append(all_gb[0])             # e.g. "12" (RAM)

    def _execute_search(term):
        print(f"[*] Amazon Rainforest API search: '{term}'")
        params = {
            'api_key': api_key,
            'type': 'search',
            'amazon_domain': 'amazon.in',
            'search_term': term
        }
        try:
            res = requests.get('https://api.rainforestapi.com/request', params=params, timeout=30)
            if res.status_code == 402:
                print("[!] Rainforest API Error: 402 Payment Required (Credits Exhausted).")
                global _RAINFOREST_EXHAUSTED
                _RAINFOREST_EXHAUSTED = True
                return {"error": "credits_exhausted"}
            if not res.ok:
                print(f"[-] Rainforest API HTTP Error: {res.status_code}")
                return {"error": "http_error"}
            return res.json()
        except Exception as e:
            print(f"[-] Rainforest API Exception for '{term}': {e}")
            return {"error": str(e)}

    # FIRST PASS: Brand + Model + Storage
    data = _execute_search(clean_query)

    # SECOND PASS: Drop storage and retry if zero results (broadened fallback)
    if not data.get('search_results'):
        # Try model_number first (highest precision, e.g. "SM-S938B")
        if model_number:
            brand_m2 = re.search(r'^(\w+)', clean_query)
            brand_prefix = brand_m2.group(1) if brand_m2 else ""
            mn_query = f"{brand_prefix} {model_number}".strip()
            print(f"[*] Rainforest: zero results. Trying model_number fallback: '{mn_query}'")
            data = _execute_search(mn_query)

    if not data.get('search_results'):
        broad_query = re.sub(r'\b\d+\s*(?:GB|TB)\b', '', clean_query, flags=re.IGNORECASE).strip()
        broad_query = re.sub(r'\s+', ' ', broad_query).strip()
        if broad_query and broad_query != clean_query:
            print(f"[*] Rainforest: zero results. Broadening to: '{broad_query}'")
            data = _execute_search(broad_query)

    print(f"[*] Rainforest found {len(data.get('search_results', []))} results for '{clean_query}'")

    candidates = []
    for result in data.get('search_results', []):
        title = result.get('title', '')
        if not title:
            continue

        title_lower = title.lower()

        # Exclude accessories and non-phone items
        if any(x in title_lower for x in ['case', 'cover', 'tempered', 'glass', 'screen guard',
                                            'protector', 'charger', 'cable', 'adapter',
                                            'earbuds', 'earphone', 'watch']):
            continue

        # Exclude Renewed/Refurbished
        if any(kw in title_lower for kw in ["renewed", "refurbished", "pre-owned", "used"]):
            continue

        asin = result.get('asin', '')
        url = result.get('link') or (f"https://www.amazon.in/dp/{asin}" if asin else None)
        if not url:
            continue

        candidates.append({
            'title': title,
            'url': url,
            'asin': asin,
            'verification_key': must_haves   # brand + storage + RAM for proper _best_match validation
        })

    return candidates
