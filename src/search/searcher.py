
import re
import time
import requests
from bs4 import BeautifulSoup
import urllib.parse


def build_search_query(normalized_data: dict, simple: bool = False) -> str:
    """
    Build a clean 'Search DNA' string from normalized product data.
    Format: [Brand] [Model] [Variant] [RAM] [Storage] [Color]
    """
    parts = []

    # 1. Brand
    brand = normalized_data.get("brand", "")
    if brand:
        parts.append(brand.title())

    # 2. Model
    model = normalized_data.get("model", "")
    if model:
        # Strip brand from model if it was accidentally included
        if brand and brand.lower() in model.lower():
            model = re.sub(rf'\b{re.escape(brand)}\b', '', model, flags=re.I).strip()
        if model:
            parts.append(model.title())

    # 3. Variant — normalise raw symbols to words, skip if already in model
    variant = normalized_data.get("variant", "")
    if variant:
        # "+" → "Plus", "r+" → "Plus", etc.
        variant_clean = variant.strip().replace("+", "Plus").replace("\\+", "Plus")
        # Only append if the variant word isn't already embedded in the model
        # e.g. model="Nord Ce 4" already contains "ce", model="2a" already contains "a"
        model_lower = model.lower()
        variant_lower = variant_clean.lower()
        already_in_model = (
            variant_lower in model_lower or
            re.search(rf'\b{re.escape(variant_lower)}\b', model_lower) is not None
        )
        if not already_in_model and (len(variant_clean) > 1 or variant_clean.isalpha()):
            parts.append(variant_clean.title())

    # 5. Storage
    storage = normalized_data.get("storage", "")
    if storage:
        # Standardize to 256GB (no space)
        parts.append(storage.replace(" ", "").upper())

    query = " ".join(parts).strip()

    # Final cleanup: remove connectivity / marketing noise that slipped through
    query = re.sub(r'\b(5g|4g|lte|volte|ai|smartphone|phone)\b', '', query, flags=re.I)
    query = re.sub(r'\s+', ' ', query).strip()
    return query


def search_platform(platform: str, query: str) -> list:
    """
    DuckDuckGo-based search for platforms (fallback, not primary path).
    """
    domains = {
        "amazon": "amazon.in",
        "flipkart": "flipkart.com",
        "croma": "croma.com",
        "reliance_digital": "reliancedigital.in",
    }
    domain = domains.get(platform)
    if not domain:
        return []

    if platform == "amazon":
        search_query = f"site:{domain}/dp {query}"
    elif platform == "flipkart":
        search_query = f"site:{domain}/p/ {query}"
    else:
        search_query = f"site:{domain} {query}"

    results = []
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        )
    }
    try:
        res = requests.post(
            'https://html.duckduckgo.com/html/',
            data={'q': search_query},
            headers=headers,
            timeout=15,
        )
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.result'):
            a_tag = item.select_one('.result__a')
            desc_tag = item.select_one('.result__snippet')
            if not a_tag:
                continue
            raw_url = a_tag.get('href', '')
            clean_url = raw_url
            if 'uddg=' in raw_url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                clean_url = qs.get('uddg', [raw_url])[0]
            if domain in clean_url:
                results.append({
                    "title": a_tag.get_text().strip(),
                    "url": clean_url,
                    "snippet": desc_tag.get_text().strip() if desc_tag else "",
                    "platform": platform,
                })
            if len(results) >= 8:
                break
        time.sleep(1.5)
    except Exception as e:
        print(f"[-] DDG search error for {platform}: {e}")
    return results
