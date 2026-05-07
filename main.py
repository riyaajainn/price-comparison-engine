"""
PriceAgent Pro — main.py
Usage:  py main.py <product_url> [--headless]
"""

import json
import re
import sys
import time
import io
import urllib.parse
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if sys.platform == 'win32':
    # Required for Playwright subprocesses on Windows. 
    # We suppress the DeprecationWarning as this is still necessary for sync Playwright in threads.
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    # Support for playwright-stealth 2.0.0+
    from playwright_stealth import Stealth
    _stealth_obj = Stealth()
    def stealth_sync(page):
        _stealth_obj.apply_stealth_sync(page)

from src.extraction.extractor import ProductExtractor, parse_attributes_from_title
from src.normalization.normalizer import get_normalized_product
from src.search.searcher import build_search_query
from src.matching.matcher import calculate_score, is_rejected

from src.search_engines.amazon import search_amazon
from src.search_engines.flipkart import search_flipkart
from src.search_engines.croma import search_croma
from src.search_engines.reliance import search_reliance

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def _detect_platform(url: str) -> str:
    u = url.lower()
    if "amazon" in u:
        return "amazon"
    if "flipkart" in u:
        return "flipkart"
    if "croma" in u:
        return "croma"
    if "reliancedigital" in u or "reliance" in u:
        return "reliance_digital"
    return "unknown"


class ProductMatchingAgent:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    # ── Browser lifecycle ──────────────────────────────────────────────────

    def start_browser(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--allow-running-insecure-content"
            ],
        )
        self.context = self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            permissions=["geolocation"],
            geolocation={"latitude": 12.9716, "longitude": 77.5946},
        )

    def stop_browser(self):
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

    # ── Fetch the input product page ───────────────────────────────────────

    def fetch_url(self, url: str) -> str:
        page = self.context.new_page()
        stealth_sync(page)
        try:
            print(f"[*] Navigating to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # CAPTCHA loop & Navigation Recovery
            max_checks = 10
            for i in range(max_checks):
                try:
                    content = page.content().lower()
                    title = page.title().lower()
                except Exception as e:
                    print(f"  [!] Navigation in progress or content unreachable. Waiting...")
                    time.sleep(2)
                    continue

                # Smarter check: are we blocked?
                is_blocked = any(kw in title for kw in ["robot check", "captcha", "human"]) or \
                             any(kw in content for kw in ["px-captcha", "press and hold", "verify you are human", "unusual traffic", "enter the characters below"])
                
                # Are we actually on a product page?
                on_product_page = any(kw in content for kw in ["producttitle", "vu-z7g", "pdp__title", "pd-title"])
                
                if is_blocked and not on_product_page:
                    print(f"\n[⚠️] BOT DETECTION on product page! (Check {i+1}/{max_checks})")
                    if self.headless:
                        print("[!] Headless mode: cannot solve CAPTCHA. Retrying with reload...")
                        time.sleep(5)
                        page.reload(wait_until="domcontentloaded")
                    else:
                        print("[!] Solve the CAPTCHA in the browser, then press ENTER here...")
                        input()
                        # Allow time for navigation to settle after manual solve
                        time.sleep(3)
                        try:
                            page.wait_for_load_state("networkidle", timeout=15000)
                        except:
                            pass
                    continue # Re-check content after solve or reload
                else:
                    # No bot detection found or we successfully reached the product page
                    break

            
            # Final content retrieval with a small buffer for dynamic elements
            time.sleep(2)
            try:
                content = page.content()
            except Exception as e:
                print(f"  [!] Final content retrieval failed: {e}. Retrying once...")
                time.sleep(2)
                content = page.content()
                
            page.close()
            return content
        except Exception as e:
            print(f"[!] Error fetching {url}: {e}")
            try:
                if not page.is_closed():
                    page.close()
            except:
                pass
            return ""

    # ── Search one platform (creates its own page) ─────────────────────────

    def _search_one_platform(self, platform: str, query: str, raw_title: str,
                             normalized_data: dict, model_number: str = "") -> tuple:
        """Returns (platform, list_of_candidates)."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Ensure context is alive
                if not self.context:
                    self.start_browser()
                
                page = self.context.new_page()
                stealth_sync(page)
                try:
                    # ── STEP 1: Precision Search (Full DNA: Brand + Model + Variant + RAM + Storage + Color)
                    candidates = self._call_search_engine(platform, page, query, raw_title,
                                                          model_number=model_number)
                    
                    # ── STEP 2: Standard Fallback (Model + Storage)
                    if not candidates:
                        # Build a query without RAM and Color
                        from src.search.searcher import build_search_query
                        std_query = build_search_query(normalized_data, simple=True)
                        if std_query != query:
                            print(f"[*] {platform} precision search failed. Retrying with Standard query: {std_query}")
                            candidates = self._call_search_engine(platform, page, std_query,
                                                                  raw_title, model_number=model_number)
                    
                    # ── STEP 3: Broad Fallback (Model Only) — as a last resort
                    if not candidates:
                        broad_query = f"{normalized_data.get('brand', '')} {normalized_data.get('model', '')} {normalized_data.get('variant', '')}".strip()
                        if broad_query and broad_query != query:
                            print(f"[*] {platform} standard search failed. Retrying with Broad query: {broad_query}")
                            candidates = self._call_search_engine(platform, page, broad_query,
                                                                  raw_title, model_number=model_number)
                    
                    return platform, candidates
                finally:
                    try:
                        page.close()
                    except:
                        pass
            except Exception as e:
                print(f"[!] Attempt {attempt+1} failed for {platform}: {e}")
                if "protocol error" in str(e).lower() or "context" in str(e).lower():
                    print("[*] Recreating browser context for next attempt...")
                    self.stop_browser()
                    self.start_browser()
                if attempt == max_retries - 1:
                    return platform, []
                time.sleep(2)
        
        return platform, []


    def _call_search_engine(self, platform: str, page, query: str, raw_title: str,
                            model_number: str = "") -> list:
        if platform == "amazon":
            # 1. PRIMARY: Call the Rainforest API directly for speed/reliability.
            from src.search_engines.amazon import search_amazon_via_api, search_amazon
            candidates = search_amazon_via_api(query, raw_title, model_number=model_number)
            
            # 2. FALLBACK: Use browser-based scraper if API is exhausted or zero results
            if not candidates:
                print(f"[*] Amazon API provided no results. Falling back to Browser Scraper...")
                return search_amazon(page, query, raw_title=raw_title)
            return candidates
        elif platform == "flipkart":
            return search_flipkart(page, query, raw_title)
        elif platform == "croma":
            return search_croma(page, query, raw_title)
        elif platform == "reliance_digital":
            return search_reliance(page, query, raw_title)
        return []

    # ── Score candidates for one platform ─────────────────────────────────

    def _best_match(self, candidates: list, normalized_data: dict,
                    raw_title: str, platform: str) -> dict | None:
        best = None
        best_score = 0.0
        print(f"[*] {len(candidates)} candidates from {platform}")

        for cand in candidates:
            enriched = (
                f"{cand['title']} | "
                f"{cand['url'].replace('-', ' ').replace('/', ' ')}"
            )
            # Parse attributes from title/url before normalizing
            cand_raw_data = parse_attributes_from_title(enriched)
            cand_norm = get_normalized_product(cand_raw_data)

            if is_rejected(enriched, normalized_data, cand_norm,
                           input_raw_title=raw_title):
                print(f"    [X] Rejected: {cand['title'][:80]}")
                continue

            # Phase 4 Verification Key (Strict SKU Matching for Amazon)
            if platform == "amazon" and "verification_key" in cand:
                v_key = cand["verification_key"]
                # Normalize title for verification key check (e.g. "One Plus" -> "oneplus")
                title_norm = re.sub(r'[^a-z0-9]', '', cand["title"].lower())
                if not all(re.sub(r'[^a-z0-9]', '', k.lower()) in title_norm for k in v_key):
                    print(f"    [X] Failed Verification Key: {v_key}")
                    continue

            score = calculate_score(normalized_data, cand_norm, enriched)
            print(f"    [✓] Score {score:.2f}: {cand['title'][:80]}")

            # Confidence Alignment: standard 0.75 threshold
            match_threshold = 0.75 

            
            if score >= match_threshold and score > best_score:
                best_score = score
                best = {"url": cand["url"], "confidence": round(score, 2)}

        return best

    # ── Main pipeline ──────────────────────────────────────────────────────

    def run(self, input_url: str, callback: callable = None) -> dict:
        self.start_browser()
        try:
            # 1. Fetch source product
            print(f"[*] Fetching source product: {input_url}")
            source_platform = _detect_platform(input_url)
            html = self.fetch_url(input_url)

            if not html:
                return {"status": "failed", "reason": "could not fetch URL"}

            # 2. Extract
            extractor = ProductExtractor(html, source_platform)
            raw_data = extractor.extract()
            raw_title = raw_data.get("title", "")
            print(f"[*] Extracted title: {raw_title}")
            print(f"[*] Extracted specs: {raw_data}")
            
            if not raw_title:
                print("[!] Warning: Extracted title is empty.")



            # 3. Normalize
            normalized_data = get_normalized_product(raw_data)
            # Fallback: use raw title as model if extraction found nothing
            if not normalized_data["model"] and raw_title:
                normalized_data["model"] = raw_title

            if not normalized_data["model"]:
                print("[!] Warning: Normalized model is empty. Checking raw title fallback...")
                if raw_title:
                    normalized_data["model"] = raw_title
                    print(f"[*] Using raw title as model fallback: {raw_title}")
                else:
                    return {"status": "failed", "reason": "could not extract product details (empty title and model)"}


            print(f"[*] Normalized: {normalized_data}")

            # 4. Build high-precision search query (Search DNA)
            query = build_search_query(normalized_data, simple=False)
            if not query or len(query) < 5:
                query = raw_title
            print(f"[*] Search query: '{query}'\n")


            # 5. Prepare results structure
            all_platforms = ["amazon", "flipkart", "croma", "reliance_digital"]
            results = {
                "input_product": {
                    "url": input_url,
                    "title": raw_title,
                    "normalized": normalized_data,
                },
                "matches": {p: None for p in all_platforms},
            }

            # Source platform — use the exact input URL (confidence 1.0)
            src_match = {
                "url": input_url,
                "confidence": 1.0,
            }
            results["matches"][source_platform] = src_match
            if callback:
                callback(source_platform, src_match)

            # 6. Search remaining platforms in parallel
            platforms_to_search = [p for p in all_platforms if p != source_platform]

            # ThreadPoolExecutor: each platform gets its own Playwright page.
            # We must run Playwright's sync API from the SAME thread that owns
            # the browser context, so we use max_workers=1 for safety unless
            # Sequential search (safer for Playwright sync API)
            for platform in platforms_to_search:
                print(f"\n[*] Searching {platform}...")
                model_num = normalized_data.get("model_number", "")
                _, candidates = self._search_one_platform(platform, query, raw_title, normalized_data, model_number=model_num)
                match = self._best_match(candidates, normalized_data, raw_title, platform)
                results["matches"][platform] = match
                if callback:
                    callback(platform, match)

            print("\n============ FINAL RESULT ============\n")
            return results


        except Exception as e:
            print(f"[!] Critical error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "failed", "error": str(e)}
        finally:
            self.stop_browser()


# ── CLI entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    headless = "--headless" in sys.argv
    url = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

    if not url:
        url = input("Enter product URL: ").strip()

    if url:
        agent = ProductMatchingAgent(headless=headless)
        agent.run(url)
    else:
        print("No URL provided.")
